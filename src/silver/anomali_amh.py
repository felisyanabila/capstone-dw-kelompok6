"""Tahap 3: kategori calon anomali (outlier asli, patahan, galat input), aturan deduplikasi, dan perbaikan galat.

Memakai daftar calon dari tugas #12 (profil_amh.py) dan tabel dari tugas #14 (grid_amh.py).
Hanya galat input yang boleh diperbaiki; kategori lain ditandai dan dijelaskan, nilainya tidak diubah.
    python src/silver/anomali_amh.py                 hitung dan tulis laporan, cetak draf log dan perintah metrics
    python src/silver/anomali_amh.py --tulis-log     juga menambahkan baris keputusan ke log-keputusan.csv
"""
import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.common.manifest import periksa  # noqa: E402
from src.silver.grid_amh import (NIM, STATUS, TOTAL_RINCI, bandingkan_total, bangun_grid,  # noqa: E402
                                 baca_pengamatan, jumlah_log_saya, md_tabel, tulis_log)
from src.silver.profil_amh import baca_data, calon_anomali  # noqa: E402
from src.silver.wilayah import INDONESIA, kamus_wilayah, kode_dari_nama  # noqa: E402

OUT = ROOT / "reports" / "profil"
GAMBAR = ROOT / "reports" / "gambar"
LAPORAN = ROOT / "reports" / "klasifikasi_anomali.md"
Z_PATAHAN = 3.0      # |z| robust median perubahan tahunan satu seri pada satu tahun
SEARAH_MIN = 0.70    # porsi provinsi yang bergerak searah
LANGKAH_MIN = 0.5    # poin persen: perubahan yang dihitung "bergerak"
TOLERANSI = 0.011    # pembulatan dua desimal pada pemeriksaan konsistensi
PERSISTEN_MIN = 3    # tahun ditandai IQR lintas provinsi agar disebut persisten
# provinsi induk -> provinsi hasil pemekaran (dipakai untuk patahan wilayah)
PEMEKARAN = {9400: [9500, 9600, 9700], 9100: [9200], 6400: [6500]}
KATEGORI = ["galat_input", "revisi_snapshot", "patahan_wilayah", "patahan_metode", "outlier_asli"]


def perubahan_tahunan(obs):
    p = obs[(obs["kode"] != INDONESIA) & obs["nilai"].notna()].sort_values(["seri", "kode", "periode"]).copy()
    p["selisih"] = p.groupby(["seri", "kode"])["nilai"].diff()
    p["jeda"] = p.groupby(["seri", "kode"])["periode"].diff()
    return p[p["jeda"] == 1]


def patahan_serentak(obs):
    """Tahun ketika median perubahan satu seri menyimpang jauh dan hampir semua provinsi bergerak searah."""
    d = perubahan_tahunan(obs)
    baris = []
    for seri, g in d.groupby("seri"):
        med = g.groupby("periode")["selisih"].median()
        mad = (med - med.median()).abs().median() * 1.4826
        for t, m in med.items():
            x = g[g["periode"] == t]["selisih"]
            searah = ((np.sign(x) == np.sign(m)) & (x.abs() >= LANGKAH_MIN)).mean() if m != 0 else 0.0
            z = (m - med.median()) / mad if mad > 0 else 0.0
            baris.append((seri, int(t), len(x), round(float(m), 2), round(float(z), 1), round(float(searah) * 100, 0),
                          abs(z) >= Z_PATAHAN and searah >= SEARAH_MIN))
    return pd.DataFrame(baris, columns=["seri", "periode", "n_provinsi", "median_perubahan", "z_robust", "pct_searah", "patahan"])


def galat_input(obs):
    """Bukti keras galat input: di luar 0 sampai 100, total di luar rentang komponennya, atau kunci kembar berbeda nilai."""
    hasil = []
    for _, b in obs[obs["nilai"].notna() & ((obs["nilai"] < 0) | (obs["nilai"] > 100))].iterrows():
        hasil.append((b["seri"], b["kode"], b["periode"], b["nilai"], "nilai di luar 0 sampai 100"))
    r = obs[obs["tabel"] == "rinci"].copy()
    r[["_x", "daerah", "jk"]] = r["seri"].str.split(" / ", expand=True)
    w = r.pivot_table(index=["kode", "daerah", "periode"], columns="jk", values="nilai").dropna()
    lo, hi = w[["Laki-laki", "Perempuan"]].min(axis=1), w[["Laki-laki", "Perempuan"]].max(axis=1)
    for (kode, daerah, t), b in w[(w["Laki-laki+Perempuan"] < lo - TOLERANSI) | (w["Laki-laki+Perempuan"] > hi + TOLERANSI)].iterrows():
        hasil.append((f"rinci / {daerah} / Laki-laki+Perempuan", kode, t, b["Laki-laki+Perempuan"], "total di luar rentang laki-laki dan perempuan"))
    d = r.pivot_table(index=["kode", "jk", "periode"], columns="daerah", values="nilai").dropna()
    lo, hi = d[["Perkotaan", "Perdesaan"]].min(axis=1), d[["Perkotaan", "Perdesaan"]].max(axis=1)
    for (kode, jk, t), b in d[(d["Perkotaan + Perdesaan"] < lo - TOLERANSI) | (d["Perkotaan + Perdesaan"] > hi + TOLERANSI)].iterrows():
        hasil.append((f"rinci / Perkotaan + Perdesaan / {jk}", kode, t, b["Perkotaan + Perdesaan"], "gabungan di luar rentang perkotaan dan perdesaan"))
    kembar = obs[obs["nilai"].notna()].groupby(["seri", "kode", "periode"])["nilai"].nunique()
    for (seri, kode, t), n in kembar[kembar > 1].items():
        hasil.append((seri, kode, t, np.nan, "kunci kembar dengan nilai berbeda"))
    return pd.DataFrame(hasil, columns=["seri", "kode", "periode", "nilai", "alasan"])


def deduplikasi(tabel):
    """var1458 vs total tabel rinci: angka sama = konfirmasi, angka beda = revisi (kedua nilai disimpan)."""
    t = tabel.copy()
    t["status"] = np.where(t["selisih"].abs() > 0.01, "revisi", "sama")
    t["nilai_dipakai"] = t["var1458"]
    t["nilai_alternatif"] = t["rinci_total"]
    return t


def kategorikan(an, obs, kode_nama, nama_kode, pat, galat, dedup):
    an = an.copy()
    an["seri"] = an["seri"].str.replace(" | ", " / ", regex=False)
    an["kode"] = an["provinsi"].map(lambda n: kode_dari_nama(n, nama_kode))
    an["periode"] = an["periode"].astype(int)
    pat_tahun = {(r.seri, r.periode) for r in pat[pat["patahan"]].itertuples()}
    galat_set = {(r.seri, int(r.kode), int(r.periode)) for r in galat.itertuples()}
    revisi_set = {(s, int(r.kode), int(r.periode)) for r in dedup[dedup["status"] == "revisi"].itertuples()
                  for s in ("var1458", TOTAL_RINCI)}
    pertama = obs[obs["nilai"].notna()].groupby(["seri", "kode"])["periode"].min().to_dict()
    persisten = (an[an["metode"] == "iqr_lintas_provinsi"].groupby(["seri", "kode"])["periode"].nunique() >= PERSISTEN_MIN).to_dict()
    kat, alasan = [], []
    for r in an.itertuples():
        k, t, s = int(r.kode), int(r.periode), r.seri
        anak = [pertama[(s, a)] for a in PEMEKARAN.get(k, []) if (s, a) in pertama]
        if (s, k, t) in galat_set:
            kat.append("galat_input"); alasan.append("bukti keras galat input (lihat tabel galat)")
        elif (s, k, t) in revisi_set:
            kat.append("revisi_snapshot"); alasan.append("nilai var1458 dan tabel rinci berbeda pada sel ini; keduanya disimpan")
        elif anak and t >= min(anak):
            kat.append("patahan_wilayah"); alasan.append(f"provinsi induk sejak provinsi hasil pemekarannya terbit ({min(anak)})")
        elif (s, t) in pat_tahun:
            kat.append("patahan_metode"); alasan.append("median perubahan seri menyimpang jauh dan hampir semua provinsi searah pada tahun ini")
        else:
            kat.append("outlier_asli")
            alasan.append("ditandai IQR lintas provinsi pada >= 3 tahun (persisten)" if persisten.get((s, k)) else
                          "tidak ada bukti galat atau patahan; dipertahankan sebagai nilai sah")
    an["kategori"], an["alasan_kategori"] = kat, alasan
    return an


def gambar_patahan(pat):
    fig, axs = plt.subplots(1, 3, figsize=(13, 3.8), sharey=False)
    for ax, seri in zip(axs, ["var1458", TOTAL_RINCI, "rinci / Perdesaan / Perempuan"]):
        g = pat[pat["seri"] == seri]
        ax.bar(g["periode"], g["median_perubahan"], color=["#b2182b" if p else "#92c5de" for p in g["patahan"]])
        ax.axhline(0, color="k", lw=.6)
        ax.set_title(seri.replace("rinci / ", ""), fontsize=8); ax.tick_params(labelsize=7)
        ax.set_xlabel("Tahun", fontsize=7)
    axs[0].set_ylabel("Median perubahan tahunan (poin)", fontsize=7)
    fig.suptitle("Median perubahan tahunan antarprovinsi (merah = patahan serentak)", fontsize=9)
    fig.tight_layout(); fig.savefig(GAMBAR / "patahan_median_perubahan.png", dpi=150); plt.close(fig)


def draf_log(f):
    return [
        ("silver", "semua",
         f"calon anomali dikategorikan: galat_input hanya bila ada bukti keras (nilai di luar 0 sampai 100, total di luar rentang komponennya, atau kunci kembar berbeda nilai); patahan_metode bila median perubahan tahunan satu seri menyimpang (|z robust| >= {Z_PATAHAN:g}) dan >= {SEARAH_MIN * 100:.0f} persen provinsi bergerak searah >= {LANGKAH_MIN:g} poin; patahan_wilayah untuk provinsi induk sejak provinsi hasil pemekarannya terbit; revisi_snapshot bila var1458 dan rinci berbeda pada sel yang sama; selain itu outlier_asli; yang bukan galat ditandai dan tidak diubah",
         "menghapus atau mengganti semua calon anomali dengan interpolasi atau winsorizing",
         "hanya galat input yang boleh diperbaiki; tanpa bukti galat, nilai ekstrem adalah data BPS yang sah; patahan dan outlier asli dijelaskan, bukan dibuang",
         f["n_sel_anomali"]),
        ("silver", "semua",
         f"tidak ada perbaikan galat input: {f['n_galat']} sel memenuhi bukti keras setelah diperiksa pada {f['n_sel_diperiksa']} sel terisi; tidak ada nilai yang diubah",
         "memperbaiki lonjakan tunggal (Papua Barat 2010 dan 2011, Kalimantan Barat 2010 dan 2011, dan sejenisnya) dengan rata-rata tahun tetangga",
         "lonjakan tunggal tidak punya bukti galat input dan wajar pada provinsi kecil bersampel terbatas; mengganti dengan angka rekaan sama dengan mengarang data",
         f["n_galat"]),
        ("silver", "var1458",
         f"deduplikasi dua snapshot (var1458 dan total tabel rinci) memakai aturan tertulis: angka sama pada sel yang sama adalah konfirmasi bukan duplikat yang salah; angka berbeda adalah revisi, kedua nilai disimpan beserta sumbernya (kunci Silver memuat _berkas_raw) dan nilai var1458 dipakai untuk analisis total (K-003)",
         "membuang salah satu baris dari pasangan yang berbeda, atau merata-ratakan keduanya",
         f"dari {f['n_pasangan']} pasangan sel, {f['n_sama']} sama dan {f['n_revisi']} berbeda (semuanya 2017); tidak ada kunci kembar di dalam satu tabel; membuang atau merata-ratakan menghilangkan jejak revisi yang perlu dijelaskan di tahap 6",
         f["n_revisi"]),
    ]


def tulis_laporan(f, ringkas, pat_tampil, kriteria, dedup_ringkas):
    catatan = "## Catatan temuan\n\n(belum diisi)\n"
    if LAPORAN.exists():  # jangan hapus catatan temuan yang sudah ditulis
        lama = LAPORAN.read_text(encoding="utf-8")
        i = lama.find("## Catatan temuan")
        if i != -1:
            catatan = lama[i:]
    teks = f"""# Kategori calon anomali dan deduplikasi (Tahap 3)

Dibuat oleh `src/silver/anomali_amh.py`. Memakai calon anomali tugas #12 ({f['n_baris_anomali']} baris, {f['n_sel_anomali']} sel unik) dan tabel tugas #14. Data mentah tidak diubah.
Hanya galat input yang boleh diperbaiki. Kategori lain ditandai dan dijelaskan, nilainya tetap.

## Kriteria (diperiksa berurutan)
{md_tabel(kriteria)}

## Hasil per kategori (sel unik)
Daftar lengkap tiap calon beserta alasan: `reports/profil/anomali_kategori.csv`.

{md_tabel(ringkas)}

## Patahan serentak (median perubahan tahunan)
Tahun dan seri yang memenuhi kriteria patahan_metode. Tabel seluruh seri dan tahun: `reports/profil/patahan_serentak.csv`.

{md_tabel(pat_tampil)}

![patahan](gambar/patahan_median_perubahan.png)

## Perbaikan galat input
{f['n_galat']} sel memenuhi bukti keras galat input dari {f['n_sel_diperiksa']} sel terisi, jadi tidak ada nilai yang diperbaiki. Berkas `reports/profil/perbaikan_galat.csv` hanya memuat judul kolom.

## Deduplikasi dua snapshot
Aturan: angka sama dari dua snapshot bukan duplikat yang salah (konfirmasi). Angka berbeda adalah revisi: kedua nilai disimpan beserta sumbernya, dan var1458 dipakai untuk total (K-003). Tidak ada kunci kembar di dalam satu tabel.
Daftar pasangan: `reports/profil/duplikat_dua_snapshot.csv`.

{md_tabel(dedup_ringkas)}

{catatan}"""
    LAPORAN.write_text(teks, encoding="utf-8")


def jalankan(tulis):
    mulai = time.time()
    n, salah = periksa()
    assert not salah, f"berkas mentah tidak cocok dengan MANIFEST: {salah}"
    print(f"sha256 raw OK ({n} berkas)")
    nama_kode, kode_nama = kamus_wilayah()
    provinsi = sorted(k for k in kode_nama if k != INDONESIA)
    obs = baca_pengamatan(nama_kode)
    grid = bangun_grid(obs, provinsi)
    pat = patahan_serentak(obs)
    galat = galat_input(obs)
    cmp_ = bandingkan_total(obs)
    dedup = deduplikasi(cmp_["tabel"])
    an = kategorikan(calon_anomali(baca_data()), obs, kode_nama, nama_kode, pat, galat, dedup)
    sel = an.drop_duplicates(["seri", "kode", "periode"])
    assert sel["kategori"].notna().all()
    jumlah = sel["kategori"].value_counts().reindex(KATEGORI, fill_value=0)

    ringkas = sel.groupby(["kategori"]).agg(sel=("kode", "size"), seri=("seri", "nunique"), provinsi=("kode", "nunique")).reindex(KATEGORI, fill_value=0).reset_index()
    pat_tampil = pat[pat["patahan"]][["seri", "periode", "n_provinsi", "median_perubahan", "z_robust", "pct_searah"]]
    kriteria = pd.DataFrame([
        ["galat_input", "nilai di luar 0 sampai 100; total di luar rentang komponennya; kunci kembar berbeda nilai", "boleh diperbaiki"],
        ["revisi_snapshot", "var1458 dan total rinci berbeda pada sel yang sama", "ditandai, dua nilai disimpan"],
        ["patahan_wilayah", "provinsi induk sejak provinsi hasil pemekarannya pertama terbit (mis. Papua 2024)", "ditandai, tidak diubah"],
        ["patahan_metode", f"|z robust| median perubahan seri >= {Z_PATAHAN:g} dan >= {SEARAH_MIN * 100:.0f} persen provinsi searah >= {LANGKAH_MIN:g} poin", "ditandai, tidak diubah"],
        ["outlier_asli", "sisanya (sering persisten di provinsi tertentu atau lonjakan tunggal)", "ditandai, tidak diubah"],
    ], columns=["kategori", "bukti", "tindakan"])
    dedup_ringkas = dedup.groupby("status").agg(pasangan=("kode", "size"), tahun=("periode", lambda x: " ".join(map(str, sorted(x.unique()))))).reset_index()
    f = {"n_baris_anomali": len(an), "n_sel_anomali": len(sel), "n_galat": len(galat),
         "n_sel_diperiksa": int(obs["nilai"].notna().sum()), "n_pasangan": len(dedup),
         "n_sama": int((dedup["status"] == "sama").sum()), "n_revisi": int((dedup["status"] == "revisi").sum())}

    OUT.mkdir(parents=True, exist_ok=True); GAMBAR.mkdir(parents=True, exist_ok=True)
    an.assign(provinsi=an["kode"].map(kode_nama))[["seri", "provinsi", "periode", "nilai", "metode", "alasan", "kategori", "alasan_kategori"]].to_csv(OUT / "anomali_kategori.csv", index=False)
    pat.to_csv(OUT / "patahan_serentak.csv", index=False)
    galat.to_csv(OUT / "perbaikan_galat.csv", index=False)
    dedup.assign(nama=dedup["kode"].map(kode_nama)).to_csv(OUT / "duplikat_dua_snapshot.csv", index=False)
    gambar_patahan(pat)
    tulis_laporan(f, ringkas, pat_tampil, kriteria, dedup_ringkas)

    baris = draf_log(f)
    print("\nKategori (sel unik):"); print(jumlah.to_string())
    print("\nPatahan serentak:"); print(pat_tampil.to_string(index=False))
    print(f"\ngalat input: {f['n_galat']}; deduplikasi: {f['n_sama']} sama, {f['n_revisi']} revisi dari {f['n_pasangan']} pasangan")
    print("\nDraf baris log-keputusan.csv:")
    for i, b in enumerate(baris, 1):
        print(f"  [{i}] tahap={b[0]} seri={b[1]} dampak_baris={b[5]}\n      {b[2]}")
    if tulis:
        print(f"\n{tulis_log(baris)} baris baru ditulis ke log-keputusan.csv")
    n_log = jumlah_log_saya(baris, tulis)
    patahan_sel = int(jumlah["patahan_metode"] + jumlah["patahan_wilayah"])
    print("\nPerintah metrics.json (jalankan sendiri setelah angkanya kamu periksa):")
    print(f"python -m src.common.hasil {NIM} baris_silver={int(obs['nilai'].notna().sum())} sel_kosong_grid={int(grid['nilai'].isna().sum())} "
          f"outlier_ditandai={f['n_sel_anomali']} sel_missing_sejati={int((grid['status'] == 'missing').sum())} "
          f"anomali_outlier_asli={int(jumlah['outlier_asli'])} anomali_patahan={patahan_sel} anomali_revisi_snapshot={int(jumlah['revisi_snapshot'])} "
          f"anomali_galat_input={f['n_galat']} keputusan_dicatat={n_log}")
    print(f"\nselesai dalam {time.time() - mulai:.1f} detik")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tulis-log", action="store_true", help="tambahkan baris keputusan ke log-keputusan.csv")
    jalankan(ap.parse_args().tulis_log)