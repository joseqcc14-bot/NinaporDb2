"""Masa de cada órgano para un individuo concreto.

Parte de las masas de referencia de ICRP 89 (hombre de 176 cm y 73 kg, mujer de
163 cm y 60 kg) y las escala según la composición corporal del individuo::

    masa = masa_ref × (X_individuo / X_referencia) ** b × factores de los modificadores

donde X es la base de escalado de cada estructura. Supuestos de esta versión,
todos editables en ``SCALING_RULES``:

- órganos y tejidos magros escalan con la masa libre de grasa (b = 1);
- encéfalo y médula espinal no escalan con el tamaño corporal en el adulto;
- la sangre escala con el volumen sanguíneo (Nadler);
- el tejido adiposo y la mama escalan con la masa grasa.

La persona de referencia de cada sexo recupera exactamente los valores de ICRP 89.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from types import MappingProxyType
from typing import Iterable, Mapping

from bodysim.anatomy import Anatomy, Structure, load_anatomy, load_data
from bodysim.anthropometry import blood_volume, fat_free_mass, fat_mass
from bodysim.person import Person, Sex


class Basis(str, Enum):
    FAT_FREE_MASS = "fat_free_mass"
    FAT_MASS = "fat_mass"
    BLOOD_VOLUME = "blood_volume"
    CONSTANT = "constant"


@dataclass(frozen=True)
class ScalingRule:
    basis: Basis
    exponent: float = 1.0


DEFAULT_RULE = ScalingRule(Basis.FAT_FREE_MASS)
SCALING_RULES: Mapping[str, ScalingRule] = MappingProxyType(
    {
        "UBERON:0000955": ScalingRule(Basis.CONSTANT),  # encéfalo
        "UBERON:0002240": ScalingRule(Basis.CONSTANT),  # médula espinal
        "UBERON:0000178": ScalingRule(Basis.BLOOD_VOLUME),  # sangre
        "UBERON:0001013": ScalingRule(Basis.FAT_MASS),  # tejido adiposo
        "UBERON:0000310": ScalingRule(Basis.FAT_MASS),  # mama, mayoritariamente adiposa
    }
)

_BASIS_FUNCTIONS = {
    Basis.FAT_FREE_MASS: fat_free_mass,
    Basis.FAT_MASS: fat_mass,
    Basis.BLOOD_VOLUME: blood_volume,
    Basis.CONSTANT: lambda person: 1.0,
}


@dataclass(frozen=True)
class Modifier:
    """Factor multiplicativo sobre la masa de una estructura.

    Es la puerta de entrada de las capas siguientes: una variante genética o una
    enfermedad se traducen en modificadores sobre estructuras concretas, sin
    tocar las variables independientes del individuo.
    """

    structure_id: str
    mass_factor: float
    origin: str  # p. ej. "genética: MYH7 p.R403Q" o "enfermedad: esteatosis hepática"

    def __post_init__(self) -> None:
        if not (math.isfinite(self.mass_factor) and self.mass_factor > 0):
            raise ValueError(f"mass_factor debe ser un número positivo: {self.mass_factor}")


@dataclass(frozen=True)
class OrganMass:
    structure: Structure
    reference_g: float
    mass_g: float
    rule: ScalingRule
    verification: str  # estado del valor de referencia, ver icrp89_reference.json


@dataclass(frozen=True)
class MassReport:
    person: Person
    organs: Mapping[str, OrganMass]

    @property
    def modeled_mass_g(self) -> float:
        return sum(organ.mass_g for organ in self.organs.values())

    @property
    def unmodeled_mass_g(self) -> float:
        """Peso corporal no asignado a estructuras modeladas (ganglios, ojos, contenido digestivo...)."""
        return self.person.weight_kg * 1000.0 - self.modeled_mass_g


@lru_cache(maxsize=1)
def _reference() -> dict:
    return load_data("icrp89_reference.json")


def reference_person(sex: Sex) -> Person:
    """Adulto de referencia de ICRP 89. La edad no interviene en ninguna base de escalado."""
    body = _reference()["reference_individuals"][Sex(sex).value]
    return Person(sex, age_years=35, height_cm=body["height_cm"], weight_kg=body["weight_kg"])


def organ_masses(
    person: Person, modifiers: Iterable[Modifier] = (), anatomy: Anatomy | None = None
) -> MassReport:
    anatomy = (anatomy or load_anatomy()).for_sex(person.sex)
    reference = reference_person(person.sex)
    entries = [e for e in _reference()["organ_masses_g"] if e[person.sex.value] is not None]

    factors: dict[str, float] = {}
    with_mass = {e["id"] for e in entries}
    for modifier in modifiers:
        if modifier.structure_id not in with_mass:
            raise ValueError(f"{modifier.structure_id} no tiene masa modelada para sexo {person.sex.value}")
        factors[modifier.structure_id] = factors.get(modifier.structure_id, 1.0) * modifier.mass_factor

    organs = {}
    for entry in entries:
        structure_id = entry["id"]
        reference_g = entry[person.sex.value]
        rule = SCALING_RULES.get(structure_id, DEFAULT_RULE)
        basis = _BASIS_FUNCTIONS[rule.basis]
        ratio = basis(person) / basis(reference)
        organs[structure_id] = OrganMass(
            structure=anatomy[structure_id],
            reference_g=reference_g,
            mass_g=reference_g * ratio**rule.exponent * factors.get(structure_id, 1.0),
            rule=rule,
            verification=entry["verification"],
        )
    return MassReport(person, MappingProxyType(organs))
