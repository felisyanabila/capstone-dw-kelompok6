"""Tahap 4 — Transformasi: susun Silver dari hasil ekstraksi. Milik tim.

Silver ditulis ke data/silver/silver.parquet dan harus lolos
`python -m src.common.skema data/silver/silver.parquet`. Logikanya ada di src/silver/bangun.py;
modul lain di paket ini (wilayah, grid_amh, profil_*, anomali_amh) adalah tahap 2-3.
"""


def jalankan(mentah):
    from src.silver import bangun
    s = bangun.susun(mentah)
    jalur = bangun.tulis(s)
    r = bangun.ringkasan(s)
    print(f"Silver: {r['baris_silver']} baris, {r['seri_silver']} seri, {r['rincian_dienkode']} rincian, "
          f"{r['baris_ditandai_anomali']} baris bertanda anomali -> {jalur.relative_to(bangun.ROOT)}")
    return s
