"""Cuerpo femenino completo: TC del Visible Human segmentada + órganos del Human Reference Atlas.

Las dos fuentes son la misma mujer: los órganos del HRA se modelaron sobre el Visible
Human Female. Se alinean con una transformación de semejanza ajustada sobre centroides
(vértebras, riñones, bazo, corazón...) y de cada estructura se toma la mejor fuente:

- HRA: órganos del tronco y la cabeza, columna (con la sexta lumbar de esta mujer) y
  pelvis, que son mallas más finas. Sus extremidades y su piel no: el HRA las cambió de
  postura (brazos separados del cuerpo) y no coinciden con el esqueleto real;
- TC (TotalSegmentator, tarea "total", Apache 2.0): cráneo, costillas, esternón,
  cartílagos costales, clavículas, escápulas, húmeros, fémures, músculos, grandes vasos,
  estómago, esófago, duodeno, tiroides, suprarrenales y lóbulos pulmonares;
- TC por umbral de densidad, a 1 mm: piel, y huesos de piernas, antebrazos, manos y pies,
  que la tarea "total" no separa (tibia, fíbula, rótula, radio y ulna se reconocen por su
  forma).

Escribe <salida>.json y <salida>.bin con el mismo formato que extract_blend.py más los
metadatos de cada pieza; build_layers.mjs los convierte en las capas del visor.

    python demo/models/ct/build_female.py --hra <capas HRA> --ct vhp_f.nii.gz --seg seg.nii.gz \\
        --labels labels_total.json --obo uberon-basic.obo --out raw
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
from pathlib import Path

import numpy as np
import SimpleITK as sitk
from scipy import ndimage
from skimage import measure, segmentation

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "zanatomy"))
from build_mapping import nearest_structure  # noqa: E402
from build_parts import LAYER_STRUCTURE, color_for  # noqa: E402

from bodysim import Kind, load_anatomy  # noqa: E402
from bodysim.sources.obo import read_obo  # noqa: E402

CT_SOURCE = "Visible Human Project (U.S. National Library of Medicine), TC segmentada con TotalSegmentator"
HRA_SOURCE = "Human Reference Atlas, 3D Reference Organ Set, United Female (v2.0), CC BY 4.0"

ORDINALS_ES = ["primera", "segunda", "tercera", "cuarta", "quinta", "sexta", "séptima", "octava", "novena", "décima",
               "undécima", "duodécima"]
ORDINALS_EN = ["First", "Second", "Third", "Fourth", "Fifth", "Sixth", "Seventh", "Eighth", "Ninth", "Tenth", "Eleventh",
               "Twelfth"]

# Clase de TotalSegmentator -> (capa, etiqueta inglesa para UBERON, nombre, género del nombre, material para el color).
# Género: "m"/"f" singular, "mp"/"fp" plural; None si el nombre ya lleva el lado.
CT_CLASSES = {
    "stomach": ("digestivo", "stomach", "estómago", "m", None),
    "esophagus": ("digestivo", "esophagus", "esófago", "m", None),
    "duodenum": ("digestivo", "duodenum", "duodeno", "m", None),
    "thyroid_gland": ("endocrino", "thyroid gland", "glándula tiroides", "f", "gland"),
    "adrenal_gland": ("endocrino", "adrenal gland", "glándula suprarrenal", "f", "gland"),
    "lung_upper_lobe_left": ("respiratorio", "upper lobe of left lung", "lóbulo superior del pulmón izquierdo", None, None),
    "lung_lower_lobe_left": ("respiratorio", "lower lobe of left lung", "lóbulo inferior del pulmón izquierdo", None, None),
    "lung_upper_lobe_right": ("respiratorio", "upper lobe of right lung", "lóbulo superior del pulmón derecho", None, None),
    "lung_middle_lobe_right": ("respiratorio", "middle lobe of right lung", "lóbulo medio del pulmón derecho", None, None),
    "lung_lower_lobe_right": ("respiratorio", "lower lobe of right lung", "lóbulo inferior del pulmón derecho", None, None),
    "aorta": ("cardiovascular", "aorta", "aorta", "f", "artery"),
    "pulmonary_vein": ("cardiovascular", "pulmonary vein", "venas pulmonares", "fp", "pulmonary vein"),
    "brachiocephalic_trunk": ("cardiovascular", "brachiocephalic artery", "tronco braquiocefálico", "m", "artery"),
    "subclavian_artery": ("cardiovascular", "subclavian artery", "arteria subclavia", "f", "artery"),
    "common_carotid_artery": ("cardiovascular", "common carotid artery", "arteria carótida común", "f", "artery"),
    "brachiocephalic_vein": ("cardiovascular", "brachiocephalic vein", "vena braquiocefálica", "f", "vein"),
    "superior_vena_cava": ("cardiovascular", "superior vena cava", "vena cava superior", "f", "vein"),
    "inferior_vena_cava": ("cardiovascular", "inferior vena cava", "vena cava inferior", "f", "vein"),
    "portal_vein_and_splenic_vein": ("cardiovascular", "hepatic portal vein", "vena porta y vena esplénica", "fp", "vein"),
    "iliac_artery": ("cardiovascular", "common iliac artery", "arteria ilíaca común", "f", "artery"),
    "iliac_vena": ("cardiovascular", "common iliac vein", "vena ilíaca común", "f", "vein"),
    "humerus": ("esqueleto", "humerus", "húmero", "m", "bone"),
    "femur": ("esqueleto", "femur", "fémur", "m", "bone"),
    "scapula": ("esqueleto", "scapula", "escápula", "f", "bone"),
    "clavicula": ("esqueleto", "clavicle bone", "clavícula", "f", "bone"),
    "gluteus_maximus": ("musculos", "gluteus maximus", "músculo glúteo mayor", "m", "muscle"),
    "gluteus_medius": ("musculos", "gluteus medius", "músculo glúteo medio", "m", "muscle"),
    "gluteus_minimus": ("musculos", "gluteus minimus", "músculo glúteo menor", "m", "muscle"),
    "autochthon": ("musculos", "erector spinae muscle group", "músculos profundos del dorso", "mp", "muscle"),
    "iliopsoas": ("musculos", "iliopsoas", "músculo iliopsoas", "m", "muscle"),
    "skull": ("esqueleto", "skull", "cráneo", "m", "bone"),
    "sternum": ("esqueleto", "sternum", "esternón", "m", "bone"),
    "costal_cartilages": ("esqueleto", "costal cartilage", "cartílagos costales", "mp", "cartilage"),
}
# Estructuras que ya da el HRA (mejores mallas): no se toman de la TC.
FROM_HRA = {"spleen", "kidney", "gallbladder", "liver", "pancreas", "trachea", "small_bowel", "colon", "urinary_bladder",
            "sacrum", "heart", "brain", "spinal_cord", "hip", "atrial_appendage_left", "prostate", "kidney_cyst"}
# Piezas del HRA que no se usan: pulmones enteros (la TC da los lóbulos), y piel, piernas y
# músculos de la rodilla, que el HRA puso en otra postura.
HRA_REPLACED = {"left_lungs_L", "lungs_R", "skin", "lower_limb_L", "lower_limb_R", "muscles_of_knee_L", "muscles_of_knee_R"}


def side_word(side: str | None, gender: str | None) -> str:
    if not side or not gender:
        return ""
    word = "izquierd" if side == "L" else "derech"
    return " " + word + ("a" if gender.startswith("f") else "o") + ("s" if gender.endswith("p") else "")


def describe(name: str) -> dict | None:
    """Clase de TotalSegmentator -> metadatos de la pieza, o None si no se usa."""
    side = "L" if name.endswith("_left") else "R" if name.endswith("_right") else None
    base = name.removesuffix("_left").removesuffix("_right")
    if name.startswith("vertebrae_") or base in FROM_HRA or name in FROM_HRA:
        return None
    if base.startswith("rib_"):
        n = int(name.rsplit("_", 1)[1])
        side = "L" if "_left_" in name else "R"
        return {"layer": "esqueleto", "label_en": f"rib {n}", "display_en": f"{ORDINALS_EN[n - 1]} rib",
                "name_es": f"{ORDINALS_ES[n - 1]} costilla" + side_word(side, "f"), "side": side, "material": "bone"}
    layer, label, spanish, gender, material = CT_CLASSES[base if base in CT_CLASSES else name]
    return {"layer": layer, "label_en": label, "display_en": label, "name_es": spanish + side_word(side, gender),
            "side": side, "material": material}


def lps_to_viewer(points_mm: np.ndarray) -> np.ndarray:
    """LPS en mm -> visor en m: X a la izquierda del sujeto, Y arriba, Z hacia delante."""
    return np.stack([points_mm[:, 0], points_mm[:, 2], -points_mm[:, 1]], 1) / 1000.0


def surface(mask: np.ndarray, origin: np.ndarray, spacing: np.ndarray, sigma: float, level: float = 0.5):
    """Superficie suavizada de una máscara (z, y, x) en coordenadas del visor."""
    zz, yy, xx = np.nonzero(mask)
    if len(zz) < 8:
        return None
    lo = np.maximum([zz.min() - 3, yy.min() - 3, xx.min() - 3], 0)
    hi = np.minimum([zz.max() + 4, yy.max() + 4, xx.max() + 4], mask.shape)
    crop = mask[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]].astype(np.float32)
    field = ndimage.gaussian_filter(crop, sigma)
    if field.max() <= level:
        return None
    verts, faces, _, _ = measure.marching_cubes(field, level)
    zyx = (verts + lo) * spacing[::-1]  # índices (z, y, x) -> mm
    positions = lps_to_viewer(zyx[:, ::-1] + origin)
    faces = faces.astype(np.int64)
    # Orientación hacia fuera: volumen con signo positivo.
    a, b, c = positions[faces[:, 0]], positions[faces[:, 1]], positions[faces[:, 2]]
    if np.einsum("ij,ij->i", a, np.cross(b, c)).sum() < 0:
        faces = faces[:, [0, 2, 1]]
    return positions, faces


# Huesos de una sola pieza: si la segmentación deja fragmentos (p. ej., en la costura entre
# bloques, donde un trozo puede quedar con la etiqueta de la costilla vecina), solo cuenta el mayor.
SINGLE_PIECE = ("rib_", "humerus", "femur", "scapula", "clavicula", "sternum", "skull")


def main_pieces(mask: np.ndarray, single: bool) -> np.ndarray:
    """Quita fragmentos sueltos: deja el mayor, o los que superan el 10 % del mayor."""
    components, count = ndimage.label(mask)
    if count <= 1:
        return mask
    sizes = np.bincount(components.ravel())[1:]
    if single:
        return components == (np.argmax(sizes) + 1)
    return np.isin(components, np.nonzero(sizes >= 0.1 * sizes.max())[0] + 1)


def decode(entry: dict) -> tuple[np.ndarray, np.ndarray]:
    q = np.frombuffer(base64.b64decode(entry["positions"]), dtype=np.uint16).reshape(-1, 3)
    positions = np.array(entry["min"]) + q / 65535.0 * np.array(entry["extent"])
    dtype = np.uint32 if entry["index_bits"] == 32 else np.uint16
    return positions, np.frombuffer(base64.b64decode(entry["indices"]), dtype=dtype).astype(np.int64).reshape(-1, 3)


def umeyama(a: np.ndarray, b: np.ndarray):
    ma, mb = a.mean(0), b.mean(0)
    u, s, vt = np.linalg.svd((b - mb).T @ (a - ma) / len(a))
    d = np.eye(3)
    d[2, 2] = np.sign(np.linalg.det(u @ vt))
    rotation = u @ d @ vt
    scale = np.trace(np.diag(s) @ d) / (a - ma).var(0).sum()
    return scale, rotation, mb - scale * rotation @ ma


# Pares HRA <-> TotalSegmentator para alinear (las lumbares bajas no: esta mujer tiene seis).
ALIGN = {"spleen": "spleen", "kidney_left": "left_kidney", "kidney_right": "right_kidney", "heart": "heart",
         "gallbladder": "gallbladder_", "sacrum": "sacrum", "vertebrae_L1": "lumbar_vertebra_1",
         "vertebrae_L2": "lumbar_vertebra_2", "liver": "liver", "pancreas": "pancreas", "urinary_bladder": "urinary_bladder",
         **{f"vertebrae_T{i}": f"thoracic_vertebra_{i}" for i in range(1, 13)},
         **{f"vertebrae_C{i}": f"cervical_vertebra_{i}" for i in range(1, 8)}}


def align_hra(hra: dict, seg: np.ndarray, labels: dict, origin: np.ndarray, spacing: np.ndarray):
    ids = {v: k for k, v in labels.items()}
    names, a, b = [], [], []
    for ts_name, hra_key in ALIGN.items():
        zz, yy, xx = np.nonzero(seg == ids[ts_name])
        if hra_key not in hra or not len(zz):
            continue
        center = lps_to_viewer((np.stack([xx, yy, zz], 1) * spacing + origin).mean(0, keepdims=True))[0]
        names.append(ts_name)
        a.append(hra[hra_key][0].mean(0))
        b.append(center)
    a, b = np.array(a), np.array(b)
    keep = np.ones(len(a), bool)
    for _ in range(5):  # se descartan los puntos que no encajan (órganos con contornos distintos)
        scale, rotation, shift = umeyama(a[keep], b[keep])
        residual = np.linalg.norm((scale * (rotation @ a.T)).T + shift - b, axis=1) * 1000
        new = residual < max(15.0, 2.5 * np.median(residual[keep]))
        if (new == keep).all():
            break
        keep = new
    print(f"HRA -> TC: escala {scale:.4f}, {keep.sum()} de {len(keep)} puntos, error medio {residual[keep].mean():.1f} mm, "
          f"descartados {[n for n, k in zip(names, keep) if not k]}")
    return scale, rotation, shift


# Huesos de las extremidades que reconoce limb_bones(): nombre, género, etiqueta UBERON, etiqueta inglesa.
LIMB_BONES = {
    "tibia": ("tibia", "f", "tibia", "Tibia"),
    "fibula": ("fíbula", "f", "fibula", "Fibula"),
    "patella": ("rótula", "f", "patella", "Patella"),
    "radius": ("radio", "m", "radius bone", "Radius"),
    "ulna": ("ulna", "f", "ulna", "Ulna"),
    "radius_ulna": ("radio y ulna", "mp", None, "Radius and ulna"),
    "tibia_fibula": ("tibia y fíbula", "fp", None, "Tibia and fibula"),
    "foot": ("huesos del pie", None, None, "Bones of foot"),
    "hand": ("huesos de la mano", None, None, "Bones of hand"),
}


def limb_bones(ct_image, seg: np.ndarray, seg_image, labels: dict, threshold: float):
    """Huesos de las extremidades que la tarea "total" no separa, desde la TC a 1 mm.

    Los huesos se separan con watershed y se reconocen por su forma: en la pierna, los dos
    huesos largos son la tibia (el mayor) y la fíbula, y la rótula queda delante de la rodilla;
    en el antebrazo, el hueso largo que sube más (olécranon) es la ulna y el otro el radio. Si la
    TC no los separa, se nombran juntos ("tibia y fíbula"). El pie es todo el hueso por debajo
    del tobillo (75 mm sobre la planta) y la mano, lo que queda por debajo de la muñeca.
    """
    ct = sitk.GetArrayFromImage(ct_image)
    origin, spacing = np.array(ct_image.GetOrigin()), np.array(ct_image.GetSpacing())
    seg_origin, seg_spacing = np.array(seg_image.GetOrigin()), np.array(seg_image.GetSpacing())
    ids = {v: k for k, v in labels.items()}
    voxel_ml = float(np.prod(spacing)) / 1000.0

    def to_index(value_mm, axis, size):
        return int(np.clip(round((value_mm - origin[axis]) / spacing[axis]), 0, size))

    def seg_crop(z0, z1, x0, x1):  # etiquetas de la segmentación sobre el recorte (vecino más próximo)
        axes = []
        for axis, (a, b), size in ((2, (z0, z1), seg.shape[0]), (1, (0, ct.shape[1]), seg.shape[1]), (0, (x0, x1), seg.shape[2])):
            mm = origin[axis] + np.arange(a, b) * spacing[axis]
            axes.append(np.clip(np.round((mm - seg_origin[axis]) / seg_spacing[axis]).astype(int), 0, size - 1))
        return seg[np.ix_(*axes)]

    def lowest(name):  # z (mm) del punto más bajo de un hueso segmentado (sin vóxeles sueltos)
        rows = np.nonzero(main_pieces(seg == ids[name], single=True).any(axis=(1, 2)))[0]
        return seg_origin[2] + rows.min() * seg_spacing[2]

    found = []
    for side in ("L", "R"):
        suffix = "left" if side == "L" else "right"
        half = (to_index(0, 0, ct.shape[2]), ct.shape[2]) if side == "L" else (0, to_index(0, 0, ct.shape[2]))
        lateral = (to_index(60, 0, ct.shape[2]), ct.shape[2]) if side == "L" else (0, to_index(-60, 0, ct.shape[2]))
        knee, elbow = lowest(f"femur_{suffix}"), lowest(f"humerus_{suffix}")
        regions = {
            "pierna": ((0, to_index(knee + 20, 2, ct.shape[0])), half),
            "brazo": ((to_index(max(elbow - 520, knee + 60), 2, ct.shape[0]), to_index(elbow + 30, 2, ct.shape[0])), lateral),
        }
        for region, ((z0, z1), (x0, x1)) in regions.items():
            crop = ct[z0:z1, :, x0:x1]
            mask = (crop > threshold) & ~ndimage.binary_dilation(seg_crop(z0, z1, x0, x1) > 0, iterations=2)
            mask = ndimage.binary_opening(mask, iterations=1)
            # En la TC de un cadáver las articulaciones están cerradas y los huesos se tocan: se
            # separan con watershed sobre la distancia al borde, con semillas del hueso erosionado
            # (corta los puentes de las articulaciones). Lo que queda sin semilla (falanges
            # pequeñas) se añade como piezas propias.
            seeds, _ = ndimage.label(ndimage.binary_erosion(mask, iterations=2))
            components = segmentation.watershed(-ndimage.distance_transform_edt(mask), seeds, mask=mask)
            leftover, extra = ndimage.label(mask & (components == 0))
            components = np.where(leftover > 0, leftover + components.max(), components)
            crop_origin = origin + np.array([x0, 0, z0]) * spacing
            stats = []
            for index, box in enumerate(ndimage.find_objects(components), start=1):
                piece = components[box] == index
                volume = piece.sum() * voxel_ml
                if volume < 0.5:
                    continue
                zz, yy, xx = np.nonzero(piece)
                z_mm = crop_origin[2] + (box[0].start + zz) * spacing[2]
                stats.append({"index": index, "volume": volume, "zmin": z_mm.min(), "zmax": z_mm.max(),
                              "y": crop_origin[1] + (box[1].start + yy.mean()) * spacing[1]})
            groups = {}
            if region == "pierna":
                # Tobillo a 75 mm de la planta: por debajo, todo es pie.
                sole = min((s["zmin"] for s in stats), default=0.0)
                ankle_row = int(np.clip(round((sole + 75 - crop_origin[2]) / spacing[2]), 0, components.shape[0]))
                foot = components[:ankle_row] > 0
                components[:ankle_row] = 0
                long = sorted((s for s in stats if s["zmax"] - s["zmin"] > 200), key=lambda s: -s["volume"])[:2]
                if not long:
                    continue
                if len(long) == 2:
                    groups["tibia"], groups["fibula"] = [long[0]["index"]], [long[1]["index"]]
                else:
                    groups["tibia_fibula"] = [long[0]["index"]]
                rest = [s for s in stats if s not in long]
                groups["patella"] = [s["index"] for s in rest if s["zmin"] > knee - 80 and 3 < s["volume"] < 60
                                     and s["y"] < long[0]["y"]][:1]
                components[:ankle_row][foot] = components.max() + 1
                groups["foot"] = [int(components.max())]
            else:
                long = sorted((s for s in stats if s["zmax"] - s["zmin"] > 150), key=lambda s: -s["zmax"])[:2]
                if not long:
                    continue
                if len(long) == 2:
                    groups["ulna"], groups["radius"] = [long[0]["index"]], [long[1]["index"]]
                else:
                    groups["radius_ulna"] = [long[0]["index"]]
                wrist = min(s["zmin"] for s in long)
                groups["hand"] = [s["index"] for s in stats if s not in long and s["zmax"] < wrist + 40]
            for bone, indices in groups.items():
                if not indices:
                    continue
                spanish, gender, uberon_label, label_en = LIMB_BONES[bone]
                mesh = surface(np.isin(components, indices), crop_origin, spacing, 1.0)
                if mesh is None:
                    continue
                if gender:
                    name_es = spanish + side_word(side, gender)
                else:  # "huesos del pie izquierdo": el lado concuerda con el pie o la mano
                    name_es = spanish + (side_word(side, "m") if bone == "foot" else side_word(side, "f"))
                volume = sum(s["volume"] for s in stats if s["index"] in indices)
                print(f"umbral: {name_es}, {len(indices)} fragmento(s), {volume:.0f} ml")
                found.append((name_es, label_en, uberon_label, side, mesh))
    return found


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    for name in ("hra", "ct", "seg", "labels", "obo", "out"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--bone-hu", type=float, default=None, help="umbral de hueso (por defecto, según la resolución)")
    args = parser.parse_args()

    labels = {int(k): v for k, v in json.loads(args.labels.read_text()).items()}
    seg_image = sitk.ReadImage(str(args.seg))
    seg = sitk.GetArrayFromImage(seg_image)
    origin, spacing = np.array(seg_image.GetOrigin()), np.array(seg_image.GetSpacing())
    voxel = float(spacing.mean())
    ct = sitk.GetArrayFromImage(sitk.Resample(sitk.ReadImage(str(args.ct)), seg_image, sitk.Transform(), sitk.sitkLinear, -1024.0))

    _, terms = read_obo(args.obo)
    names = {}
    for term in terms.values():
        if not term.obsolete:
            names.setdefault(term.name.lower(), term.id)
            for synonym in term.exact_synonyms:
                names.setdefault(synonym.lower(), term.id)
    anatomy = load_anatomy()
    targets = {s.id: s.kind for s in anatomy if s.kind is not Kind.ORGANISM}

    # Piezas del HRA, decodificadas.
    hra = {}
    manifest = json.loads((args.hra / "manifest.json").read_text())
    for layer in manifest["layers"]:
        for entry in json.loads((args.hra / layer["file"]).read_text())["meshes"]:
            hra[entry["key"]] = (*decode(entry), entry)
    scale, rotation, shift = align_hra(hra, seg, labels, origin, spacing)

    parts = []  # (metadatos, posiciones, caras)
    for key, (positions, faces, entry) in hra.items():
        if key in HRA_REPLACED:
            continue
        meta = {k: entry.get(k) for k in ("name_es", "label_en", "uberon", "model_id", "layer", "side", "color")}
        parts.append(({"key": key, **meta, "source": HRA_SOURCE, "keep": True},
                      (scale * (rotation @ positions.T)).T + shift, faces))

    sigma = max(0.6, 1.8 / voxel)  # ~2 mm de suavizado
    for label_id, name in labels.items():
        info = describe(name)
        if info is None:
            continue
        mesh = surface(main_pieces(seg == label_id, single=name.startswith(SINGLE_PIECE)), origin, spacing, sigma)
        if mesh is None:
            continue
        uberon = names.get(info["label_en"].lower())
        model_id = LAYER_STRUCTURE.get(info["layer"]) or (nearest_structure(uberon, terms, targets) if uberon else None)
        parts.append(({"key": f"ct_{name}", "name_es": info["name_es"], "label_en": info["display_en"], "uberon": uberon,
                       "model_id": model_id, "layer": info["layer"], "side": info["side"],
                       "color": color_for(info["display_en"], info["material"], info["layer"]), "source": CT_SOURCE},
                      *mesh))

    # Piel: superficie del cuerpo en la TC (componente principal, sin la mesa ni los soportes).
    body = ct > -400
    for k in range(body.shape[0]):
        body[k] = ndimage.binary_fill_holes(body[k])
    body = ndimage.binary_opening(body, iterations=2)
    components, count = ndimage.label(body)
    if count:
        body = components == (np.argmax(np.bincount(components.ravel())[1:]) + 1)
        mesh = surface(ndimage.binary_fill_holes(body), origin, spacing, sigma)
        parts.append(({"key": "skin", "name_es": "piel", "label_en": "skin", "uberon": names.get("skin of body"),
                       "model_id": LAYER_STRUCTURE["piel"], "layer": "piel", "side": None,
                       "color": color_for("skin", "skin", "piel"), "source": CT_SOURCE + " (umbral de densidad)"}, *mesh))

    # Huesos de piernas, antebrazos, manos y pies, desde la TC original a 1 mm.
    for name_es, label_en, uberon_label, side, mesh in limb_bones(sitk.ReadImage(str(args.ct)), seg, seg_image, labels,
                                                                 args.bone_hu or 200.0):
        parts.append(({"key": f"ct_{label_en.lower().replace(' ', '_')}_{side.lower()}", "name_es": name_es,
                       "label_en": label_en, "uberon": names.get(uberon_label) if uberon_label else None,
                       "model_id": LAYER_STRUCTURE["esqueleto"], "layer": "esqueleto", "side": side,
                       "color": color_for("bone", "bone", "esqueleto"), "source": CT_SOURCE + " (umbral de densidad)"},
                      *mesh))

    # Marco común: pies en Y = 0, centrado en X y Z según la piel.
    skin = next((p for meta, p, _ in parts if meta["layer"] == "piel"), None)
    reference = skin if skin is not None else np.concatenate([p for _, p, _ in parts])
    offset = np.array([-(reference[:, 0].min() + reference[:, 0].max()) / 2, -reference[:, 1].min(),
                       -(reference[:, 2].min() + reference[:, 2].max()) / 2])

    entries, chunks, position = [], [], 0
    for meta, positions, faces in parts:
        block = (positions + offset).astype(np.float32).tobytes() + faces.astype(np.uint32).tobytes()
        entries.append({**meta, "vertices": len(positions), "triangles": len(faces), "offset": position})
        chunks.append(block)
        position += len(block)
    args.out.with_suffix(".bin").write_bytes(b"".join(chunks))
    args.out.with_suffix(".json").write_text(json.dumps({
        "sex": "female",
        "source": f"{CT_SOURCE}; órganos: {HRA_SOURCE}",
        "parts": entries,
    }, ensure_ascii=False))
    by_layer = {}
    for entry in entries:
        by_layer.setdefault(entry["layer"], []).append(entry)
    for layer, items in sorted(by_layer.items()):
        ct_count = sum(1 for e in items if not e.get("keep"))
        print(f"{layer:15} {len(items):4} piezas ({ct_count} de la TC)")
    print(f"total {len(entries)} piezas")


if __name__ == "__main__":
    main()
