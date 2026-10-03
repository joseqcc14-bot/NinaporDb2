from dataclasses import replace
from itertools import product

import pytest

from bodysim import Modifier, Person, Sex, body_composition, load_anatomy, organ_masses, reference_person
from bodysim.anatomy import load_data
from bodysim.scaling import SCALING_RULES

REFERENCE = load_data("icrp89_reference.json")
LIVER, BRAIN, ADIPOSE, BLOOD = "UBERON:0002107", "UBERON:0000955", "UBERON:0001013", "UBERON:0000178"


def test_reference_data_matches_anatomy():
    anatomy = load_anatomy()
    for entry in REFERENCE["organ_masses_g"]:
        assert entry["id"] in anatomy
        assert entry["verification"] in REFERENCE["verification_legend"]
        for sex in Sex:
            assert (entry[sex.value] is not None) == anatomy[entry["id"]].applies_to(sex), entry["id"]
    assert set(SCALING_RULES) <= {e["id"] for e in REFERENCE["organ_masses_g"]}


@pytest.mark.parametrize("sex", list(Sex))
def test_reference_person_recovers_icrp89(sex):
    report = organ_masses(reference_person(sex))
    for entry in REFERENCE["organ_masses_g"]:
        if entry[sex.value] is None:
            assert entry["id"] not in report.organs
        else:
            assert report.organs[entry["id"]].mass_g == pytest.approx(entry[sex.value])
    assert 0 < report.unmodeled_mass_g < 0.1 * report.person.weight_kg * 1000


def test_weight_changes_lean_organs_and_fat_but_not_brain():
    base = reference_person(Sex.FEMALE)
    obese = organ_masses(replace(base, weight_kg=95)).organs
    reference = organ_masses(base).organs
    assert obese[LIVER].mass_g > reference[LIVER].mass_g
    assert obese[BLOOD].mass_g > reference[BLOOD].mass_g
    assert obese[BRAIN].mass_g == pytest.approx(reference[BRAIN].mass_g)
    # El tejido adiposo crece proporcionalmente más que los órganos magros.
    assert obese[ADIPOSE].mass_g / reference[ADIPOSE].mass_g > obese[LIVER].mass_g / reference[LIVER].mass_g


def test_measured_fat_separates_people_of_equal_weight():
    athlete = Person(Sex.MALE, 30, 180, 90, body_fat_fraction=0.12)
    sedentary = replace(athlete, body_fat_fraction=0.35)
    a, s = organ_masses(athlete).organs, organ_masses(sedentary).organs
    assert a[ADIPOSE].mass_g < s[ADIPOSE].mass_g
    assert a[LIVER].mass_g > s[LIVER].mass_g
    assert a[BRAIN].mass_g == s[BRAIN].mass_g
    assert a[ADIPOSE].mass_g / s[ADIPOSE].mass_g == pytest.approx(0.12 / 0.35)


def test_measuring_the_estimated_fat_changes_nothing():
    estimated = Person(Sex.FEMALE, 40, 163, 95)
    fraction = body_composition(estimated).fat_fraction
    measured = replace(estimated, body_fat_fraction=fraction)
    a, b = organ_masses(estimated).organs, organ_masses(measured).organs
    assert all(a[k].mass_g == pytest.approx(b[k].mass_g) for k in a)


def test_genotype_alone_does_not_change_anatomy():
    base = reference_person(Sex.MALE)
    with_genotype = replace(base, genotype={"rs429358": "CC"})
    a, b = organ_masses(base).organs, organ_masses(with_genotype).organs
    assert {k: v.mass_g for k, v in a.items()} == {k: v.mass_g for k, v in b.items()}


def test_modifiers_only_touch_their_structure():
    person = Person(Sex.MALE, 50, 180, 90)
    plain = organ_masses(person).organs
    modified = organ_masses(
        person,
        [Modifier(LIVER, 1.5, "prueba"), Modifier(LIVER, 1.2, "prueba 2")],
    ).organs
    assert modified[LIVER].mass_g == pytest.approx(plain[LIVER].mass_g * 1.8)
    assert all(modified[k].mass_g == plain[k].mass_g for k in plain if k != LIVER)


def test_invalid_modifiers():
    with pytest.raises(ValueError):
        Modifier(LIVER, 0, "prueba")
    with pytest.raises(ValueError):  # útero en un hombre
        organ_masses(reference_person(Sex.MALE), [Modifier("UBERON:0000995", 1.1, "prueba")])
    with pytest.raises(ValueError):  # un sistema no tiene masa propia
        organ_masses(reference_person(Sex.MALE), [Modifier("UBERON:0004535", 1.1, "prueba")])


def _plausible_people():
    grid = product(
        Sex,
        [150, 165, 176, 190, 200, 230],
        [11, 11.5, 12, 13, 13.5, 14, 16, 22, 30, 45, 60, 100],
        [None, 0.03, 0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7],
    )
    for sex, height_cm, bmi, body_fat in grid:
        try:
            yield Person(sex, 45, height_cm, bmi * (height_cm / 100) ** 2, body_fat_fraction=body_fat)
        except ValueError:
            continue  # combinación incompatible con la vida: Person la rechaza


def test_masses_are_positive_and_fit_in_body_weight():
    people = list(_plausible_people())
    assert len(people) > 500
    for person in people:
        report = organ_masses(person)
        assert all(organ.mass_g > 0 for organ in report.organs.values()), person
        assert report.unmodeled_mass_g > 0, person
