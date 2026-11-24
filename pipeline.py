"""Satu perintah reproduksi tim: data mentah -> Silver -> Gold -> validasi -> SQL."""
from pathlib import Path
import sqlite3
import sys
import time
import pandas as pd

from src import ekstraksi, gold, silver, validasi
from src.common.manifest import periksa


def muat_ke_sql(db_path: Path = Path("data/warehouse.db")) -> Path:
    if db_path.exists():
        db_path.unlink()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    pemetaan_tabel = [
        ("silver_data", Path("data/silver/silver.parquet")),
        ("gold_panel_provinsi", Path("data/gold/panel_provinsi.parquet")),
        ("gold_panel_lebar", Path("data/gold/panel_lebar.parquet")),
        ("gold_tabel_nasional", Path("data/gold/tabel_nasional.parquet")),
        ("gold_nasional_periode_seri", Path("data/gold/nasional_periode_seri.parquet")),
        ("gold_pemeriksaan_total", Path("data/gold/pemeriksaan_total_rinci_vs_ringkas.parquet")),
        ("gold_rekonsiliasi_p1", Path("data/gold/rekonsiliasi_p1_rinci_vs_var1458.parquet")),
        ("gold_rekonsiliasi_p2", Path("data/gold/rekonsiliasi_p2_var1458_vs_wdi.parquet")),
        ("gold_rekonsiliasi_p3", Path("data/gold/rekonsiliasi_p3_rinci_vs_wdi.parquet")),
    ]

    with sqlite3.connect(db_path) as conn:
        conn.executescript(Path("sql/silver_schema.sql").read_text(encoding="utf-8"))
        conn.executescript(Path("sql/gold_schema.sql").read_text(encoding="utf-8"))

        ringkasan = []
        for nama_tabel, jalur_parquet in pemetaan_tabel:
            df = pd.read_parquet(jalur_parquet)
            kolom = ", ".join(f'"{c}"' for c in df.columns)
            tanda = ", ".join("?" for _ in df.columns)
            sql_insert = f"INSERT INTO {nama_tabel} ({kolom}) VALUES ({tanda})"

            baris_data = [
                tuple(None if pd.isna(v) else (int(v) if isinstance(v, bool) else v) for v in row)
                for row in df.itertuples(index=False, name=None)
            ]
            conn.executemany(sql_insert, baris_data)

            jml_sql = conn.execute(f"SELECT COUNT(*) FROM {nama_tabel}").fetchone()[0]
            assert jml_sql == len(df), (
                f"Jumlah baris {nama_tabel} tidak sama: SQL={jml_sql} vs Parquet={len(df)}"
            )
            ringkasan.append(f"{nama_tabel}={jml_sql}")

    print(f"SQLite: {', '.join(ringkasan)} -> {db_path}")
    return db_path


def main():
    n, salah = periksa()
    if salah:
        sys.exit(f"data/raw tidak cocok dengan MANIFEST.csv ({len(salah)} berkas). Jalankan ulang unduh_data.py.")
    print(f"data/raw: {n} berkas cocok dengan MANIFEST.csv")
    for nama, langkah in [("ekstraksi", lambda h: ekstraksi.jalankan()),
                          ("silver", lambda h: silver.jalankan(h["ekstraksi"])),
                          ("gold", lambda h: gold.jalankan(h["silver"])),
                          ("validasi", lambda h: validasi.jalankan(h["silver"], h.get("gold"))),
                          ("sql", lambda h: muat_ke_sql())]:
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