from bodysim.sources.obo import parse_obo
from bodysim.sources.uberon import build_snapshot

SAMPLE = r'''format-version: 1.2
data-version: uberon/releases/2099-01-01/uberon-basic.owl
property_value: dc-title "Uber-anatomy ontology" xsd:string
property_value: dcterms-license http://creativecommons.org/licenses/by/3.0/

[Term]
id: UBERON:0002113
name: kidney
def: "An organ that \"filters\" blood ! not a comment" [FMA:7203]
subset: human_reference_atlas
synonym: "renal organ" EXACT []
synonym: "nephros" RELATED []
xref: FMA:7203
xref: UMLS:C0022646 {source="ncithesaurus:Kidney"}
is_a: UBERON:0000062 ! organ
relationship: part_of UBERON:0001008 {source="FMA"} ! renal system
relationship: develops_from UBERON:0003918 ! kidney mesenchyme

[Term]
id: UBERON:0004538
name: left kidney
is_a: UBERON:0002113 ! kidney
property_value: depiction "https://cdn.humanatlas.io/digital-objects/ref-organ/kidney-female-left/v1.3/assets/3d-vh-f-kidney-l.glb" xsd:anyURI
property_value: depiction "https://example.org/kidney.png" xsd:anyURI

[Term]
id: UBERON:0009999
name: obsolete thing
is_obsolete: true
is_a: UBERON:0002113

[Typedef]
id: part_of
name: part of
'''


def parse(text):
    header, terms = parse_obo(text.splitlines(keepends=True))
    return header, {t.id: t for t in terms}


def test_header():
    header, _ = parse(SAMPLE)
    assert header["data-version"] == "uberon/releases/2099-01-01/uberon-basic.owl"
    assert header["dcterms-license"] == "http://creativecommons.org/licenses/by/3.0/"


def test_term_fields():
    _, terms = parse(SAMPLE)
    assert set(terms) == {"UBERON:0002113", "UBERON:0004538", "UBERON:0009999"}  # Typedef ignorado
    kidney = terms["UBERON:0002113"]
    assert kidney.name == "kidney"
    assert kidney.definition == 'An organ that "filters" blood ! not a comment'
    assert kidney.exact_synonyms == ["renal organ"]
    assert kidney.xrefs == ["FMA:7203", "UMLS:C0022646"]
    assert kidney.is_a == ["UBERON:0000062"]
    assert kidney.part_of == ["UBERON:0001008"]
    assert kidney.subsets == ["human_reference_atlas"]
    assert terms["UBERON:0009999"].obsolete


def test_snapshot_collects_models_from_subclasses():
    header, terms = parse(SAMPLE)
    snapshot = build_snapshot(header, terms, ["UBERON:0002113"])
    kidney = snapshot["terms"]["UBERON:0002113"]
    assert snapshot["source"]["data_version"].endswith("2099-01-01/uberon-basic.owl")
    assert kidney["xrefs"] == {"FMA": ["FMA:7203"], "UMLS": ["UMLS:C0022646"]}
    assert kidney["in_human_reference_atlas"]
    assert kidney["models_3d"] == [
        {
            "url": "https://cdn.humanatlas.io/digital-objects/ref-organ/kidney-female-left/v1.3/assets/3d-vh-f-kidney-l.glb",
            "sex": "female",
            "uberon": "UBERON:0004538",
            "label": "left kidney",
        }
    ]


def test_snapshot_rejects_unknown_or_obsolete_terms():
    header, terms = parse(SAMPLE)
    for missing in ("UBERON:0000000", "UBERON:0009999"):
        try:
            build_snapshot(header, terms, [missing])
        except ValueError as error:
            assert missing in str(error)
        else:
            raise AssertionError(f"{missing} debería fallar")
