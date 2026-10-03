"""Distribución de la grasa: subcutánea, visceral y hepática.

El escalado da el tejido adiposo total a partir de la masa grasa. Aquí se reparte:

- grasa visceral: la medida (DXA, TC o RM, en kg) o, si falta, una fracción
  típica del tejido adiposo según el sexo;
- grasa del hígado: la fracción medida por RM (PDFF). Por encima de la de un
  hígado sano aumenta la masa del hígado; desde el 5,56 % es esteatosis;
- grasa subcutánea: el resto.

Con la misma grasa total, más grasa visceral o hepática deja menos subcutánea.
Responde a la idea de que, cuando el tejido subcutáneo no puede expandirse más,
la grasa se desplaza a las vísceras y al hígado, donde se asocia a enfermedad
metabólica.

Los parámetros y su procedencia están en ``data/fat_distribution.json``.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from types import MappingProxyType
from typing import Mapping

from bodysim.anatomy import load_data
from bodysim.person import Sex

ADIPOSE = "UBERON:0001013"
SUBCUTANEOUS = "UBERON:0002190"
VISCERAL = "UBERON:0035818"
LIVER = "UBERON:0002107"


@dataclass(frozen=True)
class FatParameters:
    visceral_fraction: Mapping[Sex, float]  # del tejido adiposo, si no se midió
    healthy_liver_fat: float  # fracción de grasa del hígado de referencia
    steatosis_threshold: float


@lru_cache(maxsize=1)
def fat_parameters() -> FatParameters:
    data = load_data("fat_distribution.json")
    visceral = data["visceral_fraction_of_adipose_tissue"]
    return FatParameters(
        visceral_fraction=MappingProxyType({sex: visceral[sex.value] for sex in Sex}),
        healthy_liver_fat=data["healthy_liver_fat_fraction"]["value"],
        steatosis_threshold=data["steatosis_threshold"]["value"],
    )


@dataclass(frozen=True)
class FatDistribution:
    subcutaneous_g: float
    visceral_g: float
    visceral_measured: bool
    liver_fat_fraction: float
    liver_fat_measured: bool
    liver_fat_excess_g: float  # grasa del hígado por encima de la de un hígado sano

    @property
    def adipose_tissue_g(self) -> float:
        """Tejido adiposo total, incluida la grasa que pasó al hígado."""
        return self.subcutaneous_g + self.visceral_g + self.liver_fat_excess_g

    @property
    def visceral_fraction(self) -> float:
        return self.visceral_g / self.adipose_tissue_g

    @property
    def steatosis(self) -> bool:
        return self.liver_fat_fraction >= fat_parameters().steatosis_threshold
