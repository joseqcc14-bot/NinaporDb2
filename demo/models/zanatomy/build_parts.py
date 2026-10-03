"""Metadatos de las piezas de Z-Anatomy para el visor de bodysim.

Lee la extracción de extract_blend.py (<raw>.json), la Terminologia Anatomica
de Z-Anatomy (TA2.csv, con los nombres en español) y UBERON, y escribe
zanatomy_parts.json con, para cada pieza:

- la capa del visor (encéfalo, nervios, sentidos, digestivo... según su grupo);
- el nombre en español, con "izquierdo/derecho" concordado;
- el término UBERON, si el nombre inglés coincide con una etiqueta o sinónimo;
- la estructura de bodysim de la que forma parte (para escalar su masa);
- el color, según el material del atlas.

    python demo/models/zanatomy/build_parts.py --raw raw.json --ta2 TA2.csv --obo uberon-basic.obo
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from build_mapping import nearest_structure  # noqa: E402

from bodysim import Kind, load_anatomy  # noqa: E402
from bodysim.sources.obo import read_obo  # noqa: E402

OUT = HERE / "zanatomy_parts.json"

# Grupos que no se muestran: membranas que envuelven todo y vainas o bolsas diminutas.
DROP_GROUPS = ("Fasciae", "Thoracolumbar fascia", "Abdominopelvic cavity", "Thoracic cavity")
DROP_NAMES = re.compile(r"bursa|tendon sheath|fibrous sheath|^\?|\?{2,}", re.I)

SUBLAYERS = {
    "Central nervous system": "encefalo",
    "Peripheral nervous system": "nervios",
    "Sense organs": "sentidos",
    "Digestive system": "digestivo",
    "Respiratory system": "respiratorio",
    "Genital systems": "reproductor",
    "Endocrine glands": "endocrino",
    "Urinary system": "urinario",
}
# Estructuras repartidas por todo el cuerpo: se asignan por capa.
LAYER_STRUCTURE = {
    "piel": "UBERON:0002097",
    "esqueleto": "UBERON:0004288",
    "articulaciones": "UBERON:0004288",
    "musculos": "UBERON:0001134",
    "inserciones": "UBERON:0001134",
}

# Inserciones musculares: "Masseter.or" es el origen derecho; "Pectoralis minor muscle.e1l",
# la segunda inserción izquierda.
ATTACHMENT = re.compile(r"\.([oe])(\d*)([lr]?)$")
# Músculos en los que el atlas invierte origen e inserción (comprobado a mano).
SWAPPED_ATTACHMENTS = {"Pectoralis minor muscle"}
ATTACHMENT_COLORS = {"origen": "#c8453b", "inserción": "#3a6db3"}

# Grupo funcional de cada músculo: el atlas lo codifica en el material ("Flexion",
# "Origin-Abduction", "End-Extension fingers"...).
FUNCTION_GROUPS = [
    (r"flexion fingers", "flexores de los dedos"),
    (r"extension fingers", "extensores de los dedos"),
    (r"flexion hand", "flexores de la mano o del pie"),
    (r"extension hand|extensor extremities", "extensores de la mano o del pie"),
    (r"flexion", "flexores"),
    (r"extension", "extensores"),
    (r"abduct", "abductores"),
    (r"adduct", "aductores"),
    (r"external rotat", "rotadores externos"),
    (r"internal rotat", "rotadores internos"),
    (r"levator", "elevadores"),
    (r"depressor", "depresores"),
    (r"orbicular", "orbiculares y constrictores"),
    (r"biarticular", "biarticulares"),
    (r"mastica", "masticadores"),
    (r"ingestion", "músculos de la ingestión"),
    (r"phonation", "músculos de la fonación"),
    (r"diaphragm", "músculos respiratorios"),
]

# Colores de atlas: por nombre de pieza primero, luego por material y por capa.
NAME_COLORS = [
    (r"^liver|segment of liver", "#7d2b22"),
    (r"gallbladder", "#4d7d3a"),
    (r"bile duct|hepatic duct|cystic duct", "#7aa04a"),
    (r"pancrea", "#e3b98c"),
    (r"stomach", "#d98f7d"),
    (r"spleen", "#6b2a40"),
    (r"kidney|renal (pelvis|calyx)", "#8c2d27"),
    (r"lung", "#e7aaa6"),
    (r"eyeball|sclera", "#f2f0ea"),
    (r"cornea|lens", "#cfe3ec"),
    (r"iris", "#5b7a8c"),
    (r"tooth|incisor|canine|molar|premolar", "#f3efe3"),
    (r"thyroid|parathyroid", "#b8524a"),
    (r"suprarenal|adrenal", "#d2a24a"),
    (r"testis|epididym", "#d8b3b0"),
    (r"prostate", "#b8697c"),
]
MATERIAL_COLORS = [
    (r"^bone|^skull", "#e8dfcb"),
    (r"teeth", "#f3efe3"),
    (r"cartilage", "#b9d0d6"),
    (r"ligament|articular capsule", "#dcd2bb"),
    (r"tendon|aponeuros", "#e8dacd"),
    (r"pulmonary artery", "#5a63c4"),
    (r"pulmonary vein", "#c8423a"),
    (r"artery|arteries", "#c62f2a"),
    (r"vein|venous|sinus", "#3157b5"),
    (r"nerve|ganglion|plexus", "#f0d36b"),
    (r"white matter", "#efe6da"),
    (r"nucleus|grey|gray", "#c98b7b"),
    (r"brain|cortex|gyr|cerebell", "#e3a99a"),
    (r"lymph", "#7fb36b"),
    (r"gland", "#d08a5c"),
    (r"bronch", "#e5c9b0"),
    (r"mucosa|intestine", "#d9978a"),
    (r"ductus", "#a9c46a"),
    (r"fat", "#e7c35e"),
    (r"skin", "#d9a589"),
]
LAYER_COLORS = {
    "musculos": "#b5463c",
    "cardiovascular": "#a8302c",
    "encefalo": "#e3a99a",
    "nervios": "#f0d36b",
    "sentidos": "#e8d8c8",
    "digestivo": "#cf8f78",
    "respiratorio": "#e3a3a0",
    "urinario": "#c97a5a",
    "reproductor": "#c97e8f",
    "endocrino": "#d08a5c",
    "linfatico": "#7fb36b",
    "esqueleto": "#e8dfcb",
    "articulaciones": "#dcd2bb",
    "inserciones": "#c8453b",
    "piel": "#d9a589",
}


def color_for(name: str, material: str | None, layer: str) -> str:
    for pattern, color in NAME_COLORS:
        if re.search(pattern, name, re.I):
            return color
    if layer == "musculos" and material and not re.search(r"tendon|aponeuros|ligament|capsule|cartilage", material, re.I):
        # Músculos: el atlas los colorea por función; aquí, rojos con ligeras variaciones.
        shade = sum(map(ord, material)) % 5
        return ["#b5463c", "#a83f37", "#bd5146", "#ad4a3f", "#b84238"][shade]
    for pattern, color in MATERIAL_COLORS:
        if material and re.search(pattern, material, re.I):
            return color
    return LAYER_COLORS[layer]


def function_group(material: str | None, layer: str) -> str | None:
    if layer not in ("musculos", "inserciones") or not material:
        return None
    return next((group for pattern, group in FUNCTION_GROUPS if re.search(pattern, material, re.I)), None)


def base_name(name: str) -> str:
    """'(Accessory parotid gland).r' -> 'Accessory parotid gland'."""
    name = re.sub(r"\.[lr]$", "", name.strip())
    return re.sub(r"\s+", " ", name.replace("(", "").replace(")", "")).strip("'. ")


def read_ta2(path: Path) -> dict[str, str]:
    terms = {}
    with open(path, encoding="utf-8-sig") as handle:
        for line in handle:
            fields = line.strip().strip('"').split(";")
            if len(fields) >= 5 and fields[1] and fields[4]:
                english, spanish = fields[1].strip().lower(), fields[4].strip()
                terms.setdefault(english, spanish)
                # "Optic nerve (II)" también como "optic nerve ii", que es como queda en base_name().
                terms.setdefault(base_name(english), spanish)
    return terms


# Términos que la TA2 deja en latín o traduce mal ("Stapes" -> "estapedio", que es el músculo).
SPANISH_TERMS = {
    "lens": "cristalino",
    "malleus": "martillo",
    "incus": "yunque",
    "stapes": "estribo",
    "vitreous body": "cuerpo vítreo",
    "ampulla of lacrimal canaliculus": "ampolla del canalículo lagrimal",
    "gingiva": "encía",
    "philtrum": "filtrum",
    "perionyx": "perioniquio",
    "nail plate foot": "lámina de la uña del pie",
    "perionyx foot": "perioniquio del pie",
    "linea alba": "línea alba",
    "cuneus": "cúneo",
    "precuneus": "precúneo",
    "flocculus": "flóculo",
    "fornix": "fórnix",
    "septum pellucidum": "septo pelúcido",
    "stria terminalis": "estría terminal",
    "cauda equina": "cola de caballo",
}


FEMININE_WORDS = {
    "piel", "nariz", "laringe", "faringe", "pelvis", "mano", "base", "cara", "lengua", "fosa", "red", "raíz",
    "hoz", "tienda", "cápsula", "vaina", "parte", "porción", "rama", "glándula", "costilla", "vértebra",
    "falange", "tráquea", "uretra", "vejiga", "vesícula", "amígdala", "mama", "tibia", "fíbula", "clavícula",
    "escápula", "rótula", "mandíbula", "maxila", "órbita", "córnea", "retina", "coroides", "esclerótica",
    "pupila", "úvula", "encía", "epiglotis", "dermis", "hipófisis", "médula", "duramadre", "aracnoides",
    "piamadre", "cóclea", "membrana", "aponeurosis", "fascia", "articulación", "sínfisis", "sutura",
}
MASCULINE_WORDS = {"sistema", "diafragma", "esquema", "cráneo", "día", "mapa", "iris"}
# Adjetivos que pueden ir delante del sustantivo ("gran vena safena").
LEADING_ADJECTIVES = {
    "gran", "pequeño", "pequeña", "primer", "primera", "segundo", "segunda", "tercer", "tercera",
    "cuarto", "cuarta", "quinto", "quinta", "sexto", "sexta", "séptimo", "séptima", "octavo", "octava",
    "noveno", "novena", "décimo", "décima", "undécimo", "undécima", "duodécimo", "duodécima",
}


SINGULAR_S = {"páncreas", "atlas", "axis", "tórax", "iris", "pubis", "ácigos", "hemiácigos"}


def head_noun(spanish: str) -> str:
    words = spanish.split()
    return next((w for w in words if w not in LEADING_ADJECTIVES), words[0])


def is_plural(spanish: str) -> bool:
    noun = head_noun(spanish)
    return noun.endswith(("os", "as", "es")) and noun not in SINGULAR_S


def is_feminine(spanish: str) -> bool:
    noun = head_noun(spanish)
    if is_plural(spanish):
        noun = noun[:-2] if noun.endswith("es") else noun[:-1]
    if noun in FEMININE_WORDS:
        return True
    if noun in MASCULINE_WORDS:
        return False
    return noun.endswith(("a", "ión", "dad", "tud", "umbre", "is", "ez"))


def spanish_name(name: str, side: str | None, ta2: dict[str, str]) -> str | None:
    base = base_name(name)
    candidates = [base, re.sub(r"\s*\(?\b[IVX]+\)?$", "", base), base + " muscle", re.sub(r" muscle$", "", base)]
    candidates.append(re.sub(r"\s*\((C\d|T\d+|L\d)\)$", "", base))
    for candidate in candidates:
        key = candidate.strip().lower()
        found = SPANISH_TERMS.get(key) or ta2.get(key)
        if found:
            break
    else:
        return None
    spanish = found.strip().lower()
    spanish = re.sub(r"^musculo\b", "músculo", spanish).replace("glóbo", "globo").replace("cerebra media", "cerebral media")
    spanish = re.sub(r"^(cabeza \w+) músculo del ", r"\1 del músculo ", spanish)  # errata de la TA2
    # La TA2 pone entre paréntesis las estructuras inconstantes: "(glándula parótida accesoria)".
    spanish = re.sub(r"^\(([^()]*)\)$", r"\1", spanish)
    # Números de par craneal, vértebra o segmento en mayúsculas: "nervio óptico (II)", "(segmento M1)".
    upper_codes = lambda m: re.sub(r"\b[a-z]{0,2}[ivx\d]+\b", lambda t: t.group(0).upper(), m.group(0))  # noqa: E731
    spanish = re.sub(r"\([^)]*\)", upper_codes, spanish)
    spanish = re.sub(r"\b[ctls]\d{1,2}\b", lambda m: m.group(0).upper(), spanish)  # "núcleo pulposo T1-T2"
    name, code = re.match(r"(.*?)((?: \([^)]*\))?)$", spanish).groups()
    if side and not re.search(r"\b(izquierd|derech)", name):
        word = ("izquierd" if side == "L" else "derech") + ("a" if is_feminine(name) else "o")
        name += " " + word + ("s" if is_plural(name) else "")
    return name + code


def attachment(name: str, side: str | None, ta2: dict[str, str]) -> tuple[str, str | None, str]:
    """'Masseter.or' -> ('origen', 'origen del músculo masetero derecho', 'Origin of Masseter')."""
    match = ATTACHMENT.search(name)
    muscle = name[: match.start()]
    kind = "origen" if match.group(1) == "o" else "inserción"
    if muscle in SWAPPED_ATTACHMENTS:
        kind = "inserción" if kind == "origen" else "origen"
    number = f" ({int(match.group(2)) + 1})" if match.group(2) else ""
    label_en = f"{'Origin' if kind == 'origen' else 'Insertion'} of {base_name(muscle)}{number}"
    muscle_es = spanish_name(muscle + (f".{match.group(3)}" if match.group(3) else ""), side, ta2)
    if not muscle_es:
        return kind, None, label_en
    if is_plural(muscle_es):
        article = "de las " if is_feminine(muscle_es) else "de los "
    else:
        article = "de la " if is_feminine(muscle_es) else "del "
    return kind, f"{kind} {article}{muscle_es}{number}", label_en


def refine_layer(part: dict) -> str | None:
    groups = [re.sub(r"\.[gj]$", "", g) for g in part["parents"]]
    if any(g.startswith(DROP_GROUPS) for g in groups) or DROP_NAMES.search(part["name"]):
        return None
    if part["layer"] == "musculos" and part["material"] and re.search(r"bursa", part["material"], re.I):
        return None
    for group in groups:
        if group in SUBLAYERS:
            return SUBLAYERS[group]
    return part["layer"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--ta2", type=Path, required=True)
    parser.add_argument("--obo", type=Path, required=True)
    args = parser.parse_args()

    raw = json.loads(args.raw.read_text(encoding="utf-8"))["parts"]
    ta2 = read_ta2(args.ta2)
    _, terms = read_obo(args.obo)
    labels = {}
    for term in terms.values():
        if term.obsolete:
            continue
        labels.setdefault(term.name.lower(), term.id)
        for synonym in term.exact_synonyms:
            labels.setdefault(synonym.lower(), term.id)
    anatomy = load_anatomy()
    targets = {s.id: s.kind for s in anatomy if s.kind is not Kind.ORGANISM}

    parts = {}
    for part in raw:
        layer = refine_layer(part)
        if layer is None or part["name"] in parts:
            continue
        if layer == "inserciones":
            # Zona de origen o inserción de un músculo sobre el hueso: sin término UBERON propio.
            kind, name_es, label_en = attachment(part["name"], part["side"], ta2)
            parts[part["name"]] = {
                "layer": layer,
                "name_es": name_es,
                "label_en": label_en,
                "uberon": None,
                "model_id": LAYER_STRUCTURE[layer],
                "side": part["side"],
                "color": ATTACHMENT_COLORS[kind],
                "group": function_group(part["material"], layer),
            }
            continue
        base = base_name(part["name"])
        # "Optic nerve II" -> "optic nerve" o "cranial nerve II", que es como lo nombra UBERON.
        cranial = re.search(r"\bnerve ([IVX]+)$", base)
        uberon = (
            labels.get(base.lower())
            or labels.get(re.sub(r"\s+[IVX]+$", "", base).lower())
            or (cranial and labels.get(f"cranial nerve {cranial.group(1).lower()}"))
        )
        model_id = LAYER_STRUCTURE.get(layer) or (nearest_structure(uberon, terms, targets) if uberon else None)
        parts[part["name"]] = {
            "layer": layer,
            "name_es": spanish_name(part["name"], part["side"], ta2),
            "label_en": base,
            "uberon": uberon,
            "model_id": model_id,
            "side": part["side"],
            "color": color_for(part["name"], part["material"], layer),
            "group": function_group(part["material"], layer),
        }
    OUT.write_text(json.dumps(parts, ensure_ascii=False, indent=0, sort_keys=True) + "\n", encoding="utf-8")
    translated = sum(1 for p in parts.values() if p["name_es"])
    with_uberon = sum(1 for p in parts.values() if p["uberon"])
    print(f"{OUT.name}: {len(parts)} piezas; {translated} con nombre en español; {with_uberon} con UBERON")


if __name__ == "__main__":
    main()
