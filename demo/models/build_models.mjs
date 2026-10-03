// Convierte un cuerpo "united" del Human Reference Atlas (GLB de 4-5 millones de
// triángulos) en un modelo ligero para la demo: una malla por estructura
// seleccionable (hígado, pulmón izquierdo, cada vértebra...), simplificada, en
// metros y con sus metadatos: término UBERON, estructura de bodysim, capa y
// nombre en español.
//
// La salida es <sexo>.json: por estructura, posiciones cuantizadas a 16 bits e
// índices, en base64 (el visor calcula las normales). Con --glb escribe además
// un GLB estándar para abrirlo en otras herramientas.
//
//   node build_models.mjs <3d-vh-m-united.glb> male [--glb]
//   node build_models.mjs <3d-vh-f-united.glb> female [--glb]
import fs from "node:fs";
import { Document, NodeIO } from "@gltf-transform/core";
import { ALL_EXTENSIONS } from "@gltf-transform/extensions";
import { MeshoptSimplifier } from "meshoptimizer";

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
  nervous_system: "nervioso",
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

const short = (name) => name.replace(/^VH_[MF]_/, "");

await MeshoptSimplifier.ready;
MeshoptSimplifier.useExperimentalFeatures = true; // necesario para la opción "Prune"
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
  units.push({ node, key, layer: /mammary_gland/.test(key) ? "reproductor" : layer });
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

// Une vértices coincidentes para que la simplificación y las normales suaves vean una superficie continua.
function weld({ positions, indices }, tolerance = 1e-5) {
  const seen = new Map();
  const remap = new Uint32Array(positions.length / 3);
  const out = [];
  for (let i = 0; i < remap.length; i++) {
    const key = `${Math.round(positions[3 * i] / tolerance)},${Math.round(positions[3 * i + 1] / tolerance)},${Math.round(positions[3 * i + 2] / tolerance)}`;
    let j = seen.get(key);
    if (j === undefined) {
      j = out.length / 3;
      seen.set(key, j);
      out.push(positions[3 * i], positions[3 * i + 1], positions[3 * i + 2]);
    }
    remap[i] = j;
  }
  const kept = [];
  for (let t = 0; t < indices.length; t += 3) {
    const a = remap[indices[t]], b = remap[indices[t + 1]], c = remap[indices[t + 2]];
    if (a !== b && b !== c && a !== c) kept.push(a, b, c);
  }
  return { positions: Float32Array.from(out), indices: Uint32Array.from(kept) };
}

function compact(positions, indices) {
  const remap = new Int32Array(positions.length / 3).fill(-1);
  const out = [];
  const result = new Uint32Array(indices.length);
  for (let i = 0; i < indices.length; i++) {
    const v = indices[i];
    if (remap[v] < 0) {
      remap[v] = out.length / 3;
      out.push(positions[3 * v], positions[3 * v + 1], positions[3 * v + 2]);
    }
    result[i] = remap[v];
  }
  return { positions: Float32Array.from(out), indices: result };
}

function simplify(geometry, maxTriangles) {
  if (geometry.indices.length / 3 <= maxTriangles) return geometry;
  let result = geometry.indices;
  for (const error of [0.02, 0.08, 0.3]) {
    [result] = MeshoptSimplifier.simplify(geometry.indices, geometry.positions, 3, maxTriangles * 3, error, ["Prune"]);
    if (result.length / 3 <= maxTriangles * 1.2) break;
  }
  return compact(geometry.positions, result);
}

function vertexNormals({ positions, indices }) {
  const normals = new Float32Array(positions.length);
  for (let t = 0; t < indices.length; t += 3) {
    const [a, b, c] = [indices[t] * 3, indices[t + 1] * 3, indices[t + 2] * 3];
    const ux = positions[b] - positions[a], uy = positions[b + 1] - positions[a + 1], uz = positions[b + 2] - positions[a + 2];
    const vx = positions[c] - positions[a], vy = positions[c + 1] - positions[a + 1], vz = positions[c + 2] - positions[a + 2];
    const nx = uy * vz - uz * vy, ny = uz * vx - ux * vz, nz = ux * vy - uy * vx; // ponderada por área
    for (const v of [a, b, c]) {
      normals[v] += nx;
      normals[v + 1] += ny;
      normals[v + 2] += nz;
    }
  }
  for (let i = 0; i < normals.length; i += 3) {
    const length = Math.hypot(normals[i], normals[i + 1], normals[i + 2]) || 1;
    normals[i] /= length;
    normals[i + 1] /= length;
    normals[i + 2] /= length;
  }
  return normals;
}

// Posiciones a 16 bits sobre la caja de cada estructura (precisión < 0,03 mm en el cuerpo entero).
function pack({ positions, indices }) {
  const min = [Infinity, Infinity, Infinity];
  const max = [-Infinity, -Infinity, -Infinity];
  for (let i = 0; i < positions.length; i++) {
    min[i % 3] = Math.min(min[i % 3], positions[i]);
    max[i % 3] = Math.max(max[i % 3], positions[i]);
  }
  const extent = max.map((v, i) => v - min[i] || 1e-6);
  const quantized = new Uint16Array(positions.length);
  for (let i = 0; i < positions.length; i++) quantized[i] = Math.round(((positions[i] - min[i % 3]) / extent[i % 3]) * 65535);
  const wide = positions.length / 3 >= 65536;
  const index = wide ? indices : Uint16Array.from(indices);
  const base64 = (array) => Buffer.from(array.buffer, array.byteOffset, array.byteLength).toString("base64");
  return { min, extent, positions: base64(quantized), indices: base64(index), index_bits: wide ? 32 : 16 };
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
const out = here(`${sex}.json`);
fs.writeFileSync(out, JSON.stringify({
  format: "bodysim-mesh-1",
  source: scene.getExtras().source,
  units: "m",
  meshes: entries,
}));
if (writeGlb) await new NodeIO().write(here(`${sex}.glb`).pathname, output);
console.log(`\n${units.length} estructuras, ${before} -> ${after} triángulos, ${(fs.statSync(out).size / 1e6).toFixed(1)} MB`);
if (missingLabels.length) console.log("sin nombre en español:", missingLabels.join(", "));
