from dataclasses import replace
from itertools import product

import pytest

from bodysim import Modifier, Person, Sex, body_composition, load_anatomy, organ_masses, reference_person
from bodysim.anatomy import load_data
from bodysim.scaling import SCALING_RULES

REFERENCE = load_data("icrp89_reference.json")
LIVER, BRAIN, ADIPOSE, BLOOD = "UBERON:0002107", "UBERON:0000955", "UBERON:0001013", "UBERON:0000178"
SUBCUTANEOUS, VISCERAL = "UBERON:0002190", "UBERON:0035818"


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
        expected = entry[sex.value]
        if entry["id"] == ADIPOSE:  # se reparte en subcutáneo y visceral
            assert ADIPOSE not in report.organs
            assert report.fat.adipose_tissue_g == pytest.approx(expected)
        elif expected is None:
            assert entry["id"] not in report.organs
        else:
            assert report.organs[entry["id"]].mass_g == pytest.approx(expected)
    assert 0 < report.unmodeled_mass_g < 0.1 * report.person.weight_kg * 1000


def test_weight_changes_lean_organs_and_fat_but_not_brain():
    base = reference_person(Sex.FEMALE)
    obese_report, reference_report = organ_masses(replace(base, weight_kg=95)), organ_masses(base)
    obese, reference = obese_report.organs, reference_report.organs
    assert obese[LIVER].mass_g > reference[LIVER].mass_g
    assert obese[BLOOD].mass_g > reference[BLOOD].mass_g
    assert obese[BRAIN].mass_g == pytest.approx(reference[BRAIN].mass_g)
    # El tejido adiposo crece proporcionalmente más que los órganos magros.
    fat_growth = obese_report.fat.adipose_tissue_g / reference_report.fat.adipose_tissue_g
    assert fat_growth > obese[LIVER].mass_g / reference[LIVER].mass_g


def test_measured_fat_separates_people_of_equal_weight():
    athlete = Person(Sex.MALE, 30, 180, 90, body_fat_fraction=0.12)
    sedentary = replace(athlete, body_fat_fraction=0.35)
    a, s = organ_masses(athlete), organ_masses(sedentary)
    assert a.fat.adipose_tissue_g / s.fat.adipose_tissue_g == pytest.approx(0.12 / 0.35)
    assert a.organs[LIVER].mass_g > s.organs[LIVER].mass_g
    assert a.organs[BRAIN].mass_g == s.organs[BRAIN].mass_g


def test_measuring_the_estimated_fat_changes_nothing():
    estimated = Person(Sex.FEMALE, 40, 163, 95)
    fraction = body_composition(estimated).fat_fraction
    measured = replace(estimated, body_fat_fraction=fraction)
    a, b = organ_masses(estimated).organs, organ_masses(measured).organs
    assert all(a[k].mass_g == pytest.approx(b[k].mass_g) for k in a)


def test_default_fat_split_is_typical_for_sex():
    for sex, share in ((Sex.MALE, 0.15), (Sex.FEMALE, 0.065)):
        fat = organ_masses(reference_person(sex)).fat
        assert not fat.visceral_measured and not fat.liver_fat_measured
        assert fat.visceral_fraction == pytest.approx(share)
        assert fat.subcutaneous_g + fat.visceral_g == pytest.approx(fat.adipose_tissue_g)
        assert not fat.steatosis


def test_measured_visceral_fat_moves_fat_out_of_subcutaneous():
    base = Person(Sex.MALE, 50, 175, 100)
    default, measured = organ_masses(base), organ_masses(replace(base, visceral_fat_kg=5.0))
    assert measured.fat.visceral_measured
    assert measured.organs[VISCERAL].mass_g == pytest.approx(5000)
    assert measured.fat.adipose_tissue_g == pytest.approx(default.fat.adipose_tissue_g)
    assert measured.organs[SUBCUTANEOUS].mass_g < default.organs[SUBCUTANEOUS].mass_g
    assert measured.modeled_mass_g == pytest.approx(default.modeled_mass_g)


def test_liver_fat_enlarges_liver_and_is_taken_from_subcutaneous_fat():
    base = Person(Sex.MALE, 50, 175, 100)
    healthy, fatty = organ_masses(base), organ_masses(replace(base, liver_fat_fraction=0.20))
    # Misma masa magra del hígado (98 % del de referencia sano), ahora con 20 % de grasa.
    assert fatty.organs[LIVER].mass_g == pytest.approx(healthy.organs[LIVER].mass_g * 0.98 / 0.80)
    added = fatty.organs[LIVER].mass_g - healthy.organs[LIVER].mass_g
    assert fatty.fat.liver_fat_excess_g == pytest.approx(added)
    assert fatty.organs[SUBCUTANEOUS].mass_g == pytest.approx(healthy.organs[SUBCUTANEOUS].mass_g - added)
    assert fatty.modeled_mass_g == pytest.approx(healthy.modeled_mass_g)
    assert fatty.fat.steatosis and fatty.fat.liver_fat_measured
    assert not organ_masses(replace(base, liver_fat_fraction=0.04)).fat.steatosis


def test_visceral_fat_cannot_exceed_adipose_tissue():
    athlete = Person(Sex.MALE, 30, 180, 75, body_fat_fraction=0.08, visceral_fat_kg=9.0)
    with pytest.raises(ValueError):
        organ_masses(athlete)


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
