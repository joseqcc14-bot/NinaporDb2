# Demo: cuerpo variabilístico en 3D

Visor de anatomía 3D al estilo de los atlas interactivos:

- **Cuerpo masculino completo** (atlas Z-Anatomy, 3674 piezas):
  - esqueleto con cada hueso, cartílago y diente;
  - 413 articulaciones y ligamentos (cápsulas, meniscos, discos);
  - 491 músculos y tendones, con su grupo funcional (flexores, extensores…);
  - 705 zonas de origen (rojo) e inserción (azul) de los músculos sobre el
    hueso;
  - corazón y vasos de todo el cuerpo;
  - encéfalo con giros, surcos, núcleos y ventrículos, y médula espinal;
  - los 12 pares craneales y los nervios periféricos;
  - ojo, oído y vías lagrimales;
  - vísceras, glándulas endocrinas y ganglios linfáticos.
- **Cuerpo femenino** (Human Reference Atlas): órganos, encéfalo, ojos, vasos
  principales y parte del esqueleto. Todavía no tiene la musculatura ni los
  nervios completos.
- **Capas y vistas.** Cada sistema es una capa que se enciende o se apaga. Las
  vistas rápidas (huesos, músculos, articulaciones, inserciones, vasos, nervios,
  órganos, encéfalo y sentidos) combinan capas y transparencia de la piel.
- **Fichas.** Cada pieza se puede tocar o buscar por nombre (en español o en
  inglés) para ver su ficha: término UBERON, estructura de bodysim y masa para
  el individuo. "Aislar" y "Atenuar el resto" la destacan.
- **Panel "Individuo".** Cambia sexo, edad, talla, peso y grasa (medida o
  estimada). Los órganos cambian de tamaño según la masa que calcula bodysim, la
  piel se separa con la grasa subcutánea y el hígado amarillea con su grasa.

## Abrirla

Necesita un servidor local porque carga los modelos con `fetch`:

```bash
python -m http.server 8000 -d demo
# y abre http://localhost:8000
```

La primera carga descarga three.js desde jsDelivr.

Las capas se descargan bajo demanda:

- al abrir llegan la piel y el esqueleto;
- las demás capas encendidas se descargan en segundo plano;
- las que empiezan apagadas (músculos, 3,3 MB; articulaciones; inserciones;
  nervios; linfático), solo al encenderlas o al elegir una vista que las use.

Cada capa se dibuja como un solo `BatchedMesh` de three.js. Así, las 3674
piezas del atlas cuestan unas 15 llamadas de dibujo.

## Archivos

- `index.html`: el visor.
- `bodysim.js`: el modelo en JavaScript, con las mismas ecuaciones que el
  paquete Python.
- `model-data.js`: GENERADO por `python demo/build_data.py` a partir de los
  datos del paquete. Hay que regenerarlo cuando cambien esos datos.
- `models/`: los dos cuerpos, una carpeta por sexo con un archivo por capa. El
  hombre deriva de Z-Anatomy y BodyParts3D (CC BY-SA 4.0, share-alike, con
  piezas posiblemente no comerciales). La mujer deriva del Human Reference
  Atlas (CC BY 4.0). En [models/README.md](models/README.md) están la
  procedencia, las licencias y cómo regenerarlos.

## Pruebas

- `tests/test_demo_parity.py` comprueba con Node.js que la demo y el paquete dan
  los mismos números en 400 casos aleatorios.
- `tests/test_demo_models.py` valida los modelos 3D:
  - manifiestos coherentes con los archivos;
  - índices dentro de rango;
  - capas conocidas y estructuras que existen en bodysim;
  - licencias;
  - piezas clave del atlas masculino y sus nombres en español.
