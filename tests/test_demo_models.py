"""Los modelos 3D de la demo son coherentes con la anatomía de bodysim."""

import base64
import json
from array import array
from pathlib import Path

import pytest

from bodysim import load_anatomy

MODELS = Path(__file__).resolve().parents[1] / "demo" / "models"
LAYERS = {
    "piel", "esqueleto", "articulaciones", "musculos", "inserciones", "cardiovascular", "encefalo",
    "nervios", "sentidos", "respiratorio", "digestivo", "urinario", "reproductor", "endocrino", "linfatico",
}
# Hombre: Z-Anatomy (derivado de BodyParts3D). Mujer: Human Reference Atlas.
LICENSES = {"male": "CC BY-SA 4.0", "female": "CC BY 4.0"}


def _decode(entry):
    positions = array("H", base64.b64decode(entry["positions"]))
    indices = array("I" if entry["index_bits"] == 32 else "H", base64.b64decode(entry["indices"]))
    return len(positions) // 3, indices


def _body(sex):
    manifest = json.loads((MODELS / sex / "manifest.json").read_text(encoding="utf-8"))
    layers = {
        layer["key"]: json.loads((MODELS / sex / layer["file"]).read_text(encoding="utf-8"))
        for layer in manifest["layers"]
    }
    return manifest, layers


def _meshes(layers):
    return {mesh["key"]: mesh for data in layers.values() for mesh in data["meshes"]}


@pytest.mark.parametrize("sex", ["male", "female"])
def test_body_matches_anatomy(sex):
    manifest, layers = _body(sex)
    anatomy = load_anatomy()
    assert manifest["format"] == "bodysim-body-1" and manifest["sex"] == sex
    assert LICENSES[sex] in manifest["source"]
    assert set(layers) <= LAYERS
    keys = []
    for info in manifest["layers"]:
        data = layers[info["key"]]
        assert data["format"] == "bodysim-mesh-1" and data["layer"] == info["key"]
        assert LICENSES[sex] in data["source"]
        assert len(data["meshes"]) == info["parts"]
        assert (MODELS / sex / info["file"]).stat().st_size == info["bytes"]
        triangles = 0
        for mesh in data["meshes"]:
            assert mesh["layer"] == info["key"], mesh["key"]
            assert mesh["name_es"] or mesh["label_en"], mesh["key"]
            assert mesh["model_id"] is None or mesh["model_id"] in anatomy, mesh["key"]
            vertices, indices = _decode(mesh)
            assert len(indices) % 3 == 0 and max(indices) < vertices, mesh["key"]
            triangles += len(indices) // 3
            keys.append(mesh["key"])
        assert triangles == info["triangles"]
    assert len(keys) == len(set(keys))
    low, high = manifest["bounds"]["min"], manifest["bounds"]["max"]
    assert 1.5 < high[1] - low[1] < 1.9  # estatura de referencia del atlas, en metros


def test_male_atlas_is_complete():
    """Z-Anatomy: huesos, articulaciones, músculos e inserciones, vasos, nervios, encéfalo y sentidos."""
    manifest, layers = _body("male")
    assert set(layers) == LAYERS
    parts = {info["key"]: info["parts"] for info in manifest["layers"]}
    assert parts["esqueleto"] > 250 and parts["musculos"] > 450 and parts["cardiovascular"] > 600
    assert parts["encefalo"] > 250 and parts["nervios"] > 200 and parts["sentidos"] >= 40
    assert parts["articulaciones"] > 400 and parts["inserciones"] > 700
    meshes = _meshes(layers)
    named = sum(1 for mesh in meshes.values() if mesh["name_es"])
    assert named / len(meshes) > 0.95
    assert meshes["Liver"]["model_id"] == "UBERON:0002107"
    assert meshes["Left ventricle"]["model_id"] == "UBERON:0000948"
    assert meshes["Femur.r"]["layer"] == "esqueleto" and meshes["Femur.r"]["uberon"] == "UBERON:0000981"
    assert meshes["Sciatic nerve.l"]["name_es"] == "nervio ciático izquierdo"
    assert meshes["Optic nerve (II).r"]["name_es"] == "nervio óptico derecho (II)"
    assert meshes["Optic nerve (II).r"]["uberon"] == "UBERON:0000941"
    assert meshes["Stapes.l"]["name_es"] == "estribo izquierdo"
    assert meshes["Iris.r"]["name_es"] == "iris derecho"
    assert meshes["Cochlea.r"]["layer"] == "sentidos"
    assert meshes["Anterior cruciate ligament.r"]["name_es"] == "ligamento cruzado anterior derecho"
    # Orígenes e inserciones: el pectoral menor va corregido (el atlas los invierte).
    assert meshes["Brachialis muscle.or"]["name_es"] == "origen del músculo braquial derecho"
    assert meshes["Brachialis muscle.or"]["group"] == "flexores"
    assert meshes["Pectoralis minor muscle.or"]["name_es"].startswith("inserción")
    assert meshes["Pectoralis minor muscle.e1r"]["name_es"].startswith("origen")
    assert meshes["Short head of biceps brachii.r"]["name_es"] == "cabeza corta del músculo bíceps braquial derecha"


def test_female_body():
    """TC del Visible Human (esqueleto, piel, vasos, músculos) + órganos del HRA de la misma mujer."""
    manifest, layers = _body("female")
    assert "Visible Human" in manifest["source"]
    meshes = _meshes(layers)
    assert meshes["liver"]["model_id"] == "UBERON:0002107"
    assert meshes["heart"]["model_id"] == "UBERON:0000948"
    assert meshes["uterus"]["layer"] == "reproductor"
    assert meshes["skin"]["layer"] == "piel"
    # Cada pieza dice de qué fuente sale.
    assert all("Visible Human" in m["source"] or "Human Reference Atlas" in m["source"] for m in meshes.values())
    # Esqueleto completo: cráneo, 24 costillas, cinturas, huesos largos, manos y pies.
    skeleton = {m["key"] for m in layers["esqueleto"]["meshes"]}
    assert {"ct_skull", "ct_sternum", "ct_femur_left", "ct_femur_right", "ct_humerus_left", "ct_humerus_right"} <= skeleton
    assert sum(1 for key in skeleton if key.startswith("ct_rib_")) == 24
    assert {"ct_bones_of_foot_l", "ct_bones_of_foot_r", "ct_bones_of_hand_l", "ct_bones_of_hand_r"} <= skeleton
    assert meshes["ct_rib_left_1"]["name_es"] == "primera costilla izquierda"
    assert meshes["ct_aorta"]["layer"] == "cardiovascular"
    low, high = manifest["bounds"]["min"], manifest["bounds"]["max"]
    assert abs(low[1]) < 1e-6 and 1.6 < high[1] < 1.75  # pies en el suelo; 1,67 m
