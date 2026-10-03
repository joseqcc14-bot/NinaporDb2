import pytest

from bodysim import Person, Sex, body_composition
from bodysim.anthropometry import (
    blood_volume,
    bmi,
    bsa_dubois,
    bsa_mosteller,
    fat_free_mass,
    fat_mass,
    total_body_water,
)

# Valores calculados a mano con los coeficientes publicados.
MAN = Person(Sex.MALE, age_years=40, height_cm=180, weight_kg=81)  # IMC 25 exacto
WOMAN = Person(Sex.FEMALE, age_years=40, height_cm=160, weight_kg=64)  # IMC 25 exacto


def test_bmi():
    assert bmi(MAN) == pytest.approx(25.0)
    assert bmi(WOMAN) == pytest.approx(25.0)


def test_body_surface_area():
    assert bsa_mosteller(Person(Sex.MALE, 40, 180, 80)) == pytest.approx(2.0)
    assert bsa_dubois(Person(Sex.MALE, 40, 180, 80)) == pytest.approx(1.9958, abs=1e-3)


def test_fat_free_mass_janmahasatian():
    assert fat_free_mass(MAN) == pytest.approx(9270 * 81 / 12080)  # 62.16 kg
    assert fat_free_mass(WOMAN) == pytest.approx(9270 * 64 / 14880)  # 39.87 kg
    assert fat_mass(MAN) == pytest.approx(81 - 9270 * 81 / 12080)


def test_blood_volume_nadler():
    assert blood_volume(MAN) == pytest.approx(5.35125, abs=1e-4)
    assert blood_volume(WOMAN) == pytest.approx(0.3561 * 1.6**3 + 0.03308 * 64 + 0.1833)


def test_total_body_water_watson():
    assert total_body_water(MAN) == pytest.approx(45.2048, abs=1e-4)
    assert total_body_water(WOMAN) == pytest.approx(30.7894, abs=1e-4)


def test_body_composition_is_consistent():
    composition = body_composition(WOMAN)
    assert composition.fat_mass_kg + composition.fat_free_mass_kg == pytest.approx(WOMAN.weight_kg)
    assert 0 < composition.fat_fraction < 1
