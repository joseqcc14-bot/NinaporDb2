"""Informe anatómico de un individuo.

Ejemplo: ``python -m bodysim --sex male --age 50 --height 175 --weight 100 --visceral-fat 4 --liver-fat 20``.
"""

from __future__ import annotations

import argparse

from bodysim import Person, Sex, body_composition, load_anatomy, organ_masses


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sex", choices=[s.value for s in Sex], required=True)
    parser.add_argument("--age", type=float, required=True, help="años")
    parser.add_argument("--height", type=float, required=True, help="cm")
    parser.add_argument("--weight", type=float, required=True, help="kg")
    parser.add_argument("--body-fat", type=float, help="%% de grasa corporal medido; si se omite, se estima")
    parser.add_argument("--visceral-fat", type=float, help="kg de grasa visceral medidos (DXA, TC o RM)")
    parser.add_argument("--liver-fat", type=float, help="%% de grasa del hígado medido por RM (PDFF)")
    args = parser.parse_args(argv)

    try:
        person = Person(
            Sex(args.sex),
            args.age,
            args.height,
            args.weight,
            body_fat_fraction=None if args.body_fat is None else args.body_fat / 100,
            visceral_fat_kg=args.visceral_fat,
            liver_fat_fraction=None if args.liver_fat is None else args.liver_fat / 100,
        )
        report = organ_masses(person)
    except ValueError as error:
        parser.error(str(error))
    composition = body_composition(person)
    fat = report.fat
    print(f"Anatomía: {load_anatomy().source_version}")
    print(
        f"IMC {composition.bmi:.1f} kg/m² | SC {composition.bsa_m2:.2f} m² | "
        f"masa libre de grasa {composition.fat_free_mass_kg:.1f} kg | "
        f"grasa {composition.fat_fraction:.0%} ({'medida' if composition.fat_measured else 'estimada'}) | "
        f"volemia {composition.blood_volume_l:.2f} L | agua {composition.total_body_water_l:.1f} L"
    )
    print(
        f"Tejido adiposo {fat.adipose_tissue_g / 1000:.1f} kg: subcutáneo {fat.subcutaneous_g / 1000:.1f} kg | "
        f"visceral {fat.visceral_g / 1000:.1f} kg ({fat.visceral_fraction:.0%}, "
        f"{'medida' if fat.visceral_measured else 'típica'}) | hígado {fat.liver_fat_fraction:.0%} de grasa "
        f"({'medida' if fat.liver_fat_measured else 'supuesto sano'}{', esteatosis' if fat.steatosis else ''})"
    )
    print(f"\n{'estructura':<28}{'UBERON':<16}{'ref (g)':>10}{'masa (g)':>10}{'Δ':>7}  modelos 3D")
    for organ in report.organs.values():
        change = organ.mass_g / organ.reference_g - 1
        models = len(organ.structure.models_for(person.sex))
        flag = "" if organ.verification == "secondary_source" else " *"
        print(
            f"{organ.structure.name_es + flag:<28}{organ.structure.id:<16}"
            f"{organ.reference_g:>10.1f}{organ.mass_g:>10.1f}{change:>+7.0%}  {models}"
        )
    print(f"\nmasa no asignada a estructuras modeladas: {report.unmodeled_mass_g / 1000:.1f} kg")
    print("* valor de referencia pendiente de contrastar con la Tabla 2.8 de ICRP 89")


if __name__ == "__main__":
    main()
