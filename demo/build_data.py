"""Genera demo/model-data.js con los datos del paquete bodysim.

La demo del navegador (demo/bodysim.js) repite las ecuaciones del paquete y lee
de aquí los mismos datos: anatomía enlazada a UBERON, masas de ICRP 89, reglas
de escalado, parámetros de la grasa y límites de validación. Ejecutar tras
cambiar cualquiera de ellos::

    python demo/build_data.py
"""

from __future__ import annotations

import json
from pathlib import Path

from bodysim import load_anatomy, person
from bodysim.adiposity import ADIPOSE, LIVER, SUBCUTANEOUS, VISCERAL
from bodysim.anatomy import load_data
from bodysim.anthropometry import FAT_FREE_MASS_HYDRATION
from bodysim.scaling import DEFAULT_RULE, SCALING_RULES

OUT = Path(__file__).resolve().parent / "model-data.js"


def _rule(rule) -> dict:
    return {"basis": rule.basis.value, "exponent": rule.exponent}


def build() -> dict:
    anatomy = load_anatomy()
    reference = load_data("icrp89_reference.json")
    fat = load_data("fat_distribution.json")
    return {
        "uberon_version": anatomy.source_version,
        "structures": [
            {
                "id": s.id,
                "name_es": s.name_es,
                "label_en": s.label_en,
                "definition": s.definition,
                "kind": s.kind.value,
                "parent": s.parent,
                "sex": s.sex.value if s.sex else None,
                "bilateral": s.bilateral,
                "xrefs": {prefix: list(values) for prefix, values in s.xrefs.items() if prefix in ("FMA", "SCTID")},
                "models": [{"url": m.url, "sex": m.sex.value if m.sex else None, "label": m.label} for m in s.models_3d],
            }
            for s in anatomy
        ],
        "reference": {
            "source": reference["source"],
            "individuals": reference["reference_individuals"],
            "organ_masses_g": reference["organ_masses_g"],
        },
        "scaling": {"default": _rule(DEFAULT_RULE), "rules": {sid: _rule(r) for sid, r in SCALING_RULES.items()}},
        "fat": {
            "ids": {"adipose": ADIPOSE, "subcutaneous": SUBCUTANEOUS, "visceral": VISCERAL, "liver": LIVER},
            "visceral_fraction": {
                sex: fat["visceral_fraction_of_adipose_tissue"][sex] for sex in ("male", "female")
            },
            "healthy_liver_fat": fat["healthy_liver_fat_fraction"]["value"],
            "steatosis_threshold": fat["steatosis_threshold"]["value"],
        },
        "limits": {
            "age_years": person.AGE_RANGE,
            "height_cm": person.HEIGHT_RANGE_CM,
            "weight_kg": person.WEIGHT_RANGE_KG,
            "body_fat_fraction": person.BODY_FAT_RANGE,
            "visceral_fat_kg": person.VISCERAL_FAT_RANGE_KG,
            "liver_fat_fraction": person.LIVER_FAT_RANGE,
            "max_bmi": person.MAX_BMI,
            "min_bmi": {sex.value: value for sex, value in person.MIN_BMI.items()},
            "essential_fat": {sex.value: value for sex, value in person.ESSENTIAL_FAT.items()},
        },
        "ffm_hydration": FAT_FREE_MASS_HYDRATION,
    }


def main() -> None:
    payload = json.dumps(build(), ensure_ascii=False, separators=(",", ":"))
    OUT.write_text(
        "// GENERADO por demo/build_data.py desde el paquete bodysim; no editar a mano.\n"
        f"globalThis.BODYSIM_DATA = {payload};\n",
        encoding="utf-8",
    )
    print(f"{OUT.name}: {OUT.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
