"""Tahap 4 sampai 6: Reshape, integrasi, dan penyimpanan ke Gold (pertemuan VII, IX, XI, XII). Milik tim.

Keluaran: data/gold/*.parquet (panel provinsi x tahun x indikator siap analisis, plus tabel
rekonsiliasi dengan pembanding nasional) dan basis data SQL (mis. data/gold/gold.sqlite).
"""


def jalankan(silver):
    """Terima Silver, tulis tabel Gold, kembalikan {nama_tabel: DataFrame}."""
    from src.gold import aturan
    # Tahap 4 (persiapan): aturan satu nilai per sel provinsi x periode x rincian (src/gold/aturan.py)
    hasil = aturan.pilih_satu_nilai(silver)
    aturan.tulis_keluaran(hasil)
    f = hasil["ringkasan"]
    print(f"Gold: {f['baris_panel']} baris satu nilai per sel, {f['baris_tidak_terpilih']} baris Silver tidak terpilih "
          f"-> reports/aturan_gold.md")
    return {"panel_provinsi": hasil["panel"], "pemeriksaan_total": hasil["pemeriksaan_total"]}