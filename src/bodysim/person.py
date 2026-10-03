"""Variables independientes del individuo simulado.

Sexo, edad, talla, peso, grasa corporal y genotipo son entradas independientes:
ninguna se calcula a partir de otra y cambiar una no altera las demás. Todo lo
que depende de ellas (IMC, masa libre de grasa, masa de cada órgano...) se
calcula en otras capas y nunca se guarda aquí, para que no pueda quedar
desactualizado.

La grasa corporal es opcional porque no siempre se mide. Si se omite, se estima
a partir de sexo, talla y peso, y dos personas con la misma talla y el mismo
peso tienen la misma composición. Si se conoce (DXA, bioimpedancia, pliegues
cutáneos), un atleta y una persona sedentaria del mismo peso dan anatomías
distintas.

Para explorar el efecto de una sola variable se usa ``dataclasses.replace``::

    base = Person(Sex.FEMALE, age_years=40, height_cm=163, weight_kg=60, body_fat_fraction=0.30)
    replace(base, weight_kg=95)            # mismo % de grasa: crecen la grasa y la masa magra
    replace(base, body_fat_fraction=0.40)  # mismo peso: más grasa y menos masa magra
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
BODY_FAT_RANGE = (0.03, 0.70)
MAX_BMI = 100.0


class Sex(str, Enum):
    """Sexo biológico; selecciona los valores de referencia y las ecuaciones."""

    MALE = "male"
    FEMALE = "female"


# Talla, peso y grasa son independientes, pero su combinación debe ser compatible
# con la vida. IMC mínimo de supervivencia: Henry, Eur J Clin Nutr 1990;44:329.
MIN_BMI = {Sex.MALE: 13.0, Sex.FEMALE: 11.0}
# Grasa esencial (ACSM). Con el IMC mínimo fija la masa libre de grasa por m²
# más baja compatible con la vida, que acota la grasa medida.
ESSENTIAL_FAT = {Sex.MALE: 0.03, Sex.FEMALE: 0.12}


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
    # Fracción de grasa corporal medida (0-1). None: se estima desde sexo, talla y peso.
    body_fat_fraction: float | None = None
    # Variante -> genotipo, p. ej. {"rs429358": "CT"}. La capa anatómica no lo lee
    # directamente: la capa genética lo traducirá a ``Modifier`` sobre estructuras.
    genotype: Mapping[str, str] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "sex", Sex(self.sex))
        _check_range("age_years", self.age_years, AGE_RANGE)
        _check_range("height_cm", self.height_cm, HEIGHT_RANGE_CM)
        _check_range("weight_kg", self.weight_kg, WEIGHT_RANGE_KG)
        bmi = self.weight_kg / self.height_m**2
        _check_range("IMC", bmi, (MIN_BMI[self.sex], MAX_BMI))
        if self.body_fat_fraction is not None:
            _check_range("body_fat_fraction", self.body_fat_fraction, BODY_FAT_RANGE)
            ffmi = bmi * (1.0 - self.body_fat_fraction)
            min_ffmi = MIN_BMI[self.sex] * (1.0 - ESSENTIAL_FAT[self.sex])
            if ffmi < min_ffmi:
                raise ValueError(
                    f"masa libre de grasa de {ffmi:.1f} kg/m², por debajo de la mínima compatible con la vida "
                    f"({min_ffmi:.1f} kg/m²)"
                )
        genotype = dict(self.genotype)
        for variant, call in genotype.items():
            if not (isinstance(variant, str) and variant and isinstance(call, str) and call):
                raise ValueError(f"genotipo inválido: {variant!r} -> {call!r}")
        object.__setattr__(self, "genotype", MappingProxyType(genotype))

    @property
    def height_m(self) -> float:
        return self.height_cm / 100.0
