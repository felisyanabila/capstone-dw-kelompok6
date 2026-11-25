"""Kamus wilayah: nama provinsi ke kode BPS x 100 (aturan K-001, tata 38 provinsi 2025).

Tabel var1458 membawa kode (wilayah_id), tabel rinci hanya nama. Kamus dibuat dari var1458,
lalu dipakai untuk memberi kode pada tabel yang hanya punya nama.
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
BPS = ROOT / "data" / "raw" / "bps" / "2026-10-17"
INDONESIA = 9999
# provinsi hasil pemekaran: kode -> tahun pembentukan (Kalimantan Utara 2012, empat provinsi Papua 2022)
TAHUN_BENTUK = {6500: 2012, 9200: 2022, 9500: 2022, 9600: 2022, 9700: 2022}


def normal(nama):
    """Huruf besar, spasi rapi, dan 'KEPULAUAN ' di awal menjadi 'KEP. ' (ejaan var1458)."""
    s = " ".join(str(nama).upper().split())
    if s.startswith("KEPULAUAN "):
        s = "KEP. " + s[len("KEPULAUAN "):]
    return s


def kamus_wilayah():
    """(nama_dinormalkan -> kode, kode -> nama baku) dari var1458."""
    a = pd.read_csv(BPS / "sdg4_amh.csv", usecols=["wilayah_id", "wilayah"]).drop_duplicates()
    kode_nama = {int(k): " ".join(n.upper().split()) for k, n in zip(a["wilayah_id"], a["wilayah"])}
    nama_kode = {normal(n): k for k, n in kode_nama.items()}
    assert len(nama_kode) == len(kode_nama), "nama atau kode ganda di var1458"
    return nama_kode, kode_nama


def kode_dari_nama(nama, nama_kode):
    try:
        return nama_kode[normal(nama)]
    except KeyError:
        raise KeyError(f"nama wilayah tidak dikenal: {nama!r}; tambahkan ke kamus dan catat di log-keputusan.csv") from None
