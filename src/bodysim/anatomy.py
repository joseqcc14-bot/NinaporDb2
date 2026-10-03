"""Capa anatómica: el árbol de estructuras del modelo, enlazado a UBERON.

Cada estructura se identifica por su CURIE de UBERON (p. ej. ``UBERON:0000948``,
corazón). Ese id es la llave común con el resto de recursos:

- FMA, que indexa las mallas de BodyParts3D y Z-Anatomy;
- los modelos 3D GLB del Human Reference Atlas (HRA);
- SNOMED CT, MeSH, NCIt y UMLS, que usan historias clínicas, literatura y
  ontologías de enfermedad, y por donde entrarán las capas de patología y genética.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from functools import lru_cache
from importlib import resources
from types import MappingProxyType
from typing import Iterable, Iterator, Mapping

from bodysim.person import Sex


def load_data(name: str) -> dict:
    """Lee un JSON de ``bodysim/data``."""
    text = resources.files("bodysim").joinpath("data").joinpath(name).read_text(encoding="utf-8")
    return json.loads(text)


class Kind(str, Enum):
    ORGANISM = "organism"
    SYSTEM = "system"
    ORGAN = "organ"
    TISSUE = "tissue"


@dataclass(frozen=True)
class Model3D:
    url: str
    sex: Sex | None
    uberon: str  # término al que está enlazado; puede ser una subclase (p. ej. riñón izquierdo)
    label: str


@dataclass(frozen=True)
class Structure:
    id: str
    name_es: str
    kind: Kind
    parent: str | None
    label_en: str = ""
    definition: str = ""
    bilateral: bool = False
    sex: Sex | None = None  # None: presente en ambos sexos
    xrefs: Mapping[str, tuple[str, ...]] = field(default_factory=dict, hash=False)
    uberon_part_of: tuple[str, ...] = ()
    in_human_reference_atlas: bool = False
    models_3d: tuple[Model3D, ...] = ()

    def applies_to(self, sex: Sex) -> bool:
        return self.sex is None or self.sex is sex

    def models_for(self, sex: Sex) -> tuple[Model3D, ...]:
        return tuple(m for m in self.models_3d if m.sex is None or m.sex is sex)


class Anatomy:
    """Árbol de estructuras con una única raíz (el organismo)."""

    def __init__(self, structures: Iterable[Structure], source_version: str = "") -> None:
        self.source_version = source_version
        self._by_id: dict[str, Structure] = {}
        for structure in structures:
            if structure.id in self._by_id:
                raise ValueError(f"estructura duplicada: {structure.id}")
            self._by_id[structure.id] = structure

        roots = [s for s in self._by_id.values() if s.parent is None]
        if len(roots) != 1:
            raise ValueError(f"se esperaba una raíz y hay {len(roots)}: {[s.id for s in roots]}")
        self._root = roots[0]

        self._children: dict[str, list[Structure]] = {sid: [] for sid in self._by_id}
        for structure in self._by_id.values():
            if structure.parent is None:
                continue
            if structure.parent not in self._by_id:
                raise ValueError(f"{structure.id} tiene un padre desconocido: {structure.parent}")
            self._children[structure.parent].append(structure)

        if len(self.descendants(self._root.id)) + 1 != len(self._by_id):
            raise ValueError("el árbol anatómico tiene ciclos o nodos desconectados de la raíz")

        self._by_xref: dict[str, Structure] = {}
        for structure in self._by_id.values():
            for values in structure.xrefs.values():
                for xref in values:
                    self._by_xref.setdefault(xref, structure)

    @property
    def root(self) -> Structure:
        return self._root

    def __getitem__(self, structure_id: str) -> Structure:
        try:
            return self._by_id[structure_id]
        except KeyError:
            raise KeyError(f"estructura no modelada: {structure_id}") from None

    def __contains__(self, structure_id: object) -> bool:
        return structure_id in self._by_id

    def __iter__(self) -> Iterator[Structure]:
        return iter(self._by_id.values())

    def __len__(self) -> int:
        return len(self._by_id)

    def children(self, structure_id: str) -> tuple[Structure, ...]:
        return tuple(self._children[self[structure_id].id])

    def ancestors(self, structure_id: str) -> tuple[Structure, ...]:
        """Del padre directo hasta la raíz."""
        chain = []
        parent = self[structure_id].parent
        while parent is not None:
            chain.append(self._by_id[parent])
            parent = self._by_id[parent].parent
        return tuple(chain)

    def descendants(self, structure_id: str) -> tuple[Structure, ...]:
        found: list[Structure] = []
        pending = list(self.children(structure_id))
        while pending:
            structure = pending.pop()
            found.append(structure)
            pending.extend(self._children[structure.id])
        return tuple(found)

    def of_kind(self, kind: Kind) -> tuple[Structure, ...]:
        return tuple(s for s in self if s.kind is kind)

    def find_xref(self, xref: str) -> Structure | None:
        """Busca por id externo, p. ej. ``FMA:7088`` o ``SCTID:80891009``."""
        return self._by_xref.get(xref)

    def for_sex(self, sex: Sex) -> Anatomy:
        """Subárbol de las estructuras presentes en ``sex``."""
        excluded = {s.id for s in self if not s.applies_to(sex)}
        kept = [
            s for s in self if s.id not in excluded and not any(a.id in excluded for a in self.ancestors(s.id))
        ]
        return Anatomy(kept, self.source_version)


def _structure(entry: dict, term: dict) -> Structure:
    return Structure(
        id=entry["id"],
        name_es=entry["name_es"],
        kind=Kind(entry["kind"]),
        parent=entry["parent"],
        label_en=term["label"],
        definition=term["definition"],
        bilateral=entry.get("bilateral", False),
        sex=Sex(entry["sex"]) if "sex" in entry else None,
        xrefs=MappingProxyType({prefix: tuple(values) for prefix, values in term["xrefs"].items()}),
        uberon_part_of=tuple(term["part_of"]),
        in_human_reference_atlas=term["in_human_reference_atlas"],
        models_3d=tuple(
            Model3D(url=m["url"], sex=Sex(m["sex"]) if m["sex"] else None, uberon=m["uberon"], label=m["label"])
            for m in term["models_3d"]
        ),
    )


@lru_cache(maxsize=1)
def load_anatomy() -> Anatomy:
    """Une el árbol curado (``structures.json``) con lo extraído de UBERON (``uberon_snapshot.json``)."""
    curated = load_data("structures.json")["structures"]
    snapshot = load_data("uberon_snapshot.json")
    terms = snapshot["terms"]
    missing = [entry["id"] for entry in curated if entry["id"] not in terms]
    if missing:
        raise ValueError(
            f"estructuras sin verificar contra UBERON: {missing}; ejecuta `python -m bodysim.sources.uberon`"
        )
    return Anatomy((_structure(e, terms[e["id"]]) for e in curated), snapshot["source"]["data_version"])
