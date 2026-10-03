"""Extrae las mallas del atlas Z-Anatomy (Startup.blend) para el visor de bodysim.

Se ejecuta con Blender como módulo de Python (pip install bpy==4.2.*):

    python extract_blend.py <Startup.blend> <salida>

Escribe <salida>.bin (posiciones float32 e índices uint32 de todas las piezas,
seguidos) y <salida>.json (una entrada por pieza: nombre, capa, material, lado,
jerarquía, número de vértices y triángulos). Las coordenadas pasan de Blender
(Z arriba) al visor (Y arriba, +Z hacia delante del sujeto), en metros.
Vasos y nervios son curvas con grosor: se evalúan como malla con menos
resolución para que el atlas quepa en un navegador.
"""

import json
import sys

import bpy
import numpy as np

blend, out = sys.argv[-2], sys.argv[-1]
bpy.ops.wm.open_mainfile(filepath=blend)
scene = bpy.context.scene

COLLECTIONS = {
    "1: Skeletal system": "esqueleto",
    "4: Muscular system": "musculos",
    "5: Cardiovascular system": "cardiovascular",
    "6: Lymphoid organs": "linfatico",
    "7: Nervous system & Sense organs": "nervioso",
    "8: Visceral systems": "visceras",
    "9: Regions of human body": "piel",
}

# Menos resolución en las curvas (tubos de vasos y nervios).
for obj in scene.objects:
    if obj.type == "CURVE":
        data = obj.data
        data.resolution_u = min(data.resolution_u, 3)
        data.render_resolution_u = 0
        if data.bevel_depth > 0:
            data.bevel_resolution = min(data.bevel_resolution, 1)
        if data.bevel_object is not None and data.bevel_object.type == "CURVE":
            data.bevel_object.data.resolution_u = min(data.bevel_object.data.resolution_u, 2)
bpy.context.view_layer.update()
depsgraph = bpy.context.evaluated_depsgraph_get()

# Blender (x, y, z) con Z arriba y -Y delante -> visor (x, z, -y).
AXES = np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]], dtype=np.float64)

entries = []
chunks = []
offset = 0
for collection_name, layer in COLLECTIONS.items():
    collection = scene.collection.children[collection_name]
    for obj in collection.all_objects:
        if obj.type not in {"MESH", "CURVE"} or obj.hide_get():
            continue
        evaluated = obj.evaluated_get(depsgraph)
        try:
            mesh = evaluated.to_mesh()
        except RuntimeError:
            continue
        if mesh is None or not mesh.polygons:
            evaluated.to_mesh_clear()
            continue
        mesh.calc_loop_triangles()
        count = len(mesh.vertices)
        local = np.empty(count * 3, dtype=np.float64)
        mesh.vertices.foreach_get("co", local)
        local = local.reshape(-1, 3)
        world = np.asarray(obj.matrix_world, dtype=np.float64)
        positions = (local @ world[:3, :3].T + world[:3, 3]) @ AXES.T
        triangles = np.empty(len(mesh.loop_triangles) * 3, dtype=np.int64)
        mesh.loop_triangles.foreach_get("vertices", triangles)
        if np.linalg.det(world[:3, :3]) < 0:  # objeto reflejado: se invierte el sentido
            triangles = triangles.reshape(-1, 3)[:, [0, 2, 1]].ravel()
        material = obj.active_material.name if obj.active_material else (mesh.materials[0].name if mesh.materials and mesh.materials[0] else None)
        evaluated.to_mesh_clear()

        chain = []
        parent = obj.parent
        while parent is not None:
            chain.append(parent.name)
            parent = parent.parent
        name = obj.name
        side = "R" if name.endswith(".r") else "L" if name.endswith(".l") else None
        entries.append({
            "name": name,
            "layer": layer,
            "curve": obj.type == "CURVE",
            "material": material,
            "side": side,
            "parents": chain,
            "vertices": count,
            "triangles": len(triangles) // 3,
            "offset": offset,
        })
        block = positions.astype(np.float32).tobytes() + triangles.astype(np.uint32).tobytes()
        chunks.append(block)
        offset += len(block)

with open(out + ".bin", "wb") as handle:
    for block in chunks:
        handle.write(block)
with open(out + ".json", "w", encoding="utf-8") as handle:
    json.dump({"source": "Z-Anatomy (CC BY-SA 4.0), derivado de BodyParts3D", "units": "m", "parts": entries}, handle, ensure_ascii=False)

by_layer = {}
for entry in entries:
    stats = by_layer.setdefault(entry["layer"], [0, 0, 0])
    stats[0] += 1
    stats[1] += entry["triangles"]
    stats[2] += entry["curve"]
for layer, (parts, triangles, curves) in by_layer.items():
    print(f"{layer:15s} piezas={parts:5d} curvas={curves:4d} triángulos={triangles}")
print("total", sum(e["triangles"] for e in entries), "triángulos,", len(entries), "piezas")
