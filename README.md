# bodysim: simulador paramétrico del cuerpo humano

El objetivo es un cuerpo humano completo en el que sexo, edad, talla, peso,
grasa corporal y genotipo sean **variables independientes**, la anatomía se
ajuste a ellas y, sobre esa base, se simulen la fisiología y las enfermedades
de cualquier estructura, tanto de causa externa como genética.

Esta primera fase deja **empalmada la anatomía**. Cada estructura del modelo
queda enlazada, con un identificador estándar, a los recursos anatómicos que ya
existen:

- la ontología UBERON;
- las mallas de BodyParts3D y Z-Anatomy (vía FMA);
- los modelos 3D del Human Reference Atlas;
- las terminologías clínicas SNOMED CT, MeSH, NCIt y UMLS.

Además, las masas de los órganos se escalan según las variables del individuo.

## La decisión: ¿interfaz existente o cuerpo propio?

Ni lo uno ni lo otro por separado: **el modelo es nuestro y la anatomía se importa.**

| | Decisión | Motivo |
|---|---|---|
| Geometría y nomenclatura anatómica | **Importar** de fuentes abiertas | Ya existe, está curada y validada. Redibujarla llevaría años y no aporta valor diferencial. |
| Cuerpo paramétrico ("variabilístico") | **Construirlo nosotros** | Lo que no existe integrado son las variables independientes, las reglas de escalado y los enlaces con fisiología, genética y enfermedad. Ahí está el valor del producto y su propiedad intelectual. |
| Plataformas comerciales (BioDigital Human, Complete Anatomy, Visible Body) | **No como núcleo** | Son visores con licencia de pago. No exponen un modelo editable ni escalable y generan dependencia de un proveedor. Sirven como referencia visual. |

El empalme es una **llave única por estructura**: su CURIE de UBERON (por
ejemplo, `UBERON:0000948`, el corazón). De esa llave cuelgan:

- la malla 3D;
- la masa de referencia;
- más adelante, los parámetros fisiológicos, los genes expresados y las
  enfermedades que la afectan.

Los detalles están en [docs/arquitectura.md](docs/arquitectura.md).

## Qué existe ya, y qué no

- **Anatomía.** Hay mucho material abierto:
  - [Human Reference Atlas](https://humanatlas.io) (HuBMAP): órganos 3D en GLB
    y tablas ASCT+B que relacionan estructura, tipo celular y biomarcador.
  - BodyParts3D y Z-Anatomy: mallas de todo el cuerpo indexadas por FMA.
  - Fantomas computacionales de ICRP 110 y 145.
  - Visible Human Project.
- **Fisiología.** También existe, aunque es menos conocida:
  - [Pulse Physiology Engine](https://pulse.kitware.com/_about_pulse.html)
    (Kitware, Apache 2.0, con API en Python). Simula un paciente definido por
    sexo, edad, talla, peso y fracción de grasa, con condiciones como EPOC,
    SDRA, anemia o sepsis.
  - BioGears (Apache 2.0).
  - HumMod, un modelo integrado con miles de variables.
  - Los modelos CellML/SBML del Physiome Project.
- **Lo que no existe integrado:** un cuerpo en el que la anatomía 3D, la
  fisiología, la genética y la enfermedad localizada compartan las mismas llaves
  y respondan a variables independientes. Ese es el hueco que cubre este proyecto.

## Uso rápido

Instalación y pruebas:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

Informe anatómico de una mujer de 163 cm y 95 kg. Las medidas de grasa son
opcionales; las que falten se estiman:

- `--body-fat`: % de grasa corporal (DXA, bioimpedancia, pliegues);
- `--visceral-fat`: kg de grasa visceral (DXA, TC o RM);
- `--liver-fat`: % de grasa del hígado por RM (PDFF).

```bash
python -m bodysim --sex female --age 40 --height 163 --weight 95
python -m bodysim --sex female --age 40 --height 163 --weight 95 --body-fat 45 --visceral-fat 2.5 --liver-fat 12
```

Desde Python:

```python
from dataclasses import replace
from bodysim import Person, Sex, organ_masses, load_anatomy

ana = Person(Sex.FEMALE, age_years=40, height_cm=163, weight_kg=60)
informe = organ_masses(replace(ana, weight_kg=95))   # solo cambia el peso
higado = informe.organs["UBERON:0002107"]
higado.mass_g                                         # 1810 g (referencia: 1400 g)
higado.structure.xrefs["FMA"]                         # ('FMA:7197',) -> BodyParts3D / Z-Anatomy
higado.structure.models_for(Sex.FEMALE)[0].url        # GLB del Human Reference Atlas

anatomia = load_anatomy()
anatomia.find_xref("FMA:7088").name_es                # 'corazón'
[s.name_es for s in anatomia.ancestors("UBERON:0002107")]  # ['sistema digestivo', 'cuerpo humano']
```

## Estructura

```text
src/bodysim/
  person.py          variables independientes del individuo (sexo, edad, talla, peso, grasa, genotipo)
  anthropometry.py   composición corporal: IMC, superficie corporal, masa libre de grasa, volemia, agua
  adiposity.py       reparto de la grasa: subcutánea, visceral y del hígado
  anatomy.py         árbol anatómico enlazado a UBERON, FMA, SNOMED CT y los modelos 3D del HRA
  scaling.py         masa de cada órgano para un individuo + modificadores (genética y enfermedad)
  sources/obo.py     lector del formato OBO
  sources/uberon.py  sincronización con un release de UBERON
  data/
    structures.json        árbol curado a mano: qué estructuras modelamos y cómo se agrupan
    uberon_snapshot.json   GENERADO desde UBERON; no se edita a mano
    icrp89_reference.json  masas de referencia de ICRP 89 y estado de verificación de cada valor
    fat_distribution.json  parámetros del reparto de la grasa, con su fuente y su verificación
demo/                    demostración interactiva en el navegador (ver demo/README.md)
tests/
docs/arquitectura.md
```

## Datos y verificación

- **`uberon_snapshot.json`** se regenera con `python -m bodysim.sources.uberon`.
  El comando descarga el último release desde GitHub y falla si alguna
  estructura deja de existir o queda obsoleta. La versión actual es UBERON
  2026-10-01: 43 estructuras y 39 modelos 3D.
- **`icrp89_reference.json`** tiene dos tipos de valores:
  - 9 contrastados con una copia secundaria de la Tabla 2.8 de ICRP 89
    (`secondary_source`);
  - 21 transcritos y pendientes de contrastar con la tabla original (`pending`).
    Hay que hacerlo antes de usar resultados fuera del desarrollo. El informe de
    la línea de comandos los marca con `*`.
- **Escalado.** Los supuestos de esta versión están documentados en
  `scaling.py`: órganos magros según la masa libre de grasa, encéfalo constante,
  sangre según la volemia y tejido adiposo según la masa grasa. Son un punto de
  partida que hay que calibrar con datos.
- **Grasa corporal.** La total, la visceral y la del hígado se usan si están
  medidas; si no, se estiman. En `fat_distribution.json`:
  - el reparto visceral típico por sexo está pendiente de contrastar (`pending`);
  - el umbral de esteatosis (5,56 %) está contrastado (`secondary_source`).

  Cómo entra la grasa en el modelo y sus limitaciones:
  [docs/arquitectura.md](docs/arquitectura.md#grasa-corporal-y-peso).

Este proyecto es una herramienta de investigación y desarrollo. No es un
dispositivo médico.

## Hoja de ruta

1. **Anatomía empalmada.** Hecha, con la grasa repartida en subcutánea,
   visceral y del hígado.
2. **Fisiología.** Puente con Pulse: `Person` se traduce en un paciente de Pulse
   y sus compartimentos se asignan a nodos UBERON.
3. **Genética.** El genotipo se traduce en `Modifier` sobre estructuras, a partir
   de ASCT+B (HRA), ClinVar, GWAS/PGS Catalog y HPO/Monarch.
4. **Enfermedad localizada.** Una enfermedad es un conjunto de modificadores
   anatómicos y fisiológicos sobre nodos UBERON, enlazada a SNOMED CT y MONDO
   por las referencias cruzadas que ya tenemos.
5. **Visualización y forma externa:**
   - visor 3D al estilo de un atlas: hecho en [demo/](demo/README.md), escalado
     según el informe de cada individuo;
   - atlas masculino completo con Z-Anatomy (CC BY-SA 4.0): hecho. Tiene 3674
     piezas: huesos, articulaciones, músculos con sus orígenes e inserciones,
     vasos, nervios, encéfalo y sentidos;
   - falta el atlas femenino completo, pues el HRA solo trae órganos;
   - pendiente antes de cualquier uso comercial: verificar o sustituir el oído
     interno y el riñón, que Z-Anatomy pudo tomar de modelos con licencia no
     comercial (ver [demo/models/README.md](demo/models/README.md#licencia));
   - superficie corporal paramétrica con
     [Anny](https://europe.naverlabs.com/blog/anny-a-free-to-use-3d-human-parametric-model-for-all-ages/)
     (Apache 2.0; edad, talla y peso como parámetros).
