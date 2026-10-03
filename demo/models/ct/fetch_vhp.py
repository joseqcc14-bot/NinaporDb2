"""Descarga la TC de cuerpo entero del Visible Human desde el NCI Imaging Data Commons (IDC).

    pip install idc-index
    python fetch_vhp.py female <carpeta>     # dos series: cabeza-muslos y fémur-pies, unos 900 MB

Visible Human Project: cortesía de la U.S. National Library of Medicine. Desde 2019 no
requiere acuerdo de licencia; sus condiciones piden reconocer a la NLM en cualquier uso.
"""
import sys

from idc_index import IDCClient

PATIENTS = {"female": "VHP-F", "male": "VHP-M"}

sex, out = sys.argv[1], sys.argv[2]
client = IDCClient()
index = client.index
series = index[(index["collection_id"] == "nlm_visible_human_project") & (index["PatientID"] == PATIENTS[sex]) & (index["Modality"] == "CT")]
print(series[["SeriesInstanceUID", "SeriesDescription", "instanceCount", "series_size_MB"]].to_string())
client.download_from_selection(downloadDir=out, seriesInstanceUID=list(series["SeriesInstanceUID"]), dirTemplate="%SeriesInstanceUID")
