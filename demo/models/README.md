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

| Capa | `male/` (Z-Anatomy) | `female/` (HRA) |
|---|---:|---:|
| piel y regiones | 256 | 1 |
| esqueleto (huesos, cartílagos, dientes) | 277 | 32 |
| articulaciones y ligamentos (cápsulas, meniscos, discos) | 413 | — |
| músculos y tendones | 491 | 2 |
| orígenes e inserciones musculares | 705 | — |
| corazón y vasos | 673 | 15 |
| encéfalo y médula (giros, surcos, núcleos, ventrículos) | 287 | 4 |
| nervios (pares craneales, plexos, nervios periféricos) | 255 | — |
| órganos de los sentidos (ojo, oído, vías lagrimales) | 40 | 2 |
| digestivo | 46 | 8 |
| respiratorio (con bronquios segmentarios) | 36 | 5 |
| urinario | 8 | 4 |
| reproductor | 14 | 9 |
| endocrino | 10 | — |
| linfático | 163 | 2 |
| **total** | **3674 piezas, 1,21 M triángulos, 16,1 MB** | **84 piezas, 0,39 M triángulos, 4,7 MB** |

El cuerpo femenino todavía no tiene esqueleto, musculatura ni nervios
completos. El HRA solo trae órganos, y Z-Anatomy no incluye órganos
reproductores femeninos.

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

## Mujer: Human Reference Atlas

### Procedencia

Derivado del Human Reference Atlas (HRA, HuBMAP), publicación v2.0 en
[hubmapconsortium/ccf-releases](https://github.com/hubmapconsortium/ccf-releases):

- **3D Reference Organ Set for United, Female**. Kristen Browne y Heidi
  Schlehlein, a partir del Visible Human Project (National Library of
  Medicine). DOI de la versión 1.4:
  [10.48539/HBM959.JMVR.733](https://doi.org/10.48539/HBM959.JMVR.733).
- **ASCT+B Tables to 3D Reference Object Library Mapping** v1.5, que relaciona
  cada pieza 3D con su término UBERON. Ellen M. Quardokus, Heidi Schlehlein,
  Bruce Herr II y Katy Börner. DOI
  [10.48539/HBM595.JNGT.446](https://doi.org/10.48539/HBM595.JNGT.446).

### Licencia

[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), tanto los datos
originales como estos derivados. Hay que mantener la atribución anterior al
reutilizarlos.

### Qué se cambió respecto del original

- **Fusión.** Las piezas de cada estructura se unen en una sola malla.
- **Simplificación** con meshoptimizer: de 4,8 a 0,39 millones de triángulos.
- **Exclusiones:**
  - un ganglio linfático aislado de alta resolución;
  - la placenta (el modelo representa un embarazo a término);
  - los nervios, músculos y vasos internos del ojo.
- **Vasos.** Arterias y venas se separan según el material original.

El HRA no incluye estómago, esófago, tiroides, suprarrenales, glándulas
salivales, ni el esqueleto y la musculatura completos.

### Regenerarlo

```bash
# 1. Archivos originales: v2.0/models/3d-vh-f-united.glb.7z y la tabla
#    v2.0/models/asct-b-3d-models-crosswalk.csv de ccf-releases.
# 2. Correspondencias con bodysim (necesita uberon-basic.obo):
python demo/models/build_mapping.py --crosswalk asct-b-3d-models-crosswalk.csv --obo uberon-basic.obo
# 3. Conversión (Node.js); --glb escribe además un GLB estándar:
cd demo/models && npm install
node build_models.mjs 3d-vh-f-united.glb female
```

Los nombres en español están en `labels_es.json`. El reparto de piezas, los
presupuestos de triángulos y las exclusiones están en `build_models.mjs`. El
mismo script convierte el cuerpo masculino del HRA (`3d-vh-m-united.glb male`),
pero escribe en `male/` y sustituiría al de Z-Anatomy.
