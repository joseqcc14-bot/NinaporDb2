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


@pytest.mark.parametrize(
    "kwargs",
    [
        {"age_years": 10},
        {"age_years": float("nan")},
        {"height_cm": 40},
        {"weight_kg": 500},
        {"height_cm": 200, "weight_kg": 35},  # IMC 8.75
        {"genotype": {"rs429358": ""}},
    ],
)
def test_rejects_out_of_range_values(kwargs):
    values = {"sex": Sex.MALE, "age_years": 30, "height_cm": 176, "weight_kg": 73, **kwargs}
    with pytest.raises(ValueError):
        Person(**values)
