"""La demo del navegador (demo/bodysim.js) da los mismos números que el paquete."""

import json
import os
import random
import shutil
import subprocess
from pathlib import Path

import pytest

from bodysim import Person, Sex, body_composition, organ_masses

DEMO = Path(__file__).resolve().parents[1] / "demo"
NODE = shutil.which("node")

HARNESS = """
const fs = require("fs"), path = require("path"), vm = require("vm");
for (const name of ["model-data.js", "bodysim.js"]) {
  vm.runInThisContext(fs.readFileSync(path.join(process.env.DEMO_DIR, name), "utf8"));
}
const cases = JSON.parse(fs.readFileSync(0, "utf8"));
const results = cases.map((person) => {
  try {
    const report = Bodysim.model.organMasses(person);
    const organs = [...report.organs].map(([id, organ]) => [id, organ.mass_g]);
    return { organs, composition: report.composition, fat: report.fat };
  } catch (error) {
    return { error: error.message };
  }
});
process.stdout.write(JSON.stringify(results));
"""


def _cases(n=400, seed=7):
    rng = random.Random(seed)
    for _ in range(n):
        height = rng.uniform(140, 210)
        yield {
            "sex": rng.choice(["male", "female"]),
            "age_years": rng.uniform(18, 90),
            "height_cm": height,
            "weight_kg": rng.uniform(11, 60) * (height / 100) ** 2,
            "body_fat_fraction": rng.choice([None, rng.uniform(0.03, 0.6)]),
            "visceral_fat_kg": rng.choice([None, rng.uniform(0.1, 8)]),
            "liver_fat_fraction": rng.choice([None, rng.uniform(0, 0.45)]),
        }


def _python(case):
    try:
        person = Person(Sex(case["sex"]), **{k: v for k, v in case.items() if k != "sex"})
        report = organ_masses(person)
    except ValueError as error:
        return {"error": str(error)}
    composition = body_composition(person)
    return {
        "organs": [[sid, organ.mass_g] for sid, organ in report.organs.items()],
        "composition": {
            "bmi": composition.bmi,
            "fat_free_mass_kg": composition.fat_free_mass_kg,
            "fat_fraction": composition.fat_fraction,
            "blood_volume_l": composition.blood_volume_l,
            "total_body_water_l": composition.total_body_water_l,
        },
        "fat": {
            "subcutaneous_g": report.fat.subcutaneous_g,
            "visceral_g": report.fat.visceral_g,
            "liver_fat_excess_g": report.fat.liver_fat_excess_g,
            "visceral_fraction": report.fat.visceral_fraction,
            "steatosis": report.fat.steatosis,
        },
    }


@pytest.mark.skipif(NODE is None, reason="hace falta Node.js para ejecutar la demo")
def test_demo_matches_python_package():
    cases = list(_cases())
    completed = subprocess.run(
        [NODE, "-e", HARNESS],
        input=json.dumps(cases),
        capture_output=True,
        text=True,
        check=True,
        env={**os.environ, "DEMO_DIR": str(DEMO)},
    )
    js_results = json.loads(completed.stdout)
    valid = 0
    for case, js in zip(cases, js_results):
        py = _python(case)
        assert ("error" in py) == ("error" in js), (case, py, js)
        if "error" in py:
            continue
        valid += 1
        assert [sid for sid, _ in js["organs"]] == [sid for sid, _ in py["organs"]]
        for (_, js_mass), (_, py_mass) in zip(js["organs"], py["organs"]):
            assert js_mass == pytest.approx(py_mass, rel=1e-9)
        for section in ("composition", "fat"):
            for key, value in py[section].items():
                assert js[section][key] == pytest.approx(value, rel=1e-9), (section, key)
    assert valid > 100
