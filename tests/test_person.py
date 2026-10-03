from dataclasses import replace

import pytest

from bodysim import Person, Sex


def test_variables_are_independent():
    base = Person(Sex.FEMALE, age_years=40, height_cm=163, weight_kg=60, genotype={"rs429358": "CT"})
    heavier = replace(base, weight_kg=95)
    assert (heavier.sex, heavier.age_years, heavier.height_cm) == (base.sex, base.age_years, base.height_cm)
    assert heavier.genotype == base.genotype
    assert replace(base, genotype={}).weight_kg == base.weight_kg


def test_sex_accepts_string():
    assert Person("male", 30, 176, 73).sex is Sex.MALE


def test_genotype_is_read_only_copy():
    calls = {"rs429358": "CT"}
    person = Person(Sex.MALE, 30, 176, 73, genotype=calls)
    calls["rs7412"] = "CC"
    assert dict(person.genotype) == {"rs429358": "CT"}
    with pytest.raises(TypeError):
        person.genotype["rs7412"] = "CC"


def test_body_fat_is_optional_and_independent():
    estimated = Person(Sex.MALE, 30, 180, 90)
    athlete = replace(estimated, body_fat_fraction=0.12)
    assert estimated.body_fat_fraction is None
    assert (athlete.height_cm, athlete.weight_kg) == (estimated.height_cm, estimated.weight_kg)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"age_years": 10},
        {"age_years": float("nan")},
        {"height_cm": 40},
        {"weight_kg": 500},
        {"height_cm": 200, "weight_kg": 35},  # IMC 8.75
        {"weight_kg": 39},  # IMC 12.6: por debajo del límite de supervivencia masculino (13)
        {"body_fat_fraction": 0.75},
        {"body_fat_fraction": 0.01},
        {"weight_kg": 45, "body_fat_fraction": 0.2},  # 11.6 kg/m² de masa libre de grasa
        {"genotype": {"rs429358": ""}},
    ],
)
def test_rejects_implausible_values(kwargs):
    values = {"sex": Sex.MALE, "age_years": 30, "height_cm": 176, "weight_kg": 73, **kwargs}
    with pytest.raises(ValueError):
        Person(**values)


def test_survival_limits_depend_on_sex():
    # IMC 12: incompatible con la vida en hombres, no en mujeres (Henry 1990).
    with pytest.raises(ValueError):
        Person(Sex.MALE, 30, 176, 37.2)
    assert Person(Sex.FEMALE, 30, 176, 37.2).weight_kg == 37.2
