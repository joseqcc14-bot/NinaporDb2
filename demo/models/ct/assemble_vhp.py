"""Reconstruye la TC de cuerpo entero del Visible Human a partir de sus series DICOM.

Las series del VHP no comparten origen de mesa: cada una reinicia la coordenada z, y
el campo de visión cambia por regiones (cabeza 250 mm, tronco 480 mm...). La posición
global de cada corte está en SliceLocation (1 mm por corte, continua entre series) y
todos los cortes están centrados en x = y = 0. Se coloca cada corte en z = -SliceLocation
y se remuestrea a una rejilla común de 1 mm.

    python assemble_vhp.py <serie DICOM>... <salida.nii.gz> [--spacing 1.5]

Con --spacing se suaviza y remuestrea al tamaño de vóxel indicado (TotalSegmentator trabaja
a 1,5 mm; a 1 mm, en CPU, no cabe en 16 GB de memoria).
"""
import glob
import sys

import numpy as np
import pydicom
import SimpleITK as sitk

args = sys.argv[1:]
target = None
if "--spacing" in args:
    position = args.index("--spacing")
    target = float(args[position + 1])
    del args[position:position + 2]
dirs, out = args[:-1], args[-1]
FOV = 480  # mm, el mayor campo de visión de las series
grid = sitk.Image([FOV, FOV], sitk.sitkFloat32)
grid.SetSpacing([1.0, 1.0])
grid.SetOrigin([-FOV / 2, -FOV / 2])

slices = {}
for d in dirs:
    for path in glob.glob(f"{d}/*.dcm"):
        ds = pydicom.dcmread(path)
        location = float(ds.SliceLocation)
        if location in slices:
            continue
        pixels = ds.pixel_array.astype(np.float32) * float(ds.RescaleSlope) + float(ds.RescaleIntercept)
        image = sitk.GetImageFromArray(pixels)  # filas = y (posterior), columnas = x (izquierda)
        spacing = float(ds.PixelSpacing[0])
        image.SetSpacing([spacing, spacing])
        image.SetOrigin([float(v) for v in ds.ImagePositionPatient[:2]])
        resampled = sitk.Resample(image, grid, sitk.Transform(), sitk.sitkLinear, -1024.0, sitk.sitkFloat32)
        slices[location] = sitk.GetArrayFromImage(resampled).astype(np.int16)

locations = sorted(slices)
steps = np.diff(locations)
print(f"{len(locations)} cortes, SliceLocation {locations[0]:.0f}-{locations[-1]:.0f}, pasos {sorted(set(steps.round(2)))}")
# Índice 0 = pies (z más bajo): z = -SliceLocation crece hacia la cabeza (LPS).
volume = np.stack([slices[loc] for loc in reversed(locations)])
result = sitk.GetImageFromArray(volume)
result.SetSpacing([1.0, 1.0, 1.0])
result.SetOrigin([-FOV / 2, -FOV / 2, -locations[-1]])
if target:
    size = [int(round(s / target)) for s in result.GetSize()]
    smooth = sitk.SmoothingRecursiveGaussian(sitk.Cast(result, sitk.sitkFloat32), 0.4 * target)
    result = sitk.Resample(smooth, size, sitk.Transform(), sitk.sitkLinear, result.GetOrigin(), [target] * 3,
                           result.GetDirection(), -1024.0, sitk.sitkInt16)
sitk.WriteImage(result, out)
print("volumen", result.GetSize(), "mm, altura", len(locations), "mm")
