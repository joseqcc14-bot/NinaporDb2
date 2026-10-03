"""Composición corporal derivada de las variables independientes.

Ecuaciones publicadas y de uso clínico habitual; las referencias van en cada
función. Todas reciben un ``Person`` y no guardan estado.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from bodysim.person import Person, Sex


def bmi(person: Person) -> float:
    """Índice de masa corporal (kg/m²)."""
    return person.weight_kg / person.height_m**2


def bsa_mosteller(person: Person) -> float:
    """Superficie corporal (m²). Mosteller, N Engl J Med 1987;317:1098."""
    return math.sqrt(person.height_cm * person.weight_kg / 3600.0)


def bsa_dubois(person: Person) -> float:
    """Superficie corporal (m²). Du Bois & Du Bois, Arch Intern Med 1916;17:863."""
    return 0.007184 * person.weight_kg**0.425 * person.height_cm**0.725


def fat_free_mass(person: Person) -> float:
    """Masa libre de grasa (kg). Janmahasatian et al., Clin Pharmacokinet 2005;44:1051.

    Validada también en obesidad, a diferencia de las fórmulas lineales de masa magra.
    """
    if person.sex is Sex.MALE:
        return 9270.0 * person.weight_kg / (6680.0 + 216.0 * bmi(person))
    return 9270.0 * person.weight_kg / (8780.0 + 244.0 * bmi(person))


def fat_mass(person: Person) -> float:
    """Masa grasa (kg): peso menos masa libre de grasa."""
    return person.weight_kg - fat_free_mass(person)


def blood_volume(person: Person) -> float:
    """Volumen sanguíneo total (L). Nadler et al., Surgery 1962;51:224."""
    if person.sex is Sex.MALE:
        return 0.3669 * person.height_m**3 + 0.03219 * person.weight_kg + 0.6041
    return 0.3561 * person.height_m**3 + 0.03308 * person.weight_kg + 0.1833


def total_body_water(person: Person) -> float:
    """Agua corporal total (L). Watson et al., Am J Clin Nutr 1980;33:27."""
    if person.sex is Sex.MALE:
        return 2.447 - 0.09516 * person.age_years + 0.1074 * person.height_cm + 0.3362 * person.weight_kg
    return -2.097 + 0.1069 * person.height_cm + 0.2466 * person.weight_kg


@dataclass(frozen=True)
class BodyComposition:
    bmi: float
    bsa_m2: float
    fat_free_mass_kg: float
    fat_mass_kg: float
    blood_volume_l: float
    total_body_water_l: float

    @property
    def fat_fraction(self) -> float:
        return self.fat_mass_kg / (self.fat_mass_kg + self.fat_free_mass_kg)


def body_composition(person: Person) -> BodyComposition:
    return BodyComposition(
        bmi=bmi(person),
        bsa_m2=bsa_mosteller(person),
        fat_free_mass_kg=fat_free_mass(person),
        fat_mass_kg=fat_mass(person),
        blood_volume_l=blood_volume(person),
        total_body_water_l=total_body_water(person),
    )
