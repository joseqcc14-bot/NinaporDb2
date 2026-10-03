// Escribe las capas del visor a partir de piezas ya preparadas, con sus metadatos
// (<raw>.json y <raw>.bin, p. ej. los de ct/build_female.py): un archivo por capa en
// formato bodysim-mesh-1 y manifest.json.
//
//   node build_layers.mjs <raw> <carpeta de salida>
//
// Las piezas marcadas "keep" (mallas ya ligeras, como las del HRA) se copian sin
// simplificar; el resto reparte el presupuesto de triángulos de su capa.
import fs from "node:fs";
import path from "node:path";
import { pack, simplify, weld } from "./mesh_tools.mjs";

const [raw, outDir] = process.argv.slice(2);
if (!raw || !outDir) {
  console.error("uso: node build_layers.mjs <raw> <carpeta de salida>");
  process.exit(1);
}
const data = JSON.parse(fs.readFileSync(`${raw}.json`, "utf8"));
const buffer = fs.readFileSync(`${raw}.bin`);

const BUDGETS = { piel: 60000, esqueleto: 140000, musculos: 40000, cardiovascular: 40000, respiratorio: 40000 };
const DEFAULT_BUDGET = 20000;
const MIN_TRIANGLES = 200;
const FIELDS = ["key", "name_es", "label_en", "uberon", "model_id", "layer", "side", "color", "group", "source"];

function geometryOf(entry) {
  const positions = new Float32Array(buffer.buffer, buffer.byteOffset + entry.offset, entry.vertices * 3);
  const indices = new Uint32Array(buffer.buffer, buffer.byteOffset + entry.offset + entry.vertices * 12, entry.triangles * 3);
  return { positions: Float32Array.from(positions), indices: Uint32Array.from(indices) };
}

const byLayer = new Map();
for (const entry of data.parts) {
  if (!byLayer.has(entry.layer)) byLayer.set(entry.layer, []);
  byLayer.get(entry.layer).push(entry);
}

fs.mkdirSync(outDir, { recursive: true });
const layers = [];
for (const [layer, entries] of byLayer) {
  const simplified = entries.filter((e) => !e.keep);
  const weights = simplified.map((e) => e.triangles ** 0.8);
  const total = weights.reduce((a, b) => a + b, 0) || 1;
  const budget = BUDGETS[layer] ?? DEFAULT_BUDGET;
  let triangles = 0;
  const meshes = entries.map((entry) => {
    let geometry = geometryOf(entry);
    if (!entry.keep) {
      const share = Math.round((budget * weights[simplified.indexOf(entry)]) / total);
      geometry = simplify(weld(geometry, 1e-6), Math.max(Math.min(entry.triangles, MIN_TRIANGLES), share));
    }
    triangles += geometry.indices.length / 3;
    const meta = Object.fromEntries(FIELDS.filter((f) => entry[f] !== undefined && entry[f] !== null).map((f) => [f, entry[f]]));
    return { ...meta, uberon: entry.uberon ?? null, model_id: entry.model_id ?? null, side: entry.side ?? null, ...pack(geometry) };
  });
  const file = `${layer}.json`;
  fs.writeFileSync(path.join(outDir, file), JSON.stringify({ format: "bodysim-mesh-1", source: data.source, units: "m", layer, meshes }));
  layers.push({ key: layer, file, parts: meshes.length, triangles, bytes: fs.statSync(path.join(outDir, file)).size });
}

// Límites del cuerpo según la piel (para encuadrar la cámara).
const bounds = { min: [Infinity, Infinity, Infinity], max: [-Infinity, -Infinity, -Infinity] };
for (const entry of byLayer.get("piel") || data.parts) {
  const { positions } = geometryOf(entry);
  for (let i = 0; i < positions.length; i++) {
    bounds.min[i % 3] = Math.min(bounds.min[i % 3], positions[i]);
    bounds.max[i % 3] = Math.max(bounds.max[i % 3], positions[i]);
  }
}
fs.writeFileSync(path.join(outDir, "manifest.json"), JSON.stringify({ format: "bodysim-body-1", sex: data.sex, source: data.source, bounds, layers }, null, 1));
for (const l of layers) console.log(`${l.key.padEnd(15)} ${String(l.parts).padStart(4)} piezas ${String(l.triangles).padStart(7)} triángulos  ${(l.bytes / 1e6).toFixed(2)} MB`);
const sum = (k) => layers.reduce((a, l) => a + l[k], 0);
console.log(`total: ${sum("parts")} piezas, ${sum("triangles")} triángulos, ${(sum("bytes") / 1e6).toFixed(1)} MB`);
