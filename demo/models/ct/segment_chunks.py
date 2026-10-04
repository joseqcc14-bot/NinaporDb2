"""Segmenta una TC de cuerpo entero con TotalSegmentator por bloques solapados.

En CPU con 16 GB de memoria, el modelo de 1,5 mm no cabe ni con --force_split: el proceso
acumula memoria entre sus cinco submodelos. Aquí cada bloque se segmenta en un proceso
aparte, que libera la memoria al terminar, y las etiquetas se cosen tomando la parte central
de cada bloque (la mitad del solape para cada vecino).

    python segment_chunks.py vhp_f_1p5mm.nii.gz seg.nii.gz [--chunks 4] [--overlap 40]

El solape se da en cortes (40 cortes de 1,5 mm = 6 cm).
"""
import argparse
import os
import subprocess
import sys
import tempfile

import numpy as np
import SimpleITK as sitk

parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
parser.add_argument("source")
parser.add_argument("out")
parser.add_argument("--chunks", type=int, default=4)
parser.add_argument("--overlap", type=int, default=40)
args = parser.parse_args()

image = sitk.ReadImage(args.source)
depth = image.GetSize()[2]
step = int(np.ceil((depth + args.overlap * (args.chunks - 1)) / args.chunks))
merged = np.zeros(sitk.GetArrayFromImage(image).shape, np.uint8)
command = os.path.join(os.path.dirname(sys.executable), "TotalSegmentator")
start = 0
with tempfile.TemporaryDirectory() as tmp:
    for i in range(args.chunks):
        z0 = max(0, min(start, depth - step))
        z1 = min(depth, z0 + step)
        piece, labels = os.path.join(tmp, f"chunk_{i}.nii.gz"), os.path.join(tmp, f"seg_{i}.nii.gz")
        sitk.WriteImage(image[:, :, z0:z1], piece)
        print(f"bloque {i + 1} de {args.chunks}: cortes {z0}-{z1}", flush=True)
        subprocess.run([command, "-i", piece, "-o", labels, "--ml", "--nr_thr_resamp", "1", "--nr_thr_saving", "1"], check=True)
        keep0 = z0 if i == 0 else z0 + args.overlap // 2
        keep1 = z1 if i == args.chunks - 1 else z1 - args.overlap // 2
        merged[keep0:keep1] = sitk.GetArrayFromImage(sitk.ReadImage(labels))[keep0 - z0:keep1 - z0]
        start = z1 - args.overlap
result = sitk.GetImageFromArray(merged)
result.CopyInformation(image)
sitk.WriteImage(result, args.out)
