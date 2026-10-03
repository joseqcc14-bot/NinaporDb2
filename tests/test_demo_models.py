"""Los modelos 3D de la demo son coherentes con la anatomía de bodysim."""

import base64
import json
from array import array
from pathlib import Path

import pytest

from bodysim import load_anatomy

MODELS = Path(__file__).resolve().parents[1] / "demo" / "models"
LAYERS = {
    "piel", "esqueleto", "musculos", "nervioso", "cardiovascular", "respiratorio",
    "digestivo", "urinario", "reproductor", "linfatico",
}


def _decode(entry):
    positions = array("H", base64.b64decode(entry["positions"]))
    indices = array("I" if entry["index_bits"] == 32 else "H", base64.b64decode(entry["indices"]))
    return len(positions) // 3, indices


@pytest.mark.parametrize("sex", ["male", "female"])
def test_model_matches_anatomy(sex):
    data = json.loads((MODELS / f"{sex}.json").read_text(encoding="utf-8"))
    anatomy = load_anatomy()
    assert data["format"] == "bodysim-mesh-1" and "CC BY 4.0" in data["source"]
    keys = [mesh["key"] for mesh in data["meshes"]]
    assert len(keys) == len(set(keys))
    for mesh in data["meshes"]:
        assert mesh["layer"] in LAYERS, mesh["key"]
        assert mesh["name_es"], mesh["key"]
        assert mesh["model_id"] is None or mesh["model_id"] in anatomy, mesh["key"]
        vertices, indices = _decode(mesh)
        assert len(indices) % 3 == 0 and max(indices) < vertices, mesh["key"]
    by_key = {mesh["key"]: mesh for mesh in data["meshes"]}
    assert by_key["liver"]["model_id"] == "UBERON:0002107"
    assert by_key["heart"]["model_id"] == "UBERON:0000948"
    assert by_key["skin"]["layer"] == "piel"
