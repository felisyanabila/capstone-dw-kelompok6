"""Tahap 4 sampai 6: Reshape, integrasi, dan penyimpanan ke Gold (pertemuan VII, IX, XI, XII). Milik tim.

Keluaran: data/gold/*.parquet (panel provinsi x tahun x indikator siap analisis, plus tabel
nasional dan rekonsiliasi dengan pembanding nasional) dan basis data SQL (mis. data/gold/gold.sqlite).
"""


def jalankan(silver):
    """Terima Silver, tulis tabel Gold, kembalikan {nama_tabel: DataFrame}."""
    from src.gold import aturan, nasional, panel
    # Tahap 4 (persiapan): aturan satu nilai per sel provinsi x periode x rincian (src/gold/aturan.py)
    pilihan = aturan.pilih_satu_nilai(silver)
    aturan.tulis_keluaran(pilihan)
    f = pilihan["ringkasan"]
    print(f"Gold: {f['baris_panel']} baris satu nilai per sel, {f['baris_tidak_terpilih']} baris Silver tidak terpilih -> reports/aturan_gold.md")
    hasil = {}
    hasil.update(panel.jalankan(silver))
    hasil.update(nasional.jalankan(silver))
    return hasil