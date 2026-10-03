# Demo: cuerpo variabilístico

Página interactiva que muestra el estado del modelo: se cambian las variables
independientes (sexo, edad, talla, peso y grasa medida o estimada) y se ve cómo
responden las masas de los órganos y la distribución de la grasa. Cada
estructura enlaza con su término de UBERON y, cuando existe, con su modelo 3D
del Human Reference Atlas.

## Abrirla

Abre `demo/index.html` en el navegador; no necesita servidor.

## Archivos

- `index.html`: la página.
- `bodysim.js`: el modelo en JavaScript, con las mismas ecuaciones que el
  paquete Python.
- `model-data.js`: GENERADO por `python demo/build_data.py` a partir de los
  datos del paquete (anatomía, masas de ICRP 89, reglas de escalado,
  parámetros de la grasa). Hay que regenerarlo cuando cambien esos datos.

`tests/test_demo_parity.py` comprueba con Node.js que la demo y el paquete dan
los mismos números en 400 casos aleatorios.
