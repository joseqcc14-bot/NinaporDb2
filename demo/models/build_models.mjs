// Convierte un cuerpo "united" del Human Reference Atlas (GLB de 4-5 millones de
// triángulos) en un modelo ligero para la demo: una malla por estructura
// seleccionable (hígado, pulmón izquierdo, cada vértebra...), simplificada, en
// metros y con sus metadatos: término UBERON, estructura de bodysim, capa y
// nombre en español.
//
// La salida es la carpeta <sexo>/: un archivo por capa (piel, encéfalo,
// sentidos, digestivo...) con, por estructura, posiciones cuantizadas a 16 bits
// e índices en base64 (el visor calcula las normales), y manifest.json con las
// capas y los límites del cuerpo. Con --glb escribe además un GLB estándar.
//
//   node build_models.mjs <3d-vh-f-united.glb> female [--glb]
//   node build_models.mjs <3d-vh-m-united.glb> male [--glb]   (sustituye al hombre de Z-Anatomy)
import fs from "node:fs";
import { Document, NodeIO, getBounds } from "@gltf-transform/core";
import { ALL_EXTENSIONS } from "@gltf-transform/extensions";
import { pack, simplify, vertexNormals, weld } from "./mesh_tools.mjs";

const [source, sex] = process.argv.slice(2);
const writeGlb = process.argv.includes("--glb");
if (!source || !["male", "female"].includes(sex)) {
  console.error("uso: node build_models.mjs <united.glb> male|female");
  process.exit(1);
}
const here = (name) => new URL(name, import.meta.url);
const parts = JSON.parse(fs.readFileSync(here("hra_parts.json"), "utf8"));
const labelsEs = JSON.parse(fs.readFileSync(here("labels_es.json"), "utf8"));

const SKELETON = "UBERON:0004288";
const LAYER_BY_SYSTEM = {
  integumentary_system: "piel",
  nervous_system: "encefalo",
  muscular_system: "musculos",
  male_reproductive_system: "reproductor",
  reproductive_system: "reproductor",
  digestive_system: "digestivo",
  urinary_system: "urinario",
  circulatory_system: "cardiovascular",
  respiratory_system: "respiratorio",
  lymphatic_system: "linfatico",
  skeletal_system: "esqueleto",
};
// Grupos cuyos hijos se seleccionan por separado.
const SPLIT = new Set([
  "Allen_brain", "lungs", "upper_urinary_tract", "kidney", "vertebrae", "pelvis", "lower_limb", "eyes",
  "mammary_gland", "fallopian_tube", "ovary", "palatine_tonsil", "palatine_tonsils", "muscles_of_knee",
  "blood_vasculature", "tracheobronchial_tree",
]);
// Fuera de la demo: un ganglio linfático aislado de alta resolución, la placenta
// (el modelo femenino representa un embarazo a término) y estructuras finas del ojo.
const DROP = new Set(["Yao_lymph_node", "placenta", "nerves_of_eye", "muscles_of_eye", "blood_vasculature_of_eye"]);
// Estructura de bodysim cuando la tabla del HRA no la da.
const MODEL_OVERRIDES = [
  [/mammary_gland/, "UBERON:0000310"],
  [/ovary/, "UBERON:0000992"],
  [/gallbladder/, "UBERON:0002110"],
];
// Triángulos máximos por estructura tras simplificar.
const BUDGET = [
  [/^skin$/, 60000],
  [/^Allen_brain_hemisphere/i, 20000],
  [/^Allen_/, 8000],
  [/^heart$/, 22000],
  [/^liver$/, 14000],
  [/^(left_)?lungs_[LR]$/, 9000],
  [/kidney/, 5000],
  [/vertebra/, 1600],
  [/^blood_vasculature/, 3500],
  [/^bronchi$/, 10000],
  [/mammary_gland/, 6000],
  [/^eye_[LR]$/, 2500],
];
const DEFAULT_BUDGET = 4000;
// Colores de atlas por estructura.
const COLORS = [
  [/^skin$/, "#d9a589"],
  [/__arterias$/, "#c62f2a"],
  [/__venas$/, "#3157b5"],
  [/vertebra|sacrum|coccyx|pubis|ilium|ischium|hyoid|lower_limb/, "#e8dfcb"],
  [/^Allen_brain/i, "#e3a99a"],
  [/spinal_cord|optic_chiasm/, "#f0d36b"],
  [/^eye_/, "#f2f0ea"],
  [/muscles/, "#b5463c"],
  [/^heart$/, "#a8302c"],
  [/lungs/, "#e7aaa6"],
  [/larynx|trachea|bronchi/, "#e5c9b0"],
  [/^liver$/, "#7d2b22"],
  [/gallbladder/, "#4d7d3a"],
  [/biliary/, "#7aa04a"],
  [/pancreas/, "#e3b98c"],
  [/small_intestine/, "#e0a493"],
  [/^colon$/, "#c98a73"],
  [/tonsil/, "#d88c8c"],
  [/kidney/, "#8c2d27"],
  [/renal_pelvis|ureter|urethra/, "#e0bfa3"],
  [/bladder/, "#dba98d"],
  [/spleen/, "#6b2a40"],
  [/thymus/, "#e4baa2"],
  [/prostate/, "#b8697c"],
  [/genital_duct/, "#d7a7a3"],
  [/uterus/, "#c97e8f"],
  [/ovary/, "#e6b9a6"],
  [/fallopian/, "#dc9eaa"],
  [/vagina/, "#c8838f"],
  [/ligaments/, "#dcc0b0"],
  [/mammary/, "#e9c3a8"],
];
const colorFor = (key) => (COLORS.find(([pattern]) => pattern.test(key)) || [null, "#d9b8a8"])[1];

const short = (name) => name.replace(/^VH_[MF]_/, "");

const io = new NodeIO().registerExtensions(ALL_EXTENSIONS);
const input = await io.read(source);
const body = input.getRoot().getDefaultScene().listChildren()[0];

// ---------- Estructuras seleccionables ----------
const units = [];
function collect(node, layer) {
  const key = short(node.getName());
  if (DROP.has(key)) return;
  if (SPLIT.has(key) && node.listChildren().length) {
    for (const child of node.listChildren()) collect(child, layer);
    return;
  }
  if (key.startsWith("blood_vasculature")) {
    // Arterias y venas por separado, según el material de origen, para colorearlas como en un atlas.
    units.push({ node, key: `${key}__arterias`, layer, keep: (prim) => !isVein(prim) });
    units.push({ node, key: `${key}__venas`, layer, keep: isVein });
    return;
  }
  units.push({ node, key, layer: /mammary_gland/.test(key) ? "reproductor" : /^eye_/.test(key) ? "sentidos" : layer });
}
const isVein = (prim) => /vein/i.test(prim.getMaterial()?.getName() || "");
for (const system of body.listChildren()) {
  const layer = LAYER_BY_SYSTEM[short(system.getName())];
  if (!layer) throw new Error(`sistema sin capa: ${system.getName()}`);
  for (const child of system.listChildren()) collect(child, layer);
}

// ---------- Geometría ----------
function merge(root, keep = () => true) {
  const positions = [];
  const indices = [];
  let offset = 0;
  root.traverse((node) => {
    const mesh = node.getMesh();
    if (!mesh) return;
    const m = node.getWorldMatrix();
    const det = m[0] * (m[5] * m[10] - m[6] * m[9]) - m[4] * (m[1] * m[10] - m[2] * m[9]) + m[8] * (m[1] * m[6] - m[2] * m[5]);
    for (const prim of mesh.listPrimitives()) {
      if (prim.getMode() !== 4 || !keep(prim)) continue;
      const position = prim.getAttribute("POSITION");
      const count = position.getCount();
      const v = [0, 0, 0];
      for (let i = 0; i < count; i++) {
        position.getElement(i, v);
        positions.push(
          m[0] * v[0] + m[4] * v[1] + m[8] * v[2] + m[12],
          m[1] * v[0] + m[5] * v[1] + m[9] * v[2] + m[13],
          m[2] * v[0] + m[6] * v[1] + m[10] * v[2] + m[14],
        );
      }
      const source = prim.getIndices() ? prim.getIndices().getArray() : Array.from({ length: count }, (_, i) => i);
      for (let t = 0; t + 2 < source.length; t += 3) {
        // Un nodo reflejado invierte el sentido de los triángulos.
        if (det < 0) indices.push(source[t] + offset, source[t + 2] + offset, source[t + 1] + offset);
        else indices.push(source[t] + offset, source[t + 1] + offset, source[t + 2] + offset);
      }
      offset += count;
    }
  });
  return { positions: Float32Array.from(positions), indices: Uint32Array.from(indices) };
}






// ---------- Metadatos ----------
function describe(unit) {
  const name = unit.node.getName().replace(/__(arterias|venas)$/, "");
  const part = parts[name] || {};
  let modelId = part.model_id || null;
  for (const [pattern, id] of MODEL_OVERRIDES) if (pattern.test(unit.key)) modelId = id;
  if (unit.layer === "esqueleto") modelId = SKELETON;
  const side = /(^|_)(L|left)(_|$)/.test(unit.key) ? "L" : /(^|_)(R|right)(_|$)/.test(unit.key) ? "R" : null;
  return {
    key: unit.key,
    name_es: labelsEs[unit.key] || null,
    label_en: part.label || unit.key.replace(/^Allen_/, "").replace(/_/g, " "),
    uberon: part.uberon || null,
    model_id: modelId,
    layer: unit.layer,
    side,
    color: colorFor(unit.key),
  };
}

// ---------- Salida ----------
const output = new Document();
const buffer = output.createBuffer();
const scene = output.createScene(sex);
output.getRoot().setDefaultScene(scene);
const material = output.createMaterial("tejido").setBaseColorFactor([0.8, 0.7, 0.65, 1]).setRoughnessFactor(0.6).setMetallicFactor(0);
let before = 0;
let after = 0;
const entries = [];
const missingLabels = [];
for (const unit of units) {
  const merged = weld(merge(unit.node, unit.keep));
  const triangles = merged.indices.length / 3;
  if (!triangles) continue;
  const budget = (BUDGET.find(([pattern]) => pattern.test(unit.key)) || [null, DEFAULT_BUDGET])[1];
  const geometry = simplify(merged, budget);
  const extras = describe(unit);
  if (!extras.name_es) missingLabels.push(unit.key);
  before += triangles;
  after += geometry.indices.length / 3;
  const vertexCount = geometry.positions.length / 3;
  const primitive = output
    .createPrimitive()
    .setAttribute("POSITION", output.createAccessor().setType("VEC3").setArray(geometry.positions).setBuffer(buffer))
    .setAttribute("NORMAL", output.createAccessor().setType("VEC3").setArray(vertexNormals(geometry)).setBuffer(buffer))
    .setIndices(
      output
        .createAccessor()
        .setType("SCALAR")
        .setArray(vertexCount < 65536 ? Uint16Array.from(geometry.indices) : geometry.indices)
        .setBuffer(buffer),
    )
    .setMaterial(material);
  scene.addChild(output.createNode(unit.key).setMesh(output.createMesh(unit.key).addPrimitive(primitive)).setExtras(extras));
  entries.push({ ...extras, ...pack(geometry) });
  console.log(`${unit.key.padEnd(48)} ${String(triangles).padStart(7)} -> ${String(geometry.indices.length / 3).padStart(6)}  ${extras.layer.padEnd(14)} ${extras.model_id || "-"}`);
}
scene.setExtras({
  source: "Human Reference Atlas, 3D Reference Organ Set, United " + (sex === "male" ? "Male" : "Female") + " (v2.0), CC BY 4.0",
  units: "m",
});
const outDir = here(`${sex}/`).pathname;
fs.mkdirSync(outDir, { recursive: true });
const credit = scene.getExtras().source;
const layers = [];
for (const layer of [...new Set(entries.map((e) => e.layer))]) {
  const meshes = entries.filter((e) => e.layer === layer);
  const file = `${outDir}${layer}.json`;
  fs.writeFileSync(file, JSON.stringify({ format: "bodysim-mesh-1", source: credit, units: "m", layer, meshes }));
  const triangles = meshes.reduce((n, m) => n + Buffer.from(m.indices, "base64").length / (m.index_bits / 8) / 3, 0);
  layers.push({ key: layer, file: `${layer}.json`, parts: meshes.length, triangles, bytes: fs.statSync(file).size });
}
const skin = units.find((u) => u.key === "skin");
const skinBounds = getBounds(skin.node);
fs.writeFileSync(`${outDir}manifest.json`, JSON.stringify({
  format: "bodysim-body-1", sex, source: credit, bounds: { min: skinBounds.min, max: skinBounds.max }, layers,
}, null, 1));
if (writeGlb) await new NodeIO().write(here(`${sex}.glb`).pathname, output);
const bytes = layers.reduce((n, l) => n + l.bytes, 0);
console.log(`\n${units.length} estructuras, ${before} -> ${after} triángulos, ${layers.length} capas, ${(bytes / 1e6).toFixed(1)} MB`);
if (missingLabels.length) console.log("sin nombre en español:", missingLabels.join(", "));
