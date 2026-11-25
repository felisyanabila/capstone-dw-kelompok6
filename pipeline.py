"""Satu perintah reproduksi tim: data mentah -> Silver -> Gold -> validasi."""
import sys
import time

from src import ekstraksi, gold, silver, validasi
from src.common.manifest import periksa


def main():
    n, salah = periksa()
    if salah:
        sys.exit(f"data/raw tidak cocok dengan MANIFEST.csv ({len(salah)} berkas). Jalankan ulang unduh_data.py.")
    print(f"data/raw: {n} berkas cocok dengan MANIFEST.csv")
    for nama, langkah in [("ekstraksi", lambda h: ekstraksi.jalankan()),
                          ("silver", lambda h: silver.jalankan(h["ekstraksi"])),
                          ("gold", lambda h: gold.jalankan(h["silver"])),
                          ("validasi", lambda h: validasi.jalankan(h["silver"], h.get("gold")))]:
        mulai = time.time()
        try:
            hasil[nama] = langkah(hasil)
            print(f"{nama:<10} selesai dalam {time.time() - mulai:.1f} s")
        except NotImplementedError:
            hasil[nama] = None
            print(f"{nama:<10} dilewati (tahap Sprint 2)")
    print("Periksa skema minimal: python -m src.common.skema data/silver/silver.parquet")


hasil = {}

if __name__ == "__main__":
    main()
