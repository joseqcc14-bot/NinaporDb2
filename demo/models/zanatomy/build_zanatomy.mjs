// Convierte la extracción de Z-Anatomy (extract_blend.py) en las capas del visor:
// un archivo por capa (piel, esqueleto, músculos, cardiovascular, encéfalo,
// nervios, sentidos, aparatos...) con una malla simplificada por pieza, en el
// formato bodysim-mesh-1 que lee demo/index.html.
//
//   node build_zanatomy.mjs <raw> [salida]
//
// <raw>.json y <raw>.bin vienen de extract_blend.py; zanatomy_parts.json, de
// build_parts.py. La salida por defecto es ../male/.
import fs from "node:fs";
import path from "node:path";
import { pack, simplify, weld } from "../mesh_tools.mjs";

const [raw, outArg] = process.argv.slice(2);
if (!raw) {
  console.error("uso: node build_zanatomy.mjs <raw> [salida]");
  process.exit(1);
}
const here = path.dirname(new URL(import.meta.url).pathname);
const outDir = outArg || path.join(here, "..", "male");
const extraction = JSON.parse(fs.readFileSync(`${raw}.json`, "utf8"));
const buffer = fs.readFileSync(`${raw}.bin`);
const parts = JSON.parse(fs.readFileSync(path.join(here, "zanatomy_parts.json"), "utf8"));

// Triángulos por capa tras simplificar: el visor carga cada capa al encenderla.
const BUDGETS = {
  piel: 70000,
  esqueleto: 170000,
  articulaciones: 60000,
  musculos: 260000,
  inserciones: 70000,
  cardiovascular: 170000,
  encefalo: 130000,
  nervios: 90000,
  sentidos: 40000,
  digestivo: 45000,
  respiratorio: 35000,
  urinario: 12000,
  reproductor: 10000,
  endocrino: 8000,
  linfatico: 25000,
};
const MIN_TRIANGLES = 60;

function geometryOf(entry) {
  const positions = new Float32Array(buffer.buffer, buffer.byteOffset + entry.offset, entry.vertices * 3);
  const indices = new Uint32Array(buffer.buffer, buffer.byteOffset + entry.offset + entry.vertices * 12, entry.triangles * 3);
  return { positions: Float32Array.from(positions), indices: Uint32Array.from(indices) };
}

const byLayer = new Map();
for (const entry of extraction.parts) {
  const info = parts[entry.name];
  if (!info) continue; // pieza descartada en build_parts.py
  if (!byLayer.has(info.layer)) byLayer.set(info.layer, []);
  byLayer.get(info.layer).push({ entry, info });
}

fs.mkdirSync(outDir, { recursive: true });
const summary = [];
for (const [layer, items] of byLayer) {
  const budget = BUDGETS[layer];
  if (!budget) throw new Error(`capa sin presupuesto: ${layer}`);
  // Reparto del presupuesto: favorece algo a las piezas pequeñas para que no se deshagan.
  const weights = items.map(({ entry }) => entry.triangles ** 0.8);
  const total = weights.reduce((a, b) => a + b, 0);
  const meshes = [];
  let before = 0;
  let after = 0;
  items.forEach(({ entry, info }, i) => {
    const target = Math.max(Math.min(entry.triangles, MIN_TRIANGLES), Math.round((budget * weights[i]) / total));
    const geometry = simplify(weld(geometryOf(entry), 1e-6), target);
    if (!geometry.indices.length) return;
    before += entry.triangles;
    after += geometry.indices.length / 3;
    meshes.push({
      key: entry.name,
      name_es: info.name_es,
      label_en: info.label_en,
      uberon: info.uberon,
      model_id: info.model_id,
      layer,
      side: info.side,
      color: info.color,
      ...(info.group ? { group: info.group } : {}),
      ...pack(geometry),
    });
  });
  const file = path.join(outDir, `${layer}.json`);
  fs.writeFileSync(file, JSON.stringify({
    format: "bodysim-mesh-1",
    source: "Z-Anatomy (CC BY-SA 4.0), derivado de BodyParts3D (DBCLS, CC BY-SA 2.1 JP)",
    units: "m",
    layer,
    meshes,
  }));
  summary.push([layer, meshes.length, before, after, fs.statSync(file).size]);
}
// Manifiesto: capas disponibles y límites del cuerpo (para encuadrar la cámara).
const bounds = { min: [Infinity, Infinity, Infinity], max: [-Infinity, -Infinity, -Infinity] };
for (const { entry } of byLayer.get("piel") || []) {
  const { positions } = geometryOf(entry);
  for (let i = 0; i < positions.length; i++) {
    bounds.min[i % 3] = Math.min(bounds.min[i % 3], positions[i]);
    bounds.max[i % 3] = Math.max(bounds.max[i % 3], positions[i]);
  }
}
fs.writeFileSync(path.join(outDir, "manifest.json"), JSON.stringify({
  format: "bodysim-body-1",
  sex: "male",
  source: "Z-Anatomy (CC BY-SA 4.0), derivado de BodyParts3D (DBCLS, CC BY-SA 2.1 JP)",
  bounds,
  layers: summary.map(([layer, parts, , triangles, bytes]) => ({ key: layer, file: `${layer}.json`, parts, triangles, bytes })),
}, null, 1));
for (const [layer, count, before, after, size] of summary) {
  console.log(`${layer.padEnd(15)} ${String(count).padStart(4)} piezas ${String(before).padStart(8)} -> ${String(after).padStart(7)} triángulos  ${(size / 1e6).toFixed(1)} MB`);
}
const totals = summary.reduce((acc, row) => [acc[0] + row[1], acc[1] + row[3], acc[2] + row[4]], [0, 0, 0]);
console.log(`total: ${totals[0]} piezas, ${totals[1]} triángulos, ${(totals[2] / 1e6).toFixed(1)} MB`);
