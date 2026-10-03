"""Informe anatómico de un individuo: ``python -m bodysim --sex female --age 40 --height 163 --weight 95``."""

from __future__ import annotations

import argparse

from bodysim import Person, Sex, body_composition, load_anatomy, organ_masses


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sex", choices=[s.value for s in Sex], required=True)
    parser.add_argument("--age", type=float, required=True, help="años")
    parser.add_argument("--height", type=float, required=True, help="cm")
    parser.add_argument("--weight", type=float, required=True, help="kg")
    args = parser.parse_args(argv)

    person = Person(Sex(args.sex), args.age, args.height, args.weight)
    composition = body_composition(person)
    report = organ_masses(person)
    print(f"Anatomía: {load_anatomy().source_version}")
    print(
        f"IMC {composition.bmi:.1f} kg/m² | SC {composition.bsa_m2:.2f} m² | "
        f"masa libre de grasa {composition.fat_free_mass_kg:.1f} kg | grasa {composition.fat_fraction:.0%} | "
        f"volemia {composition.blood_volume_l:.2f} L | agua {composition.total_body_water_l:.1f} L"
    )
    print(f"\n{'estructura':<24}{'UBERON':<16}{'ref (g)':>10}{'masa (g)':>10}{'Δ':>7}  modelos 3D")
    for organ in report.organs.values():
        change = organ.mass_g / organ.reference_g - 1
        models = len(organ.structure.models_for(person.sex))
        flag = "" if organ.verification == "secondary_source" else " *"
        print(
            f"{organ.structure.name_es + flag:<24}{organ.structure.id:<16}"
            f"{organ.reference_g:>10.1f}{organ.mass_g:>10.1f}{change:>+7.0%}  {models}"
        )
    print(f"\nmasa no asignada a estructuras modeladas: {report.unmodeled_mass_g / 1000:.1f} kg")
    print("* valor de referencia pendiente de contrastar con la Tabla 2.8 de ICRP 89")


if __name__ == "__main__":
    main()
