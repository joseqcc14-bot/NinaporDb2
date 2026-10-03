"""Variables independientes del individuo simulado.

Sexo, edad, talla, peso y genotipo son entradas independientes: ninguna se
calcula a partir de otra y cambiar una no altera las demás. Todo lo que depende
de ellas (IMC, masa libre de grasa, masa de cada órgano...) se calcula en otras
capas y nunca se guarda aquí, para que no pueda quedar desactualizado.

Para explorar el efecto de una sola variable se usa ``dataclasses.replace``::

    base = Person(Sex.FEMALE, age_years=40, height_cm=163, weight_kg=60)
    obesa = replace(base, weight_kg=95)  # misma talla, edad y genotipo
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Mapping

# Rangos admitidos. Las ecuaciones de composición corporal están validadas en adultos.
AGE_RANGE = (18.0, 100.0)
HEIGHT_RANGE_CM = (120.0, 230.0)
WEIGHT_RANGE_KG = (30.0, 300.0)
# Talla y peso son independientes, pero su combinación debe ser compatible con la vida.
BMI_RANGE = (10.0, 100.0)


class Sex(str, Enum):
    """Sexo biológico; selecciona los valores de referencia y las ecuaciones."""

    MALE = "male"
    FEMALE = "female"


def _check_range(name: str, value: float, bounds: tuple[float, float]) -> None:
    low, high = bounds
    if not (math.isfinite(value) and low <= value <= high):
        raise ValueError(f"{name}={value} fuera del rango validado [{low}, {high}]")


@dataclass(frozen=True)
class Person:
    sex: Sex
    age_years: float
    height_cm: float
    weight_kg: float
    # Variante -> genotipo, p. ej. {"rs429358": "CT"}. La capa anatómica no lo lee
    # directamente: la capa genética lo traducirá a ``Modifier`` sobre estructuras.
    genotype: Mapping[str, str] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "sex", Sex(self.sex))
        _check_range("age_years", self.age_years, AGE_RANGE)
        _check_range("height_cm", self.height_cm, HEIGHT_RANGE_CM)
        _check_range("weight_kg", self.weight_kg, WEIGHT_RANGE_KG)
        _check_range("IMC", self.weight_kg / self.height_m**2, BMI_RANGE)
        genotype = dict(self.genotype)
        for variant, call in genotype.items():
            if not (isinstance(variant, str) and variant and isinstance(call, str) and call):
                raise ValueError(f"genotipo inválido: {variant!r} -> {call!r}")
        object.__setattr__(self, "genotype", MappingProxyType(genotype))

    @property
    def height_m(self) -> float:
        return self.height_cm / 100.0
