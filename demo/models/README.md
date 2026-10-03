# Modelos 3D de la demo

`male.json` y `female.json` contienen el cuerpo masculino y femenino que muestra
el visor: una malla por estructura seleccionable (hígado, pulmón izquierdo, cada
vértebra, arterias y venas de cada órgano...), con su término UBERON, la
estructura de bodysim a la que pertenece, su capa (sistema) y su nombre en
español.

## Procedencia y licencia

Derivados del Human Reference Atlas (HRA, HuBMAP), publicación v2.0 en
[hubmapconsortium/ccf-releases](https://github.com/hubmapconsortium/ccf-releases):

- **3D Reference Organ Set for United, Male** y **Female**. Kristen Browne y
  Heidi Schlehlein, a partir del Visible Human Project (National Library of
  Medicine). DOI de la versión 1.4: [10.48539/HBM728.HNBH.685](https://doi.org/10.48539/HBM728.HNBH.685)
  (hombre) y [10.48539/HBM959.JMVR.733](https://doi.org/10.48539/HBM959.JMVR.733)
  (mujer).
- **ASCT+B Tables to 3D Reference Object Library Mapping** v1.5, que relaciona
  cada pieza 3D con su término UBERON. Ellen M. Quardokus, Heidi Schlehlein,
  Bruce Herr II y Katy Börner. DOI [10.48539/HBM595.JNGT.446](https://doi.org/10.48539/HBM595.JNGT.446).

Licencia de los datos originales y de estos derivados:
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Hay que mantener la
atribución anterior al reutilizarlos.

## Qué se cambió respecto del original

- **Fusión.** Las piezas de cada estructura se unen en una sola malla, en
  metros y en el sistema de coordenadas del cuerpo: Y hacia arriba, +Z hacia
  delante y +X hacia la izquierda del sujeto.
- **Simplificación.** Con meshoptimizer se pasa de 3,4 a 0,36 millones de
  triángulos en el hombre y de 4,8 a 0,39 millones en la mujer.
- **Exclusiones:**
  - un ganglio linfático aislado de alta resolución;
  - la placenta (el modelo femenino representa un embarazo a término);
  - los nervios, músculos y vasos internos del ojo.
- **Vasos.** Arterias y venas se separan según el material original.
- **Formato.** Las posiciones se cuantizan a 16 bits sobre la caja de cada
  estructura (precisión inferior a 0,03 mm). Las normales las calcula el visor.

El atlas no incluye estómago, esófago, tiroides, suprarrenales, glándulas
salivales, ni el esqueleto y la musculatura completos. Esas estructuras existen
en el modelo de masas de bodysim, pero no tienen malla 3D.

## Regenerarlos

```bash
# 1. Archivos originales: v2.0/models/3d-vh-m-united.glb.zip y 3d-vh-f-united.glb.7z,
#    y la tabla v2.0/models/asct-b-3d-models-crosswalk.csv de ccf-releases.
# 2. Correspondencias con bodysim (necesita uberon-basic.obo):
python demo/models/build_mapping.py --crosswalk asct-b-3d-models-crosswalk.csv --obo uberon-basic.obo
# 3. Conversión (Node.js):
cd demo/models && npm install
node build_models.mjs 3d-vh-m-united.glb male
node build_models.mjs 3d-vh-f-united.glb female   # --glb escribe además un GLB estándar
```

Los nombres en español están en `labels_es.json`. El reparto de piezas, los
presupuestos de triángulos y las exclusiones están en `build_models.mjs`.
