// Utilidades de malla compartidas por los conversores de modelos de la demo.
import { MeshoptSimplifier } from "meshoptimizer";

await MeshoptSimplifier.ready;
MeshoptSimplifier.useExperimentalFeatures = true; // necesario para la opción "Prune"

// Une vértices coincidentes para que la simplificación y las normales suaves vean una superficie continua.
export function weld({ positions, indices }, tolerance = 1e-5) {
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

export function compact(positions, indices) {
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

export function simplify(geometry, maxTriangles) {
  if (geometry.indices.length / 3 <= maxTriangles) return geometry;
  let result = geometry.indices;
  for (const error of [0.02, 0.08, 0.3]) {
    [result] = MeshoptSimplifier.simplify(geometry.indices, geometry.positions, 3, maxTriangles * 3, error, ["Prune"]);
    if (result.length / 3 <= maxTriangles * 1.2) break;
  }
  return compact(geometry.positions, result);
}

export function vertexNormals({ positions, indices }) {
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
export function pack({ positions, indices }) {
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
