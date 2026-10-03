# Modelos 3D de la demo

Cada cuerpo ocupa una carpeta con:

- `manifest.json` (formato `bodysim-body-1`): sexo, fuente, límites del cuerpo
  (para encuadrar la cámara) y las capas disponibles, con su número de piezas,
  de triángulos y de bytes;
- un archivo por capa (formato `bodysim-mesh-1`). El visor lo descarga solo
  cuando se enciende esa capa.

Cada pieza seleccionable (el fémur derecho, el nervio óptico, la cóclea, un giro
cerebral...) lleva:

- su nombre en español y en inglés;
- su término UBERON, si lo hay;
- la estructura de bodysim de la que forma parte, que sirve para escalar su masa;
- su lado y su color;
- la malla: posiciones cuantizadas a 16 bits sobre la caja de la pieza
  (precisión inferior a 0,03 mm) e índices, ambos en base64. Las normales las
  calcula el visor.

Coordenadas en metros: Y hacia arriba, +Z hacia delante y +X hacia la izquierda
del sujeto.

| Capa | `male/` (Z-Anatomy) | `female/` (Visible Human + HRA) |
|---|---:|---:|
| piel y regiones | 256 | 1 |
| esqueleto (huesos, cartílagos, dientes) | 277 | 73 |
| articulaciones y ligamentos (cápsulas, meniscos, discos) | 413 | — |
| músculos y tendones | 491 | 10 |
| orígenes e inserciones musculares | 705 | — |
| corazón y vasos | 673 | 31 |
| encéfalo y médula (giros, surcos, núcleos, ventrículos) | 287 | 4 |
| nervios (pares craneales, plexos, nervios periféricos) | 255 | — |
| órganos de los sentidos (ojo, oído, vías lagrimales) | 40 | 2 |
| digestivo | 46 | 11 |
| respiratorio (con bronquios segmentarios) | 36 | 8 |
| urinario | 8 | 4 |
| reproductor | 14 | 9 |
| endocrino | 10 | 3 |
| linfático | 163 | 2 |
| **total** | **3674 piezas, 1,21 M triángulos, 16,1 MB** | **158 piezas, 0,63 M triángulos, 7,7 MB** |

El cuerpo femenino ya tiene el esqueleto completo, pero todavía no tiene
nervios, ligamentos ni la mayoría de los músculos (ver más abajo).

## Hombre: Z-Anatomy

### Procedencia

Atlas [Z-Anatomy](https://github.com/Z-Anatomy/Models-of-human-anatomy)
("The libre 3D atlas of anatomy"), archivo `Z-Anatomy.zip` → `Startup.blend`
(commit `19a363b`). Su geometría base es
[BodyParts3D](https://dbarchive.biosciencedbc.jp/en/bodyparts3d/download.html),
del Database Center for Life Science (DBCLS). Los nombres en español salen de
su tabla `TA2.csv` (Terminologia Anatomica 2; traducción al español de Carlos
Torres Villar), con correcciones propias.

### Licencia

[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). Al reutilizar
estos archivos hay que atribuir así:

- "BodyParts3D - The Database Center for Life Science - CC-BY-SA 2.1 Japan"
- "Z-Anatomy - The libre 3D atlas of anatomy - CC-BY-SA 4.0"

Es una licencia **share-alike**. Permite el uso comercial, pero las mallas
derivadas (estas incluidas) deben distribuirse con la misma licencia. No afecta
al código del visor ni del modelo, que solo las carga.

**Atención: piezas posiblemente no comerciales.** Z-Anatomy declara que usó
como referencia, o incluyó y adaptó, modelos de terceros:

| Modelo | Autoría | Licencia |
|---|---|---|
| "Anatomy of the Inner Ear" | University of Dundee | CC BY-NC-SA 4.0 |
| "Kidney" | Lissie Cowley | CC BY-NC 4.0 |
| "Cranial Nerves and Foramina" | University of Dundee, CAHID | CC BY 4.0 |
| "Brainder" y "White matter" | University of Washington | sin especificar |

Mientras no se verifique qué mallas proceden de cada uno, el oído interno
(cóclea, vestíbulo) y los riñones de este cuerpo no deben usarse con fines
comerciales. Para un producto comercial hay dos opciones:

- sustituirlos por los originales de BodyParts3D o por los del HRA (CC BY 4.0);
- obtener permiso de sus autores.

### Qué se cambió respecto del original

- **Extracción** con Blender como módulo de Python (`extract_blend.py`):
  - colecciones de esqueleto, inserciones musculares, articulaciones,
    músculos, cardiovascular, linfático, nervioso y sentidos, vísceras y
    regiones;
  - solo los objetos visibles;
  - en coordenadas del mundo;
  - vasos y nervios son curvas con grosor y se convierten en tubos con menos
    resolución.
- **Exclusiones** (`build_parts.py`): fascias, cavidades, bolsas sinoviales,
  vainas tendinosas y piezas sin nombre. De 3874 piezas quedan 3674.
- **Capas.** Cada pieza va a una capa según su grupo en el atlas: sistema
  nervioso central → encéfalo, periférico → nervios, órganos de los
  sentidos → sentidos, y así con cada aparato.
- **Nombres en español** con "izquierdo/derecho" concordado en género y número.
  `SPANISH_TERMS` corrige los términos que la TA2 deja en latín o traduce mal:
  - "malleus" → martillo, "incus" → yunque;
  - "stapes" → estribo (la TA2 da "estapedio", que es el músculo);
  - "lens" → cristalino.

  Con nombre en español quedan 3595 piezas; el resto muestra el inglés.
- **UBERON.** Se asigna cuando el nombre inglés coincide con una etiqueta o un
  sinónimo exacto (1202 piezas). Los pares craneales se buscan como "cranial
  nerve II", etc.
- **Estructura de bodysim**, para escalar la masa:
  - huesos, músculos y piel se asignan al esqueleto, la musculatura y la piel
    completos;
  - el resto, al órgano más cercano en la jerarquía is_a/part_of de UBERON.
- **Orígenes e inserciones.** Cada zona de anclaje de un músculo sobre el
  hueso es una pieza: "Masseter.or" es el origen derecho del masetero y
  "Pectoralis minor muscle.e1l", la segunda inserción izquierda del pectoral
  menor. El visor pinta los orígenes en rojo y las inserciones en azul.
  - Se toman del atlas tal cual, salvo el pectoral menor, que el atlas da
    invertido (origen en la escápula). Puede haber otros casos: conviene
    revisarlos contra un texto de referencia antes de usarlos en docencia.
  - El **grupo funcional** (flexores, extensores, abductores, rotadores…)
    sale del material con que el atlas colorea cada músculo y cada inserción.
    Es una clasificación simplificada: un músculo puede tener varias acciones.
- **Simplificación** con meshoptimizer: de 6,6 a 1,21 millones de triángulos.
  Cada capa tiene su presupuesto (`build_zanatomy.mjs`) y cada pieza conserva
  al menos 60 triángulos.

### Regenerarlo

```bash
# 1. Z-Anatomy.zip de Z-Anatomy/Models-of-human-anatomy, descomprimido; TA2.csv del mismo repositorio.
# 2. Extracción (Blender como módulo; necesita Python 3.11):
python -m venv blender-venv && blender-venv/bin/pip install "bpy==4.2.*" numpy
blender-venv/bin/python demo/models/zanatomy/extract_blend.py Z-Anatomy/Startup.blend raw
# 3. Capas, nombres y UBERON (con bodysim instalado; necesita uberon-basic.obo):
python demo/models/zanatomy/build_parts.py --raw raw.json --ta2 TA2.csv --obo uberon-basic.obo
# 4. Simplificación y escritura de male/ (Node.js):
cd demo/models && npm install
node zanatomy/build_zanatomy.mjs ../../raw
```

## Mujer: Visible Human + Human Reference Atlas

Es la mujer del Visible Human Project, de la que hay dos fuentes abiertas que se
combinan:

- **su TC de cuerpo entero** (1 mm, de la cabeza a los pies), segmentada con
  TotalSegmentator;
- **los órganos del HRA**, modelados sobre esa misma mujer. Se alinean con la TC
  con una transformación de semejanza ajustada sobre centroides de vértebras,
  riñones, bazo, corazón y vesícula: escala 1,0001 y error medio de 5 mm en 27
  puntos.

De cada estructura se toma la mejor fuente:

| Fuente | Estructuras |
|---|---|
| TC, segmentación de TotalSegmentator | cráneo, 24 costillas, esternón, cartílagos costales, clavículas, escápulas, húmeros y fémures; glúteos, iliopsoas y músculos profundos del dorso; aorta, cavas, carótidas, subclavias, braquiocefálicos, ilíacas, porta y venas pulmonares; lóbulos pulmonares, estómago, esófago, duodeno, tiroides y suprarrenales |
| TC, umbral de densidad a 1 mm | piel; tibia y fíbula, radio y ulna, huesos de manos y pies |
| HRA | vísceras, encéfalo, ojos, columna (con la sexta vértebra lumbar de esta mujer), pelvis, aparato reproductor, mamas y vasos de los órganos |

El HRA cambió de postura las extremidades y la piel (brazos separados del
cuerpo), así que esas piezas suyas no se usan: no coincidirían con el esqueleto
real.

### Procedencia y licencias

- **Visible Human Project**, cortesía de la U.S. National Library of Medicine.
  Desde 2019 no requiere acuerdo de licencia; sus condiciones (NLM Terms and
  Conditions, 21 de mayo de 2019) piden reconocer a la NLM en cualquier uso. La
  TC se descarga del NCI Imaging Data Commons, colección
  `nlm_visible_human_project`.
- **TotalSegmentator** (Wasserthal et al., *Radiology: Artificial Intelligence*
  2023, [10.1148/ryai.230024](https://doi.org/10.1148/ryai.230024)): tarea
  `total`, licencia Apache 2.0, que permite el uso comercial. No se usan sus
  subtareas de licencia restringida, como `appendicular_bones` (huesos de manos
  y pies): esos huesos salen del umbral de densidad.
- **Human Reference Atlas** (HuBMAP), publicación v2.0 en
  [hubmapconsortium/ccf-releases](https://github.com/hubmapconsortium/ccf-releases),
  [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/):
  - **3D Reference Organ Set for United, Female**. Kristen Browne y Heidi
    Schlehlein, a partir del Visible Human Project. DOI de la versión 1.4:
    [10.48539/HBM959.JMVR.733](https://doi.org/10.48539/HBM959.JMVR.733).
  - **ASCT+B Tables to 3D Reference Object Library Mapping** v1.5, que relaciona
    cada pieza 3D con su término UBERON. Ellen M. Quardokus, Heidi Schlehlein,
    Bruce Herr II y Katy Börner. DOI
    [10.48539/HBM595.JNGT.446](https://doi.org/10.48539/HBM595.JNGT.446).

Cada pieza lleva su fuente en el campo `source`, y el visor la muestra en su
ficha.

### Límites de esta versión

- **Resolución.** Las estructuras de TotalSegmentator salen de su modelo
  rápido, a 3 mm (en CPU, el de 1,5 mm tarda casi una hora); las superficies se
  suavizan unos 2 mm. Los huesos de las extremidades y la piel salen de la TC a
  1 mm.
- **Huesos agrupados.** La TC de un cadáver tiene las articulaciones cerradas:
  cuando no se separan, tibia y fíbula, y radio y ulna, van juntos, y los huesos
  de cada mano y cada pie forman un grupo.
- **Columna.** TotalSegmentator numera cinco lumbares y esta mujer tiene seis.
  Por eso la columna viene del HRA.
- **Postura.** La TC es de un cadáver tumbado: la espalda y las mamas están
  aplanadas.
- **Falta el detalle fino.** No hay nervios periféricos, ligamentos ni la
  mayoría de los músculos. El siguiente paso es deformar el atlas masculino
  (Z-Anatomy) hasta el esqueleto de esta mujer.

### Regenerarlo

```bash
# 1. TC del Visible Human desde el IDC (unos 900 MB) y volúmenes de 1 y 1,5 mm:
pip install idc-index pydicom SimpleITK
python demo/models/ct/fetch_vhp.py female vhp_dicom
python demo/models/ct/assemble_vhp.py vhp_dicom/* vhp_f.nii.gz
python demo/models/ct/assemble_vhp.py vhp_dicom/* vhp_f_1p5mm.nii.gz --spacing 1.5
# 2. Segmentación (en CPU, --force_split reduce la memoria):
pip install TotalSegmentator
TotalSegmentator -i vhp_f_1p5mm.nii.gz -o seg.nii.gz --ml --force_split   # --fast: modelo de 3 mm
python -c "import json; from totalsegmentator.map_to_binary import class_map; json.dump(class_map['total'], open('labels_total.json', 'w'))"
# 3. Órganos del HRA en una carpeta aparte. Archivos de ccf-releases:
#    v2.0/models/3d-vh-f-united.glb.7z y v2.0/models/asct-b-3d-models-crosswalk.csv.
python demo/models/build_mapping.py --crosswalk asct-b-3d-models-crosswalk.csv --obo uberon-basic.obo
cd demo/models && npm install && node build_models.mjs 3d-vh-f-united.glb female ../../hra_female && cd ../..
# 4. Combinación y capas del visor (necesita bodysim, scikit-image y scipy):
python demo/models/ct/build_female.py --hra hra_female --ct vhp_f.nii.gz --seg seg.nii.gz \
    --labels labels_total.json --obo uberon-basic.obo --out female_raw
node demo/models/build_layers.mjs female_raw demo/models/female
```

Los nombres en español de las piezas del HRA están en `labels_es.json`, y su
reparto y exclusiones, en `build_models.mjs`:

- se excluyen un ganglio linfático aislado de alta resolución, la placenta (el
  modelo representa un embarazo a término) y los nervios, músculos y vasos
  internos del ojo;
- arterias y venas se separan según el material original.

Los de las piezas de la TC están en `ct/build_female.py`.
