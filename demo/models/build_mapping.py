"""Relaciona las piezas 3D del Human Reference Atlas con las estructuras de bodysim.

Lee la tabla de correspondencias del HRA (asct-b-3d-models-crosswalk.csv:
nombre de nodo 3D -> término UBERON) y, con la jerarquía de UBERON (is_a y
part_of), busca para cada término la estructura del modelo más cercana. Escribe
hra_parts.json, que usa build_models.mjs::

    python demo/models/build_mapping.py --crosswalk <crosswalk.csv> --obo <uberon-basic.obo>
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import deque
from pathlib import Path

from bodysim import Kind, load_anatomy
from bodysim.sources.obo import read_obo

OUT = Path(__file__).resolve().parent / "hra_parts.json"


def read_crosswalk(path: Path) -> list[dict]:
    with open(path, encoding="utf-8-sig") as handle:
        rows = list(csv.reader(handle))
    header = next(i for i, row in enumerate(rows) if row and row[0] == "anatomical_structure_of")
    return [dict(zip(rows[header], row)) for row in rows[header + 1 :] if len(row) >= 5]


def nearest_structure(term_id: str, terms: dict, targets: dict) -> str | None:
    """Estructura del modelo más cercana subiendo por is_a y part_of; a igual distancia, órganos antes que sistemas."""
    seen, queue, found, found_depth = {term_id}, deque([(term_id, 0)]), [], None
    while queue:
        current, depth = queue.popleft()
        if found_depth is not None and depth > found_depth:
            break
        if current in targets:
            found.append(current)
            found_depth = depth
            continue
        term = terms.get(current)
        for parent in (term.is_a + term.part_of) if term else []:
            if parent not in seen:
                seen.add(parent)
                queue.append((parent, depth + 1))
    if not found:
        return None
    return min(found, key=lambda sid: (targets[sid] is Kind.SYSTEM, sid))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--crosswalk", type=Path, required=True)
    parser.add_argument("--obo", type=Path, required=True)
    args = parser.parse_args()

    anatomy = load_anatomy()
    targets = {s.id: s.kind for s in anatomy if s.kind is not Kind.ORGANISM}
    _, terms = read_obo(args.obo)
    parts = {}
    for row in read_crosswalk(args.crosswalk):
        name, term_id = row["node_name"], row["OntologyID"]
        if not name or name == "-" or name in parts:
            continue
        uberon = term_id if term_id.startswith("UBERON:") else None
        parts[name] = {
            "uberon": uberon,
            "label": row["label"] if row["label"] != "-" else None,
            "model_id": nearest_structure(uberon, terms, targets) if uberon else None,
        }
    OUT.write_text(json.dumps(parts, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    mapped = sum(1 for p in parts.values() if p["model_id"])
    print(f"{OUT.name}: {len(parts)} piezas, {mapped} enlazadas a una estructura de bodysim")


if __name__ == "__main__":
    main()
