"""Sincroniza la capa anatómica con un release de UBERON.

UBERON es la ontología anatómica abierta (CC BY 3.0) que usan el Human Reference
Atlas (HRA), Monarch, el Human Cell Atlas y la mayoría de bases genómicas. Cada
término trae sus equivalencias en FMA (llave de BodyParts3D y Z-Anatomy), SNOMED
CT, MeSH, NCIt y UMLS, y para los órganos del HRA los enlaces a sus modelos 3D
(GLB). Este módulo extrae esa información para las estructuras del modelo y la
guarda en ``data/uberon_snapshot.json``, de modo que el simulador funcione sin
conexión y cada cambio de release quede visible en el diff.

Uso::

    python -m bodysim.sources.uberon                        # descarga el último release
    python -m bodysim.sources.uberon --obo uberon-basic.obo # usa un archivo local
"""

from __future__ import annotations

import argparse
import json
import re
import tempfile
import urllib.request
from collections import defaultdict
from pathlib import Path

from bodysim.sources.obo import OboTerm, read_obo

RELEASE_URL = "https://github.com/obophenotype/uberon/releases/latest/download/uberon-basic.obo"
XREF_PREFIXES = ("FMA", "SCTID", "MESH", "NCIT", "UMLS")
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
_HRA_MODEL_NAME = re.compile(r"3d-[a-z0-9]+-([fm])-")


def _model_sex(url: str) -> str | None:
    """Los GLB del HRA se llaman ``3d-<origen>-<f|m>-<órgano>.glb``, p. ej. ``3d-vh-f-heart.glb``."""
    match = _HRA_MODEL_NAME.match(url.rsplit("/", 1)[-1])
    if match is None:
        return None
    return "female" if match.group(1) == "f" else "male"


def _models_3d(term: OboTerm, subclasses: list[OboTerm]) -> list[dict]:
    # Algunos modelos cuelgan de subclases laterales (p. ej. "left kidney" is_a "kidney").
    models: list[dict] = []
    seen: set[str] = set()
    for source in [term, *sorted(subclasses, key=lambda t: t.id)]:
        for url in source.depictions:
            if url.endswith(".glb") and url not in seen:
                seen.add(url)
                models.append({"url": url, "sex": _model_sex(url), "uberon": source.id, "label": source.name})
    return models


def build_snapshot(header: dict[str, str], terms: dict[str, OboTerm], ids: list[str]) -> dict:
    """Extrae de ``terms`` la información de cada id; falla si alguno no existe o es obsoleto."""
    missing = [i for i in ids if i not in terms or terms[i].obsolete]
    if missing:
        raise ValueError(f"Términos ausentes u obsoletos en este release de UBERON: {missing}")

    subclasses: dict[str, list[OboTerm]] = defaultdict(list)
    for term in terms.values():
        if not term.obsolete:
            for parent in term.is_a:
                subclasses[parent].append(term)

    snapshot = {}
    for structure_id in ids:
        term = terms[structure_id]
        xrefs = {
            prefix: sorted(x for x in term.xrefs if x.split(":", 1)[0] == prefix) for prefix in XREF_PREFIXES
        }
        snapshot[structure_id] = {
            "label": term.name,
            "definition": term.definition,
            "exact_synonyms": term.exact_synonyms,
            "xrefs": {prefix: values for prefix, values in xrefs.items() if values},
            "is_a": term.is_a,
            "part_of": term.part_of,
            "in_human_reference_atlas": "human_reference_atlas" in term.subsets,
            "models_3d": _models_3d(term, subclasses[structure_id]),
        }
    return {
        "source": {
            "ontology": "UBERON",
            "license": header.get("dcterms-license", ""),
            "data_version": header.get("data-version", ""),
            "download_url": RELEASE_URL,
        },
        "terms": snapshot,
    }


def model_ids(data_dir: Path = DATA_DIR) -> list[str]:
    with open(data_dir / "structures.json", encoding="utf-8") as handle:
        return [entry["id"] for entry in json.load(handle)["structures"]]


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--obo", type=Path, help="archivo uberon-basic.obo local; si se omite se descarga")
    parser.add_argument("--out", type=Path, default=DATA_DIR / "uberon_snapshot.json")
    args = parser.parse_args(argv)

    obo_path = args.obo
    if obo_path is None:
        obo_path = Path(tempfile.gettempdir()) / "uberon-basic.obo"
        print(f"Descargando {RELEASE_URL} ...")
        urllib.request.urlretrieve(RELEASE_URL, obo_path)

    header, terms = read_obo(obo_path)
    snapshot = build_snapshot(header, terms, model_ids())
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(snapshot, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    n_models = sum(len(t["models_3d"]) for t in snapshot["terms"].values())
    print(f"{len(snapshot['terms'])} estructuras y {n_models} modelos 3D desde {snapshot['source']['data_version']}")


if __name__ == "__main__":
    main()
