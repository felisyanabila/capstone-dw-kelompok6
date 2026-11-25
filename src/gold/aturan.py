"""Tahap 4 (persiapan Gold): aturan satu nilai per sel.

Silver boleh punya lebih dari satu baris untuk sel yang sama (dua snapshot, banyak rincian). Gold tidak
boleh. Fungsi `pilih_satu_nilai(silver)` memilih tepat satu baris per provinsi x periode x rincian dan
mencatat baris Silver yang tidak terpilih beserta alasannya. Dipanggil oleh `src/gold/__init__.py`
(dan karena itu oleh pipeline.py).

Aturan (diperiksa berurutan, tiap baris Silver kena paling banyak satu alasan penyisihan):
  1. Baris Indonesia (kode 9999) bukan provinsi: tidak masuk panel, dipakai tabel nasional (K-005).
  2. Total provinsi: 2014 sampai 2025 dipakai var1458, sebelum 2014 dipakai tabel rinci (K-003).
     Total tabel rinci pada sel yang var1458-nya ada tidak terpilih; selisihnya dilaporkan, bukan disamakan.
  3. Rincian (laki-laki, perempuan, perkotaan, perdesaan, dan gabungannya) hanya ada di tabel rinci
     dan seluruhnya masuk panel pada kolom `rincian`.
  4. Periode harus tahunan; bila ada semesteran atau bulanan fungsi berhenti dengan galat.
  5. Penanda anomali (kategori_anomali) dibawa ke Gold, termasuk penanda dari baris yang tidak terpilih.

Cara pakai tunggal:
    python src/gold/aturan.py                 hitung, tulis reports/gold/* dan reports/aturan_gold.md
    python src/gold/aturan.py --tulis-log     juga menambah baris tahap gold ke log-keputusan.csv
"""
import argparse
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "reports" / "gold"
LAPORAN = ROOT / "reports" / "aturan_gold.md"
SILVER = ROOT / "data" / "silver" / "silver.parquet"

INDONESIA = 9999
RINCI = "tabel:sdg4_amh_rinci"
RINGKAS = "var1458"
TAHUN_RINGKAS = "2014"
KUNCI = ["wilayah_kode", "periode", "rincian"]
# urutan prioritas bila satu sel punya lebih dari satu penanda (paling kuat di depan)
PRIORITAS = ["galat_input", "revisi_snapshot", "patahan_wilayah", "patahan_metode", "outlier_asli"]
ALASAN_NASIONAL = "nasional_bukan_provinsi"
ALASAN_TOTAL = "total_rinci_digantikan_var1458"


def _gabung_penanda(s):
    """Penanda terkuat per sel (wilayah, periode, rincian) dari semua baris kandidat, termasuk yang tidak terpilih."""
    rank = {k: i for i, k in enumerate(PRIORITAS)}
    p = s[s["kategori_anomali"].notna()].copy()
    p["_r"] = p["kategori_anomali"].map(rank)
    if p["_r"].isna().any():
        raise ValueError(f"kategori_anomali tidak dikenal: {sorted(p.loc[p['_r'].isna(), 'kategori_anomali'].unique())}")
    p = p.sort_values("_r").drop_duplicates(KUNCI)
    return p.set_index(KUNCI)["kategori_anomali"]


def pilih_satu_nilai(silver):
    """Terima Silver (DataFrame), kembalikan dict: panel, tidak_terpilih, pemeriksaan_total, ringkasan."""
    s = silver.reset_index(drop=True).copy()
    s["_id"] = s.index

    # aturan 4: periode harus tahunan
    bukan_tahun = s.loc[s["jenis_periode"] != "tahun", "jenis_periode"]
    if len(bukan_tahun):
        raise ValueError(f"periode bukan tahunan ({sorted(bukan_tahun.unique())}): tentukan aturan agregasi periode "
                         "lebih dulu, jangan merata-ratakan diam-diam")

    alasan = pd.Series(pd.NA, index=s.index, dtype="object")

    # aturan 1: Indonesia bukan provinsi
    nasional = s["wilayah_kode"] == INDONESIA
    alasan[nasional] = ALASAN_NASIONAL
    prov = ~nasional

    asing = prov & ~s["seri_kode"].isin([RINCI, RINGKAS])
    if asing.any():
        raise ValueError(f"seri provinsi tanpa aturan: {sorted(s.loc[asing, 'seri_kode'].unique())}; tambahkan aturannya")

    # aturan 2: total provinsi, var1458 diutamakan bila ada pada sel yang sama
    ringkas_ada = s[prov & (s["seri_kode"] == RINGKAS)][["wilayah_kode", "periode"]].drop_duplicates()
    ringkas_ada["_ada"] = True
    m = s[["wilayah_kode", "periode"]].merge(ringkas_ada, on=["wilayah_kode", "periode"], how="left")
    ada = m["_ada"].fillna(False).to_numpy(dtype=bool)
    total_rinci = prov & (s["seri_kode"] == RINCI) & (s["rincian"] == "total") & ada
    alasan[total_rinci] = ALASAN_TOTAL

    terpilih = alasan.isna()
    panel = s[terpilih].copy()

    # kunci sel harus unik di Gold
    kembar = panel.duplicated(KUNCI, keep=False)
    if kembar.any():
        contoh = panel.loc[kembar, KUNCI + ["seri_kode"]].head(10).to_string(index=False)
        raise AssertionError(f"{int(kembar.sum())} baris Gold berkunci kembar setelah aturan dijalankan:\n{contoh}")

    # aturan 5: penanda anomali dari semua kandidat sel, termasuk baris yang tidak terpilih
    gabung = _gabung_penanda(s[prov])
    sendiri = panel["kategori_anomali"]
    kunci_idx = pd.MultiIndex.from_frame(panel[KUNCI])
    panel["kategori_anomali"] = gabung.reindex(kunci_idx).to_numpy()
    panel["penanda_dari_baris_lain"] = panel["kategori_anomali"].notna() & sendiri.isna().to_numpy()
    jumlah = s[prov].groupby(KUNCI).size()
    panel["jumlah_kandidat"] = jumlah.reindex(kunci_idx).to_numpy()

    panel = panel.rename(columns={"seri_kode": "seri_terpilih", "kode_sdg": "indikator"})
    kolom = ["wilayah_kode", "nama_wilayah", "periode", "indikator", "rincian", "daerah", "jenis_kelamin", "nilai",
             "satuan", "seri_terpilih", "jumlah_kandidat", "kategori_anomali", "penanda_dari_baris_lain",
             "_berkas_raw", "_sha256_raw"]
    panel = panel[kolom].sort_values(KUNCI).reset_index(drop=True)

    tidak = s[~terpilih].copy()
    tidak["alasan"] = alasan[~terpilih]
    tidak = tidak[["seri_kode", "wilayah_kode", "nama_wilayah", "periode", "rincian", "nilai", "alasan"]]
    tidak = tidak.sort_values(["alasan", "seri_kode", "wilayah_kode", "periode", "rincian"]).reset_index(drop=True)

    if len(panel) + len(tidak) != len(s):
        raise AssertionError("jumlah baris panel + tidak terpilih tidak sama dengan Silver")

    # tabel pemeriksaan total rinci vs ringkas: dilaporkan, tidak disamakan paksa
    r = s[(s["seri_kode"] == RINCI) & (s["rincian"] == "total")]
    v = s[s["seri_kode"] == RINGKAS]
    pm = r.merge(v, on=["wilayah_kode", "periode"], suffixes=("_rinci", "_var1458"))
    pm["selisih"] = (pm["nilai_rinci"] - pm["nilai_var1458"]).round(4)
    pm["status"] = pm["selisih"].abs().gt(1e-6).map({True: "beda", False: "sama"})
    pm["nilai_dipakai"] = pm["nilai_var1458"]
    pemeriksaan = pm.rename(columns={"nama_wilayah_rinci": "nama_wilayah", "nilai_rinci": "nilai_rinci_total"})[
        ["wilayah_kode", "nama_wilayah", "periode", "nilai_var1458", "nilai_rinci_total", "selisih", "status",
         "nilai_dipakai"]].sort_values(["wilayah_kode", "periode"]).reset_index(drop=True)

    sisih = tidak["alasan"].value_counts()
    ringkasan = {
        "baris_silver": len(s),
        "baris_panel": len(panel),
        "baris_tidak_terpilih": len(tidak),
        "tidak_nasional": int(sisih.get(ALASAN_NASIONAL, 0)),
        "tidak_total_rinci": int(sisih.get(ALASAN_TOTAL, 0)),
        "pasangan_total": len(pemeriksaan),
        "pasangan_sama": int((pemeriksaan["status"] == "sama").sum()),
        "pasangan_beda": int((pemeriksaan["status"] == "beda").sum()),
        "tahun_beda": sorted(pemeriksaan.loc[pemeriksaan["status"] == "beda", "periode"].unique().tolist()),
        "sel_panel_bertanda": int(panel["kategori_anomali"].notna().sum()),
        "penanda_dipindah": int(panel["penanda_dari_baris_lain"].sum()),
        "rincian_di_panel": int(panel["rincian"].nunique()),
        "provinsi_di_panel": int(panel["wilayah_kode"].nunique()),
        "per_kategori": panel["kategori_anomali"].value_counts().reindex(PRIORITAS, fill_value=0).to_dict(),
    }
    return {"panel": panel, "tidak_terpilih": tidak, "pemeriksaan_total": pemeriksaan, "ringkasan": ringkasan}


def _md(t):
    from src.silver.grid_amh import md_tabel
    return md_tabel(t)


def tulis_keluaran(hasil):
    """Tulis tabel bantu dan laporan. Panel Gold sendiri ditulis oleh tugas panel (#28), bukan di sini."""
    OUT.mkdir(parents=True, exist_ok=True)
    f = hasil["ringkasan"]
    hasil["tidak_terpilih"].to_csv(OUT / "baris_silver_tidak_terpilih.csv", index=False)
    hasil["pemeriksaan_total"].to_csv(OUT / "pemeriksaan_total_rinci_vs_ringkas.csv", index=False)
    ring = pd.DataFrame([
        ["baris Silver", f["baris_silver"]],
        ["masuk panel provinsi (satu nilai per sel)", f["baris_panel"]],
        ["tidak terpilih: nasional_bukan_provinsi", f["tidak_nasional"]],
        ["tidak terpilih: total_rinci_digantikan_var1458", f["tidak_total_rinci"]],
    ], columns=["keterangan", "baris"])
    ring.to_csv(OUT / "ringkasan_aturan_satu_nilai.csv", index=False)

    catatan = "## Catatan temuan\n\n(belum diisi)\n"
    if LAPORAN.exists():  # jangan hapus catatan yang sudah ditulis
        lama = LAPORAN.read_text(encoding="utf-8")
        i = lama.find("## Catatan temuan")
        if i != -1:
            catatan = lama[i:]
    aturan = pd.DataFrame([
        [1, "Baris Indonesia (9999) bukan provinsi", "tidak masuk panel; dipakai tabel nasional (K-005)"],
        [2, "Total provinsi: 2014 sampai 2025 pakai var1458, sebelum 2014 pakai tabel rinci (K-003)",
         "total tabel rinci pada sel yang var1458-nya ada tidak terpilih; selisih dilaporkan"],
        [3, "Rincian laki-laki, perempuan, perkotaan, perdesaan, dan gabungannya hanya ada di tabel rinci",
         "seluruhnya masuk panel pada kolom rincian"],
        [4, "Periode harus tahunan", "periode semesteran atau bulanan menghentikan proses dengan galat"],
        [5, "Penanda anomali dibawa ke Gold", "penanda dari baris tidak terpilih dipindah ke baris terpilih (prioritas "
         + ", ".join(PRIORITAS) + ")"],
    ], columns=["no", "aturan", "akibat"])
    kat = pd.DataFrame([[k, v] for k, v in f["per_kategori"].items()], columns=["kategori_anomali", "sel_di_panel"])
    teks = f"""# Aturan satu nilai per sel Gold (Tahap 4, persiapan)

Dibuat oleh `src/gold/aturan.py` (fungsi `pilih_satu_nilai`), dipanggil `src/gold/__init__.py` dan karena itu `pipeline.py`.
Silver boleh punya beberapa baris per sel, Gold tidak boleh. Kunci sel Gold: `wilayah_kode` x `periode` x `rincian`.

## Aturan
{_md(aturan)}

## Hasil pada Silver sekarang
{_md(ring)}

Panel memuat {f['provinsi_di_panel']} kode provinsi dan {f['rincian_di_panel']} rincian. Daftar baris Silver yang tidak terpilih:
`reports/gold/baris_silver_tidak_terpilih.csv`.

## Pemeriksaan total rinci vs ringkas
Dari {f['pasangan_total']} pasangan sel (termasuk Indonesia), {f['pasangan_sama']} sama dan {f['pasangan_beda']} berbeda (tahun {', '.join(f['tahun_beda'])}).
Selisih dilaporkan, tidak disamakan paksa; nilai yang dipakai Gold adalah var1458. Daftar: `reports/gold/pemeriksaan_total_rinci_vs_ringkas.csv`.

## Penanda anomali di panel
{f['sel_panel_bertanda']} sel panel bertanda; {f['penanda_dipindah']} di antaranya mewarisi penanda dari baris tabel rinci yang tidak terpilih.

{_md(kat)}

{catatan}"""
    LAPORAN.write_text(teks, encoding="utf-8")


def draf_log(f):
    n_tot, n_nas = f["tidak_total_rinci"], f["tidak_nasional"]
    return [
        ("gold", "semua",
         "Gold memuat tepat satu nilai per provinsi x periode x rincian lewat fungsi pilih_satu_nilai di src/gold/aturan.py yang dipanggil pipeline.py; kunci sel (wilayah_kode, periode, rincian); kunci kembar menghentikan proses dengan galat",
         "saringan tangan di notebook; merata-ratakan kandidat angka",
         "Gold tidak boleh punya dua angka untuk satu sel; aturan di kode dapat diulang dan diperiksa; rata-rata menyembunyikan selisih revisi",
         f["baris_tidak_terpilih"]),
        ("gold", "tabel:sdg4_amh_rinci;var1458",
         "angka total provinsi: 2014 sampai 2025 dipakai var1458 dan sebelum 2014 dipakai tabel rinci (K-003); total tabel rinci pada sel yang var1458-nya ada tidak terpilih; selisih (tahun " + ", ".join(f["tahun_beda"]) + ") dilaporkan di tabel pemeriksaan, tidak disamakan paksa",
         "memakai total tabel rinci untuk semua tahun; merata-ratakan kedua angka",
         f"var1458 adalah sumber kanonik 2014 sampai 2025; dari {f['pasangan_total']} pasangan sel, {f['pasangan_beda']} berbeda; rata-rata menghapus jejak revisi",
         n_tot),
        ("gold", "tabel:sdg4_amh_rinci",
         "delapan rincian selain total (laki-laki, perempuan, perkotaan, perdesaan, dan gabungannya) hanya ada di tabel rinci dan seluruhnya masuk panel pada kolom rincian beserta kolom daerah dan jenis_kelamin",
         "hanya menyimpan total di Gold; memecah rincian menjadi kolom lebar",
         "var1458 tidak punya rincian; panduan meminta rincian dienkode ke kolom rincian yang konsisten; tidak ada baris rincian yang disisihkan",
         0),
        ("gold", "semua",
         "baris Indonesia (kode 9999) dan seri WDI tidak masuk panel provinsi; tetap di Silver dan dipakai tabel nasional dan rekonsiliasi",
         "memasukkan Indonesia sebagai satu provinsi di panel",
         "Indonesia adalah agregat nasional, bukan provinsi (K-005); WDI hanya punya titik nasional",
         n_nas),
        ("gold", "semua",
         "periode di Silver semuanya tahunan; fungsi pilih_satu_nilai berhenti dengan galat bila menemukan periode semesteran atau bulanan",
         "merata-ratakan periode semesteran atau bulanan ke tahunan secara diam-diam",
         "agregasi periode adalah keputusan substantif yang harus dicatat; saat ini tidak ada periode non-tahunan sehingga tidak ada baris yang terdampak",
         0),
        ("gold", "semua",
         "kolom kategori_anomali dibawa ke Gold; bila baris yang tidak terpilih punya penanda, penanda itu dipindah ke baris terpilih dengan prioritas galat_input, revisi_snapshot, patahan_wilayah, patahan_metode, outlier_asli, dan ditandai di kolom penanda_dari_baris_lain",
         "menghapus penanda saat baris tidak terpilih; memakai penanda baris terpilih saja",
         "penanda patahan dan outlier tidak boleh hilang di Gold; tanpa pemindahan, sel yang terpilih dari var1458 kehilangan penanda dari tabel rinci",
         f["penanda_dipindah"]),
        ("gold", "var1458;tabel:sdg4_amh_rinci",
         f"koreksi angka pada K-003 dan K-008: sel total var1458 vs tabel rinci yang berbeda berjumlah {f['pasangan_beda']} dari {f['pasangan_total']} pasangan (tahun " + ", ".join(f["tahun_beda"]) + "), bukan 33; ambang selisih sebelumnya membulatkan dan mengabaikan selisih 0,01 (DKI Jakarta 2017); pemilihan var1458 sebagai nilai Gold tidak berubah",
         "membiarkan angka 33 di log dan laporan",
         "log harus sama dengan hasil validasi Silver (laporan validasi: 34 dari 427) dan tabel pemeriksaan Gold; baris lama tidak ditulis ulang agar riwayat keputusan tetap utuh",
         1),
    ]


def jalankan(tulis_log=False):
    from src.silver.grid_amh import jumlah_log_saya, tulis_log as tulis_baris
    mulai = time.time()
    hasil = pilih_satu_nilai(pd.read_parquet(SILVER))
    tulis_keluaran(hasil)
    f = hasil["ringkasan"]
    print(f"Silver {f['baris_silver']} baris -> panel {f['baris_panel']} baris ({f['provinsi_di_panel']} provinsi, {f['rincian_di_panel']} rincian); "
          f"tidak terpilih {f['baris_tidak_terpilih']} (nasional {f['tidak_nasional']}, total rinci {f['tidak_total_rinci']})")
    print(f"pemeriksaan total: {f['pasangan_sama']} sama, {f['pasangan_beda']} beda dari {f['pasangan_total']}, tahun beda {f['tahun_beda']}")
    print(f"penanda di panel: {f['per_kategori']}; dipindah dari baris tidak terpilih: {f['penanda_dipindah']}")
    baris = draf_log(f)
    print("\nDraf baris log-keputusan.csv (tahap gold):")
    for i, b in enumerate(baris, 1):
        print(f"  [{i}] seri={b[1]} dampak_baris={b[5]}\n      {b[2][:150]}")
    if tulis_log:
        print(f"\n{tulis_baris(baris)} baris baru ditulis ke log-keputusan.csv")
    n_log = jumlah_log_saya(baris, tulis_log)
    print("\nPerintah metrics.json (periksa angkanya dulu, lalu jalankan sendiri):")
    print(f"python -m src.common.hasil 124450001 baris_silver={f['baris_silver']} baris_panel_gold={f['baris_panel']} "
          f"baris_silver_tidak_terpilih={f['baris_tidak_terpilih']} sel_kosong_grid=686 outlier_ditandai=463 sel_missing_sejati=0 "
          f"anomali_outlier_asli=441 anomali_patahan=20 anomali_revisi_snapshot=2 anomali_galat_input=0 keputusan_dicatat={n_log}")
    print(f"\nselesai dalam {time.time() - mulai:.1f} detik")
    return hasil


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    ap = argparse.ArgumentParser()
    ap.add_argument("--tulis-log", action="store_true", help="tambahkan baris tahap gold ke log-keputusan.csv")
    jalankan(ap.parse_args().tulis_log)