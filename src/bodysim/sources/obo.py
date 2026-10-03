"""Lector mínimo del formato OBO 1.2, el que publica UBERON en cada release.

Solo extrae lo que el simulador necesita de cada término: nombre, definición,
sinónimos exactos, referencias cruzadas (FMA, SNOMED CT, MeSH...), relaciones
``is_a`` y ``part_of``, subconjuntos y los modelos 3D enlazados como
``depiction``. Las estrofas que no son ``[Term]`` (p. ej. ``[Typedef]``) se ignoran.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Iterator

_QUOTED = re.compile(r'"((?:[^"\\]|\\.)*)"')


@dataclass
class OboTerm:
    id: str
    name: str = ""
    definition: str = ""
    exact_synonyms: list[str] = field(default_factory=list)
    xrefs: list[str] = field(default_factory=list)
    is_a: list[str] = field(default_factory=list)
    part_of: list[str] = field(default_factory=list)
    subsets: list[str] = field(default_factory=list)
    depictions: list[str] = field(default_factory=list)
    obsolete: bool = False


def _quoted(value: str) -> str | None:
    match = _QUOTED.search(value)
    if match is None:
        return None
    return re.sub(r"\\(.)", r"\1", match.group(1))


def _apply(term: OboTerm, key: str, value: str) -> None:
    if key == "name":
        term.name = value.strip()
    elif key == "def":
        term.definition = _quoted(value) or ""
    elif key == "synonym":
        text = _quoted(value)
        scope = value[value.rfind('"') + 1 :].split()[:1]
        if text is not None and scope == ["EXACT"]:
            term.exact_synonyms.append(text)
    elif key == "xref":
        term.xrefs.append(value.split()[0])
    elif key == "is_a":
        term.is_a.append(value.split()[0])
    elif key == "relationship":
        relation, target = value.split()[:2]
        if relation == "part_of":
            term.part_of.append(target)
    elif key == "subset":
        term.subsets.append(value.strip())
    elif key == "property_value" and value.startswith("depiction "):
        url = _quoted(value)
        if url:
            term.depictions.append(url)
    elif key == "is_obsolete":
        term.obsolete = value.strip() == "true"


def parse_obo(lines: Iterable[str]) -> tuple[dict[str, str], Iterator[OboTerm]]:
    """Devuelve la cabecera del archivo y un iterador sobre sus términos."""
    iterator = iter(lines)
    header: dict[str, str] = {}
    first_stanza: str | None = None
    for raw in iterator:
        line = raw.rstrip("\n")
        if line.startswith("["):
            first_stanza = line.strip()
            break
        key, sep, value = line.partition(": ")
        if not sep:
            continue
        if key == "property_value":  # p. ej. "property_value: dcterms-license <url>"
            key, _, value = value.partition(" ")
        header.setdefault(key, value.strip())
    return header, _terms(first_stanza, iterator)


def _terms(stanza: str | None, lines: Iterator[str]) -> Iterator[OboTerm]:
    in_term = stanza == "[Term]"
    term: OboTerm | None = None
    for raw in lines:
        line = raw.rstrip("\n")
        if line.startswith("["):
            if term is not None:
                yield term
            term = None
            in_term = line.strip() == "[Term]"
            continue
        if not in_term:
            continue
        key, sep, value = line.partition(": ")
        if not sep:
            continue
        if key == "id":
            if term is None:
                term = OboTerm(id=value.strip())
        elif term is not None:
            _apply(term, key, value)
    if term is not None:
        yield term


def read_obo(path: str | Path) -> tuple[dict[str, str], dict[str, OboTerm]]:
    """Lee un archivo ``.obo`` completo y devuelve ``(cabecera, términos por id)``."""
    with open(path, encoding="utf-8") as handle:
        header, terms = parse_obo(handle)
        return header, {term.id: term for term in terms}
