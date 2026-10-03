// Modelo de bodysim para el navegador. Repite las ecuaciones del paquete Python
// (src/bodysim) con los datos de model-data.js; tests/test_demo_parity.py
// comprueba que ambos dan los mismos números.
(function (root) {
  "use strict";

  function createModel(D) {
    const FAT = D.fat.ids;

    function check(name, value, bounds) {
      const [low, high] = bounds;
      if (!(Number.isFinite(value) && value >= low && value <= high)) {
        throw new RangeError(`${name}=${value} fuera del rango validado [${low}, ${high}]`);
      }
    }

    const heightM = (p) => p.height_cm / 100;
    const bmi = (p) => p.weight_kg / heightM(p) ** 2;

    // Mismas reglas que Person.__post_init__.
    function validate(p) {
      const L = D.limits;
      check("age_years", p.age_years, L.age_years);
      check("height_cm", p.height_cm, L.height_cm);
      check("weight_kg", p.weight_kg, L.weight_kg);
      check("IMC", bmi(p), [L.min_bmi[p.sex], L.max_bmi]);
      if (p.body_fat_fraction != null) {
        check("body_fat_fraction", p.body_fat_fraction, L.body_fat_fraction);
        const ffmi = bmi(p) * (1 - p.body_fat_fraction);
        const minFfmi = L.min_bmi[p.sex] * (1 - L.essential_fat[p.sex]);
        if (ffmi < minFfmi) {
          throw new RangeError(
            `masa libre de grasa de ${ffmi.toFixed(1)} kg/m², por debajo de la mínima compatible con la vida (${minFfmi.toFixed(1)} kg/m²)`
          );
        }
      }
      if (p.visceral_fat_kg != null) check("visceral_fat_kg", p.visceral_fat_kg, L.visceral_fat_kg);
      if (p.liver_fat_fraction != null) check("liver_fat_fraction", p.liver_fat_fraction, L.liver_fat_fraction);
    }

    const bsaMosteller = (p) => Math.sqrt((p.height_cm * p.weight_kg) / 3600);

    function estimatedFatFreeMass(p) {
      return p.sex === "male"
        ? (9270 * p.weight_kg) / (6680 + 216 * bmi(p))
        : (9270 * p.weight_kg) / (8780 + 244 * bmi(p));
    }

    function fatFreeMass(p) {
      return p.body_fat_fraction != null ? p.weight_kg * (1 - p.body_fat_fraction) : estimatedFatFreeMass(p);
    }

    const fatMass = (p) => p.weight_kg - fatFreeMass(p);

    function bloodVolume(p) {
      const h = heightM(p);
      return p.sex === "male"
        ? 0.3669 * h ** 3 + 0.03219 * p.weight_kg + 0.6041
        : 0.3561 * h ** 3 + 0.03308 * p.weight_kg + 0.1833;
    }

    function totalBodyWater(p) {
      if (p.body_fat_fraction != null) return D.ffm_hydration * fatFreeMass(p);
      return p.sex === "male"
        ? 2.447 - 0.09516 * p.age_years + 0.1074 * p.height_cm + 0.3362 * p.weight_kg
        : -2.097 + 0.1069 * p.height_cm + 0.2466 * p.weight_kg;
    }

    function bodyComposition(p) {
      const ffm = fatFreeMass(p);
      const fm = p.weight_kg - ffm;
      return {
        bmi: bmi(p),
        bsa_m2: bsaMosteller(p),
        fat_free_mass_kg: ffm,
        fat_mass_kg: fm,
        fat_fraction: fm / p.weight_kg,
        blood_volume_l: bloodVolume(p),
        total_body_water_l: totalBodyWater(p),
        fat_measured: p.body_fat_fraction != null,
      };
    }

    function referencePerson(sex) {
      const body = D.reference.individuals[sex];
      return { sex, age_years: 35, height_cm: body.height_cm, weight_kg: body.weight_kg };
    }

    const BASIS = {
      fat_free_mass: fatFreeMass,
      fat_mass: fatMass,
      blood_volume: bloodVolume,
      constant: () => 1,
    };

    // Mismo orden de pasos que scaling.organ_masses y _distribute_fat.
    function organMasses(p) {
      validate(p);
      const reference = referencePerson(p.sex);
      const organs = new Map();
      for (const entry of D.reference.organ_masses_g) {
        const referenceG = entry[p.sex];
        if (referenceG == null) continue;
        const rule = D.scaling.rules[entry.id] || D.scaling.default;
        const basis = BASIS[rule.basis];
        const ratio = basis(p) / basis(reference);
        organs.set(entry.id, {
          id: entry.id,
          reference_g: referenceG,
          mass_g: referenceG * ratio ** rule.exponent,
          basis: rule.basis,
          verification: entry.verification,
        });
      }

      const adipose = organs.get(FAT.adipose);
      organs.delete(FAT.adipose);

      const healthy = D.fat.healthy_liver_fat;
      const liver = organs.get(FAT.liver);
      const liverFat = p.liver_fat_fraction != null ? p.liver_fat_fraction : healthy;
      const liverG = (liver.mass_g * (1 - healthy)) / (1 - liverFat);
      const excessG = liverG - liver.mass_g;
      organs.set(FAT.liver, { ...liver, mass_g: liverG });

      const share = D.fat.visceral_fraction[p.sex];
      const visceralG = p.visceral_fat_kg != null ? p.visceral_fat_kg * 1000 : adipose.mass_g * share;
      const subcutaneousG = adipose.mass_g - visceralG - excessG;
      if (subcutaneousG <= 0) {
        throw new RangeError(
          `la grasa visceral (${(visceralG / 1000).toFixed(1)} kg) y la del hígado (${(excessG / 1000).toFixed(1)} kg) no caben en el tejido adiposo total (${(adipose.mass_g / 1000).toFixed(1)} kg); revisa la grasa corporal`
        );
      }
      organs.set(FAT.subcutaneous, {
        ...adipose,
        id: FAT.subcutaneous,
        reference_g: adipose.reference_g * (1 - share),
        mass_g: subcutaneousG,
      });
      organs.set(FAT.visceral, {
        ...adipose,
        id: FAT.visceral,
        reference_g: adipose.reference_g * share,
        mass_g: visceralG,
      });

      let modeled = 0;
      for (const organ of organs.values()) modeled += organ.mass_g;
      const adiposeTotal = subcutaneousG + visceralG + excessG;
      return {
        organs,
        composition: bodyComposition(p),
        fat: {
          subcutaneous_g: subcutaneousG,
          visceral_g: visceralG,
          visceral_measured: p.visceral_fat_kg != null,
          visceral_fraction: visceralG / adiposeTotal,
          liver_fat_fraction: liverFat,
          liver_fat_measured: p.liver_fat_fraction != null,
          liver_fat_excess_g: excessG,
          adipose_tissue_g: adiposeTotal,
          steatosis: liverFat >= D.fat.steatosis_threshold,
        },
        modeled_mass_g: modeled,
        unmodeled_mass_g: p.weight_kg * 1000 - modeled,
      };
    }

    return { validate, bodyComposition, organMasses, referencePerson, estimatedFatFreeMass };
  }

  const api = { createModel };
  if (root.BODYSIM_DATA) api.model = createModel(root.BODYSIM_DATA);
  root.Bodysim = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
