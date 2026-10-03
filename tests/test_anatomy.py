import pytest

from bodysim import Kind, Sex, Structure, load_anatomy
from bodysim.anatomy import Anatomy, load_data

ANATOMY = load_anatomy()


def test_every_curated_structure_is_verified_against_uberon():
    snapshot = load_data("uberon_snapshot.json")
    assert snapshot["source"]["data_version"].startswith("uberon/releases/")
    curated = load_data("structures.json")["structures"]
    assert len(ANATOMY) == len(curated)
    for structure in ANATOMY:
        assert structure.id.startswith("UBERON:")
        assert structure.label_en, structure.id


def test_tree_shape():
    assert ANATOMY.root.id == "UBERON:0000468"
    assert ANATOMY.root.kind is Kind.ORGANISM
    for system in ANATOMY.of_kind(Kind.SYSTEM):
        assert system.parent == ANATOMY.root.id
    for structure in ANATOMY.of_kind(Kind.ORGAN) + ANATOMY.of_kind(Kind.TISSUE):
        assert ANATOMY.ancestors(structure.id)[-1] == ANATOMY.root


def test_known_links():
    heart = ANATOMY["UBERON:0000948"]
    assert heart.name_es == "corazón" and heart.label_en == "heart"
    assert ANATOMY.ancestors(heart.id)[0].id == "UBERON:0004535"  # sistema cardiovascular
    assert heart.xrefs["FMA"] == ("FMA:7088",)
    assert ANATOMY.find_xref("FMA:7088") is heart
    assert heart.in_human_reference_atlas
    assert {m.sex for m in heart.models_3d} == {Sex.MALE, Sex.FEMALE}
    assert all(m.url.endswith(".glb") for m in heart.models_3d)


def test_bilateral_models_come_from_lateral_subclasses():
    kidney = ANATOMY["UBERON:0002113"]
    assert kidney.bilateral
    assert {m.label for m in kidney.models_for(Sex.FEMALE)} == {"left kidney", "right kidney"}


def test_for_sex_filters_sex_specific_structures():
    male, female = ANATOMY.for_sex(Sex.MALE), ANATOMY.for_sex(Sex.FEMALE)
    assert "UBERON:0000473" in male and "UBERON:0000473" not in female  # testículo
    assert "UBERON:0000995" in female and "UBERON:0000995" not in male  # útero
    assert "UBERON:0000310" in male and "UBERON:0000310" in female  # mama


def test_unknown_structure():
    with pytest.raises(KeyError):
        ANATOMY["UBERON:9999999"]


def test_rejects_malformed_trees():
    root = Structure("A", "a", Kind.ORGANISM, None)
    with pytest.raises(ValueError):
        Anatomy([root, Structure("B", "b", Kind.ORGAN, "Z")])  # padre inexistente
    with pytest.raises(ValueError):
        Anatomy([root, root])  # duplicado
    with pytest.raises(ValueError):
        Anatomy([root, Structure("B", "b", Kind.ORGAN, "C"), Structure("C", "c", Kind.ORGAN, "B")])  # ciclo
