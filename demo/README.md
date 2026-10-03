# Demo: cuerpo variabilístico en 3D

Visor de anatomía 3D al estilo de los atlas interactivos:
- un cuerpo masculino o femenino que se gira, se acerca y se recorre por sistemas
  (piel, esqueleto, músculos, nervioso, cardiovascular, respiratorio, digestivo,
  urinario, reproductor y linfático);
- cada estructura se puede tocar para ver su ficha;
- el panel "Individuo" cambia sexo, edad, talla, peso y grasa (medida o
  estimada), y los órganos cambian de tamaño según la masa que calcula bodysim;
- la piel se separa con la grasa subcutánea y el hígado amarillea con su grasa.

## Abrirla

Necesita un servidor local porque carga los modelos con `fetch`:

```bash
python -m http.server 8000 -d demo
# y abre http://localhost:8000
```

La primera carga descarga three.js desde jsDelivr.

## Archivos

- `index.html`: el visor.
- `bodysim.js`: el modelo en JavaScript, con las mismas ecuaciones que el
  paquete Python.
- `model-data.js`: GENERADO por `python demo/build_data.py` a partir de los
  datos del paquete. Hay que regenerarlo cuando cambien esos datos.
- `models/`: cuerpos 3D derivados del Human Reference Atlas (CC BY 4.0). En
  [models/README.md](models/README.md) están su procedencia y cómo
  regenerarlos.

## Pruebas

- `tests/test_demo_parity.py` comprueba con Node.js que la demo y el paquete dan
  los mismos números en 400 casos aleatorios.
- `tests/test_demo_models.py` valida los modelos 3D: índices dentro de rango,
  capas conocidas y estructuras que existen en bodysim.
