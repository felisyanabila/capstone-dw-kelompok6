"""Tahap 3: grid provinsi x periode, status sel kosong, kelengkapan panel, dan sumber kanonik total.

Hanya membaca data/raw. Menghasilkan tabel dan laporan di reports/, tidak mengubah data mentah.
    python src/silver/grid_amh.py                 hitung dan tulis laporan, cetak draf log dan perintah metrics
    python src/silver/grid_amh.py --tulis-log     juga menambahkan baris keputusan ke log-keputusan.csv
"""
import argparse
import csv
import datetime
import io
import re
import sys
import time
from pathlib import Path

import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.common.manifest import periksa  # noqa: E402
from src.silver.profil_amh import baca_data, calon_anomali  # noqa: E402
from src.silver.wilayah import BPS, INDONESIA, TAHUN_BENTUK, kamus_wilayah, kode_dari_nama, normal  # noqa: E402

NIM = "124450001"
OUT = ROOT / "reports" / "profil"
GAMBAR = ROOT / "reports" / "gambar"
LAPORAN = ROOT / "reports" / "kelengkapan_panel.md"
LOG = ROOT / "log-keputusan.csv"
TOTAL_RINCI = "rinci / Perkotaan + Perdesaan / Laki-laki+Perempuan"
STATUS = ["terisi", "belum_ada_wilayah", "belum_terbit", "tidak_berlaku", "missing"]
WARNA = ["#2166ac", "#d9d9d9", "#f4a582", "#9970ab", "#b2182b"]


def baca_pengamatan(nama_kode):
    """Satu tabel panjang: seri, kode wilayah, periode, nilai (sel kosong tetap ada sebagai NaN)."""
    a = pd.read_csv(BPS / "sdg4_amh.csv")
    a = pd.DataFrame({"seri": "var1458", "tabel": "var1458", "kode": a["wilayah_id"].astype(int),
                      "nama_sumber": a["wilayah"], "periode": a["tahun"], "nilai": a["nilai"]})
    r = pd.read_csv(BPS / "sdg4_amh_rinci.csv")
    r = pd.DataFrame({"seri": "rinci / " + r["daerah"] + " / " + r["jenis_kelamin"], "tabel": "rinci",
                      "kode": r["wilayah"].map(lambda n: kode_dari_nama(n, nama_kode)),
                      "nama_sumber": r["wilayah"], "periode": r["tahun"], "nilai": r["nilai"]})
    return pd.concat([a, r], ignore_index=True)


def tabel_pemetaan(obs, kode_nama):
    p = obs[["tabel", "nama_sumber", "kode"]].drop_duplicates().copy()
    p["nama_baku"] = p["kode"].map(kode_nama)

    def cara(b):
        if b["tabel"] == "var1458":
            return "kode dari tabel"
        return "nama sama" if " ".join(b["nama_sumber"].upper().split()) == b["nama_baku"] else "alias ejaan (KEPULAUAN menjadi KEP.)"
    p["cara"] = p.apply(cara, axis=1)
    return p.sort_values(["tabel", "kode"]).reset_index(drop=True)


def status_sel(ada_tahun, kode, tahun):
    """Jenis sel pada satu provinsi, satu seri, satu tahun."""
    if tahun in ada_tahun:
        return "terisi"
    if kode in TAHUN_BENTUK and tahun < TAHUN_BENTUK[kode]:
        return "belum_ada_wilayah"          # provinsi belum dibentuk
    if not ada_tahun:
        return "tidak_berlaku"              # seri ini tidak pernah punya pengamatan untuk provinsi tsb
    if tahun < min(ada_tahun):
        return "belum_terbit"               # provinsi ada, seri belum terbit pada tahun awal
    return "missing"                        # kosong sesudah terbit pertama


def bangun_grid(obs, provinsi):
    baris = []
    for seri, g in obs.groupby("seri"):
        tahun_seri = range(int(g["periode"].min()), int(g["periode"].max()) + 1)
        ada = g[g["nilai"].notna() & (g["kode"] != INDONESIA)]
        nilai = ada.set_index(["kode", "periode"])["nilai"].to_dict()
        tahun_ada = ada.groupby("kode")["periode"].apply(set).to_dict()
        for kode in provinsi:
            for t in tahun_seri:
                baris.append((seri, kode, t, nilai.get((kode, t)),
                              status_sel(tahun_ada.get(kode, set()), kode, t)))
    return pd.DataFrame(baris, columns=["seri", "wilayah_kode", "periode", "nilai", "status"])


def kelengkapan(grid):
    c = pd.crosstab([grid["seri"], grid["periode"]], grid["status"]).reindex(columns=STATUS, fill_value=0)
    c["n_grid"] = c.sum(axis=1)
    c["pct_terisi_grid"] = (c["terisi"] / c["n_grid"] * 100).round(1)
    ada = c["n_grid"] - c["belum_ada_wilayah"] - c["tidak_berlaku"]
    c["pct_terisi_wilayah_ada"] = (c["terisi"] / ada * 100).round(1)
    return c.reset_index()


def bandingkan_total(obs):
    """Total var1458 vs total tabel rinci pada tahun beririsan (selisih dicatat, bukan dihapus)."""
    v = obs[obs["seri"] == "var1458"][["kode", "periode", "nilai"]].rename(columns={"nilai": "var1458"})
    r = obs[obs["seri"] == TOTAL_RINCI][["kode", "periode", "nilai"]].rename(columns={"nilai": "rinci_total"})
    m = v.merge(r, on=["kode", "periode"], how="inner").dropna()
    m["selisih"] = (m["rinci_total"] - m["var1458"]).round(2) + 0.0
    beda = m[m["selisih"].abs() > 0.01]
    prov = m[m["kode"] != INDONESIA]
    pv = prov.pivot(index="kode", columns="periode", values="var1458")
    pr = prov.pivot(index="kode", columns="periode", values="rinci_total")
    lengkap = pv[[2016, 2017, 2018]].dropna().index

    def arah(p):
        d1 = (p.loc[lengkap, 2017] - p.loc[lengkap, 2016]).mean()
        d2 = (p.loc[lengkap, 2018] - p.loc[lengkap, 2017]).mean()
        turun = int((p.loc[lengkap, 2018] < p.loc[lengkap, 2017]).sum())
        return round(float(d1), 2), round(float(d2), 2), turun
    return {
        "tabel": m, "n_pasangan": len(m), "n_beda": len(beda),
        "tahun_beda": sorted(beda["periode"].unique().tolist()),
        "n_beda_2017": int((beda["periode"] == 2017).sum()),
        "rata_selisih_2017": round(float(beda[beda["periode"] == 2017]["selisih"].mean()), 2),
        "maks_selisih_2017": round(float(beda["selisih"].abs().max()), 2),
        "n_prov_dibanding": len(lengkap), "arah_var1458": arah(pv), "arah_rinci": arah(pr),
        "n_rinci_total_beririsan": int(((obs["seri"] == TOTAL_RINCI) & obs["periode"].isin(v["periode"]) & obs["nilai"].notna()).sum()),
    }


def gambar_status(grid, seri, nama_berkas, kode_nama):
    g = grid[grid["seri"] == seri]
    p = g.pivot(index="wilayah_kode", columns="periode", values="status").map(STATUS.index)
    p.index = [kode_nama[k].title() for k in p.index]
    fig, ax = plt.subplots(figsize=(9, 9))
    ax.imshow(p.values, aspect="auto", cmap=ListedColormap(WARNA), vmin=0, vmax=len(STATUS) - 1)
    ax.set_yticks(range(len(p))); ax.set_yticklabels(p.index, fontsize=6)
    ax.set_xticks(range(len(p.columns))); ax.set_xticklabels(p.columns, rotation=90, fontsize=7)
    ax.set_title(f"Grid 38 provinsi: {seri}", fontsize=9)
    ax.legend(handles=[Patch(color=w, label=s) for w, s in zip(WARNA, STATUS)],
              loc="upper center", bbox_to_anchor=(0.5, -0.06), ncol=5, fontsize=7)
    fig.tight_layout(); fig.savefig(GAMBAR / nama_berkas, dpi=150); plt.close(fig)


def gambar_kelengkapan(kl):
    fig, ax = plt.subplots(figsize=(9, 4.5))
    for seri in ["var1458", TOTAL_RINCI, "rinci / Perdesaan / Laki-laki+Perempuan", "rinci / Perkotaan / Laki-laki+Perempuan"]:
        g = kl[kl["seri"] == seri]
        ax.plot(g["periode"], g["pct_terisi_grid"], marker="o", ms=3, label=seri)
    ax.set_ylim(0, 105); ax.set_xlabel("Tahun"); ax.set_ylabel("Persen sel terisi (dari 38 provinsi)")
    ax.set_title("Kelengkapan grid per tahun"); ax.legend(fontsize=7, loc="lower right")
    fig.tight_layout(); fig.savefig(GAMBAR / "kelengkapan_per_tahun.png", dpi=150); plt.close(fig)


def md_tabel(t):
    k = list(t.columns)
    baris = ["| " + " | ".join(k) + " |", "|" + "|".join(["---"] * len(k)) + "|"]
    for _, b in t.astype(object).iterrows():   # astype(object) menjaga bilangan bulat tidak jadi 2014.0
        baris.append("| " + " | ".join("" if pd.isna(v) else str(v).replace("|", "\\|") for v in b) + " |")
    return "\n".join(baris)


def draf_log(f):
    """Baris keputusan (id dan tanggal diisi saat ditulis). Angka dampak berasal dari data."""
    return [
        ("silver", "tabel:sdg4_amh_rinci",
         "nama provinsi di tabel rinci dipetakan ke kode BPS lewat kamus nama dari var1458 (nama dinormalkan, KEPULAUAN di awal menjadi KEP.); nama yang tidak dikenal menghentikan proses",
         "pencocokan nama mendekati (fuzzy) atau pemetaan manual per baris",
         "tabel rinci tidak punya kode; kamus eksak mudah diperiksa dan 39 nama semuanya cocok; hanya dua nama beda ejaan (KEPULAUAN BANGKA BELITUNG, KEPULAUAN RIAU); nama hanya jembatan ke kode, kunci akhir tetap kode (K-001)",
         f["baris_alias"]),
        ("silver", "var1458",
         "var1458 menjadi sumber kanonik angka total 2014 sampai 2025; tabel rinci dipakai untuk rincian daerah dan jenis kelamin dan sebagai satu-satunya total 2009 sampai 2013; selisih dicatat, tidak dihapus",
         "tabel rinci sebagai sumber kanonik total",
         f"kedua total identik pada 2014 sampai 2025 kecuali 2017 ({f['n_beda_2017']} sel berbeda, rata-rata selisih rinci {f['rata_selisih_2017']:+.2f}); pada 2017 var1458 naik mulus ({f['arah_var1458'][0]:+.2f} lalu {f['arah_var1458'][1]:+.2f}) sedangkan rinci melonjak lalu turun ({f['arah_rinci'][0]:+.2f} lalu {f['arah_rinci'][1]:+.2f}; {f['arah_rinci'][2]} dari {f['n_prov_dibanding']} provinsi turun ke 2018, var1458 hanya {f['arah_var1458'][2]}); var1458 juga membawa kode wilayah dan tanpa sel kosong",
         f["n_beda"]),
        ("silver", "semua",
         "sel kosong pada grid 38 provinsi dibagi empat jenis: belum ada wilayah (sebelum pemekaran), belum terbit (wilayah ada, seri belum terbit pada tahun awal), tidak berlaku (tidak ada pengamatan sama sekali, DKI Jakarta perdesaan) dan missing sejati (kosong sesudah terbit pertama); hanya jenis terakhir disebut missing; tidak ada yang diimputasi",
         "interpolasi, nilai provinsi induk (Papua) atau rata-rata nasional; menghapus Kalimantan Utara dan empat provinsi Papua baru dari grid",
         f"tidak ada celah di tengah deret ({f['n_missing']} missing sejati), semua kosong berada di awal deret atau pada seri yang tidak pernah ada; mengisi akan membuat angka yang tidak pernah dilaporkan BPS; patahan Papua 2023 ke 2024 tidak diperbaiki di sini",
         f["sel_kosong"]),
        ("silver", "semua",
         "Indonesia (kode 9999) dipisah dari 38 provinsi: grid provinsi dan tabel nasional disimpan terpisah dan tidak dijumlahkan",
         "membiarkan 9999 sebagai wilayah ke-39 dalam grid provinsi",
         "nilai nasional bukan provinsi; ikut dihitung akan menggeser rata-rata dan sebaran provinsi",
         f["baris_indonesia"]),
    ]


def tulis_log(baris):
    teks = LOG.read_text(encoding="utf-8")
    akhir = "\r\n" if "\r\n" in teks else "\n"
    ids = [int(x) for x in re.findall(r"^K-(\d+),", teks, flags=re.M)]
    sudah = {r["keputusan"] for r in csv.DictReader(io.StringIO(teks))}
    baru = [b for b in baris if b[2] not in sudah]
    nomor = max(ids, default=0)
    with open(LOG, "a", encoding="utf-8", newline="") as f:
        if teks and not teks.endswith("\n"):
            f.write(akhir)
        w = csv.writer(f, lineterminator=akhir)
        for tahap, seri, keputusan, alt, alasan, dampak in baru:
            nomor += 1
            w.writerow([f"K-{nomor:03d}", datetime.date.today().isoformat(), NIM, tahap, seri, keputusan, alt, alasan, dampak])
    return len(baru)


def jumlah_log_saya(baris, tulis):
    teks = LOG.read_text(encoding="utf-8")
    sudah = {r["keputusan"]: r["nim"] for r in csv.DictReader(io.StringIO(teks))}
    milik = sum(1 for v in sudah.values() if v == NIM)
    return milik + (0 if tulis else sum(1 for b in baris if b[2] not in sudah))


def tulis_laporan(f, kl, ringkas_seri, pemetaan, tahun_var, tahun_total):
    catatan = "## Catatan temuan\n\n(belum diisi)\n"
    if LAPORAN.exists():  # jangan hapus catatan temuan yang sudah ditulis
        lama = LAPORAN.read_text(encoding="utf-8")
        i = lama.find("## Catatan temuan")
        if i != -1:
            catatan = lama[i:]
    alias = pemetaan[pemetaan["cara"].str.startswith("alias")][["tabel", "nama_sumber", "nama_baku"]]
    teks = f"""# Kelengkapan panel provinsi x periode (Tahap 3)

Dibuat oleh `src/silver/grid_amh.py` (kamus wilayah di `src/silver/wilayah.py`). Data: `data/raw/bps/2026-10-17/`, tidak diubah.

## Cara membaca sel kosong
Grid dibentuk lebih dulu: setiap seri x 38 provinsi x setiap tahun pada rentang seri itu. Sel tanpa nilai dibagi empat jenis (K-004):

| Jenis | Arti | Disebut missing? |
|---|---|---|
| belum_ada_wilayah | tahun sebelum provinsi dibentuk (Kalimantan Utara 2012, empat provinsi Papua 2022) | tidak |
| belum_terbit | provinsi sudah ada, seri belum terbit pada tahun awal | tidak |
| tidak_berlaku | seri tidak pernah punya pengamatan untuk provinsi itu (DKI Jakarta perdesaan, diduga tidak punya daerah perdesaan) | tidak |
| missing | kosong sesudah pengamatan pertama | ya ({f['n_missing']} sel) |

## Ringkasan per seri
Tabel per seri dan tahun: `reports/profil/kelengkapan_per_seri_tahun.csv`.

{md_tabel(ringkas_seri)}

![kelengkapan](gambar/kelengkapan_per_tahun.png)

## Persen sel terisi per tahun (dari 38 provinsi)
var1458:

{md_tabel(tahun_var)}

Total tabel rinci (Perkotaan + Perdesaan, Laki-laki+Perempuan):

{md_tabel(tahun_total)}

![var1458](gambar/grid_status_var1458.png)
![rinci total](gambar/grid_status_rinci_total.png)
![rinci perdesaan](gambar/grid_status_rinci_perdesaan.png)

## Pemetaan wilayah ke 38 provinsi
Aturan K-001: kode BPS dua digit x 100, 9999 untuk Indonesia. var1458 sudah membawa kode. Tabel rinci hanya nama, jadi diberi kode lewat kamus dari var1458 (K-002). Daftar lengkap: `reports/profil/pemetaan_wilayah.csv`. Dua nama berbeda ejaan:

{md_tabel(alias.drop_duplicates())}

Baris Indonesia dipisah dari provinsi (K-005): `reports/profil/nasional_indonesia.csv` memuat {f['baris_indonesia']} baris, grid provinsi tidak memuatnya.

## Sumber kanonik angka total
Pilihan: **var1458** untuk 2014 sampai 2025 (K-003). Tabel rinci tetap dipakai untuk rincian dan untuk total 2009 sampai 2013.

- Pada tahun beririsan ({f['n_pasangan']} pasangan wilayah dan tahun) selisih lebih dari 0,01 hanya terjadi pada tahun {', '.join(map(str, f['tahun_beda']))}: {f['n_beda']} sel, rata-rata selisih rinci {f['rata_selisih_2017']:+.2f}, selisih terbesar {f['maks_selisih_2017']:.2f}.
- Arah 2016 ke 2017 ke 2018 (rata-rata perubahan {f['n_prov_dibanding']} provinsi yang lengkap): var1458 {f['arah_var1458'][0]:+.2f} lalu {f['arah_var1458'][1]:+.2f}, hanya {f['arah_var1458'][2]} provinsi turun ke 2018. Rinci {f['arah_rinci'][0]:+.2f} lalu {f['arah_rinci'][1]:+.2f}, dengan {f['arah_rinci'][2]} provinsi turun ke 2018.
- var1458 membawa kode wilayah dan tidak punya sel kosong. Tabel rinci hanya nama dan memuat 645 sel kosong.
- Daftar selisih: `reports/profil/kanonik_total_selisih.csv`. Angka rinci 2017 tidak dihapus; penjelasan selisih dikerjakan pada tahap 6.

## Angka untuk metrics.json
- baris_silver = {f['baris_silver']} (baris observasi BPS var1458 dan rinci yang terisi, setelah pemetaan wilayah)
- sel_kosong_grid = {f['sel_kosong']} (sel grid 38 provinsi tanpa nilai, semua jenis)
- outlier_ditandai = {f['outlier']} (sel unik seri x provinsi x periode yang ditandai di tugas #12)

{catatan}"""
    LAPORAN.write_text(teks, encoding="utf-8")


def jalankan(tulis):
    mulai = time.time()
    n, salah = periksa()
    assert not salah, f"berkas mentah tidak cocok dengan MANIFEST: {salah}"
    print(f"sha256 raw OK ({n} berkas)")
    nama_kode, kode_nama = kamus_wilayah()
    provinsi = sorted(k for k in kode_nama if k != INDONESIA)
    assert len(provinsi) == 38, f"harus 38 provinsi, ditemukan {len(provinsi)}"
    obs = baca_pengamatan(nama_kode)
    pemetaan = tabel_pemetaan(obs, kode_nama)
    grid = bangun_grid(obs, provinsi)
    kl = kelengkapan(grid)
    cmp_ = bandingkan_total(obs)
    nasional = obs[(obs["kode"] == INDONESIA) & obs["nilai"].notna()][["seri", "periode", "nilai"]]
    nasional = nasional.sort_values(["seri", "periode"])

    ringkas = (grid.groupby(["seri", "status"]).size().unstack(fill_value=0).reindex(columns=STATUS, fill_value=0))
    ringkas["n_grid"] = ringkas.sum(axis=1)
    ringkas["pct_terisi_grid"] = (ringkas["terisi"] / ringkas["n_grid"] * 100).round(1)
    ringkas = ringkas.reset_index()
    tahun_var = kl[kl["seri"] == "var1458"][["periode", "terisi", "belum_ada_wilayah", "belum_terbit", "pct_terisi_grid", "pct_terisi_wilayah_ada"]]
    tahun_total = kl[kl["seri"] == TOTAL_RINCI][["periode", "terisi", "belum_ada_wilayah", "belum_terbit", "pct_terisi_grid", "pct_terisi_wilayah_ada"]]

    alias_nama = set(pemetaan[pemetaan["cara"].str.startswith("alias")]["nama_sumber"])
    rinci = obs[obs["tabel"] == "rinci"]
    unik = calon_anomali(baca_data())[["seri", "provinsi", "periode"]].drop_duplicates()
    fakta = {
        **cmp_,
        "baris_alias": int(rinci["nama_sumber"].isin(alias_nama).sum()),
        "baris_indonesia": len(nasional),
        "n_missing": int((grid["status"] == "missing").sum()),
        "sel_kosong": int(grid["nilai"].isna().sum()),
        "baris_silver": int(obs["nilai"].notna().sum()),
        "outlier": len(unik),
    }

    OUT.mkdir(parents=True, exist_ok=True); GAMBAR.mkdir(parents=True, exist_ok=True)
    pemetaan.to_csv(OUT / "pemetaan_wilayah.csv", index=False)
    g = grid.assign(nama_provinsi=grid["wilayah_kode"].map(kode_nama))
    g[["seri", "wilayah_kode", "nama_provinsi", "periode", "nilai", "status"]].to_csv(OUT / "grid_provinsi.csv", index=False)
    nasional.to_csv(OUT / "nasional_indonesia.csv", index=False)
    kl.to_csv(OUT / "kelengkapan_per_seri_tahun.csv", index=False)
    cmp_["tabel"].assign(nama=lambda d: d["kode"].map(kode_nama)).to_csv(OUT / "kanonik_total_selisih.csv", index=False)
    gambar_status(grid, "var1458", "grid_status_var1458.png", kode_nama)
    gambar_status(grid, TOTAL_RINCI, "grid_status_rinci_total.png", kode_nama)
    gambar_status(grid, "rinci / Perdesaan / Laki-laki+Perempuan", "grid_status_rinci_perdesaan.png", kode_nama)
    gambar_kelengkapan(kl)
    tulis_laporan(fakta, kl, ringkas, pemetaan, tahun_var, tahun_total)

    baris = draf_log(fakta)
    print("\nRingkasan grid per seri:")
    print(ringkas.to_string(index=False))
    print(f"\nsel grid: {len(grid)}; kosong: {fakta['sel_kosong']}; missing sejati: {fakta['n_missing']}")
    print(f"total var1458 vs rinci: {cmp_['n_beda']} sel berbeda pada tahun {cmp_['tahun_beda']}")
    print(f"arah 2016>2017>2018 var1458 {cmp_['arah_var1458']}, rinci {cmp_['arah_rinci']}")
    print("\nDraf baris log-keputusan.csv:")
    for i, b in enumerate(baris, 1):
        print(f"  [{i}] tahap={b[0]} seri={b[1]} dampak_baris={b[5]}\n      {b[2]}")
    if tulis:
        print(f"\n{tulis_log(baris)} baris baru ditulis ke log-keputusan.csv")
    n_log = jumlah_log_saya(baris, tulis)
    print("\nPerintah metrics.json (jalankan sendiri setelah angkanya kamu periksa):")
    print(f"python -m src.common.hasil {NIM} baris_silver={fakta['baris_silver']} sel_kosong_grid={fakta['sel_kosong']} "
          f"outlier_ditandai={fakta['outlier']} sel_missing_sejati={fakta['n_missing']} keputusan_dicatat={n_log}")
    print(f"\nselesai dalam {time.time() - mulai:.1f} detik")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tulis-log", action="store_true", help="tambahkan baris keputusan ke log-keputusan.csv")
    jalankan(ap.parse_args().tulis_log)