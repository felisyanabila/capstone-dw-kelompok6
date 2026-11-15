"""Tahap 2: profil dan calon anomali untuk var1458 dan tabel sdg4_amh_rinci.

Menemukan, bukan memperbaiki. Hanya membaca data/raw, tidak mengubahnya.
Jalankan dari akar repo:  python src/silver/profil_amh.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.common.manifest import periksa  # noqa: E402

RAW = ROOT / "data" / "raw" / "bps" / "2026-10-17"
OUT = ROOT / "reports" / "profil"
GAMBAR = ROOT / "reports" / "gambar"
Z_BATAS = 2.5      # |z| dalam satu provinsi
IQR_K = 1.5        # pagar Tukey untuk lintas provinsi
IQR_LOMPAT = 3.0   # pagar lebih longgar untuk selisih tahunan (pagar "jauh")
INDONESIA = "INDONESIA"


def baca_data():
    a = pd.read_csv(RAW / "sdg4_amh.csv")
    a = a.drop(columns="periode").rename(columns={"tahun": "periode"})
    a["seri"] = "var1458"
    a["wilayah"] = a["wilayah"].str.strip().str.upper()
    a = a[["seri", "wilayah", "periode", "nilai"]]

    r = pd.read_csv(RAW / "sdg4_amh_rinci.csv")
    r["wilayah"] = r["wilayah"].str.strip().str.upper()
    r["seri"] = "rinci | " + r["daerah"] + " | " + r["jenis_kelamin"]
    r = r.rename(columns={"tahun": "periode"})[["seri", "wilayah", "periode", "nilai"]]
    return pd.concat([a, r], ignore_index=True)


def agregat(g):
    """Statistik deskriptif untuk satu groupby atas kolom nilai."""
    n = g["nilai"]
    return pd.DataFrame({
        "n_terisi": n.count(), "rata2": n.mean(), "simpangan_baku": n.std(),
        "min": n.min(), "q1": n.quantile(.25), "median": n.median(),
        "q3": n.quantile(.75), "maks": n.max(),
    })


def statistik(df):
    prov = df[df["wilayah"] != INDONESIA]
    per_seri = agregat(prov.groupby("seri"))
    per_seri["n_sel"] = prov.groupby("seri").size()
    per_seri["n_kosong"] = per_seri["n_sel"] - per_seri["n_terisi"]
    per_seri["pct_kosong"] = (per_seri["n_kosong"] / per_seri["n_sel"] * 100).round(1)
    per_prov = agregat(df.groupby(["seri", "wilayah"]))
    per_prov["n_sel"] = df.groupby(["seri", "wilayah"]).size()
    per_prov["n_kosong"] = per_prov["n_sel"] - per_prov["n_terisi"]
    return per_seri.reset_index().round(3), per_prov.reset_index().round(3)


def laporan_kosong(df):
    k = df[df["nilai"].isna()]
    return (k.groupby(["seri", "wilayah"])["periode"]
              .agg(n_kosong="count", dari="min", sampai="max").reset_index())


def pagar(x, k=IQR_K):
    q1, q3 = x.quantile(.25), x.quantile(.75)
    i = q3 - q1
    return q1 - k * i, q3 + k * i


def calon_anomali(df):
    hasil = []
    prov = df[(df["wilayah"] != INDONESIA) & df["nilai"].notna()].copy()

    # 1. IQR lintas provinsi: satu seri, satu periode
    for (seri, per), g in prov.groupby(["seri", "periode"]):
        if len(g) < 8:
            continue
        lo, hi = pagar(g["nilai"])
        for _, b in g[(g["nilai"] < lo) | (g["nilai"] > hi)].iterrows():
            hasil.append((seri, b["wilayah"], per, b["nilai"], "iqr_lintas_provinsi",
                          f"di luar pagar [{lo:.2f}; {hi:.2f}] antarprovinsi pada periode itu"))

    # 2. z-score dalam deret satu provinsi
    for (seri, w), g in prov.groupby(["seri", "wilayah"]):
        if len(g) < 6 or g["nilai"].std() == 0:
            continue
        z = (g["nilai"] - g["nilai"].mean()) / g["nilai"].std()
        for idx in z[z.abs() >= Z_BATAS].index:
            hasil.append((seri, w, g.loc[idx, "periode"], g.loc[idx, "nilai"], "z_dalam_provinsi",
                          f"z = {z[idx]:.2f} terhadap deret provinsi itu sendiri"))

    # 3. lompatan antartahun (kandidat patahan atau galat input)
    prov = prov.sort_values(["seri", "wilayah", "periode"])
    prov["selisih"] = prov.groupby(["seri", "wilayah"])["nilai"].diff()
    prov["jeda"] = prov.groupby(["seri", "wilayah"])["periode"].diff()
    d = prov[prov["jeda"] == 1]
    for seri, g in d.groupby("seri"):
        lo, hi = pagar(g["selisih"], IQR_LOMPAT)
        for _, b in g[(g["selisih"] < lo) | (g["selisih"] > hi)].iterrows():
            hasil.append((seri, b["wilayah"], b["periode"], b["nilai"], "lompatan_tahunan",
                          f"selisih {b['selisih']:+.2f} poin dari tahun sebelumnya, "
                          f"di luar pagar [{lo:.2f}; {hi:.2f}]"))

    out = pd.DataFrame(hasil, columns=["seri", "provinsi", "periode", "nilai", "metode", "alasan"])
    return out.sort_values(["seri", "provinsi", "periode", "metode"]).reset_index(drop=True)


def gambar(df):
    GAMBAR.mkdir(parents=True, exist_ok=True)
    prov = df[df["wilayah"] != INDONESIA]

    # a. var1458: boxplot per tahun
    a = prov[prov["seri"] == "var1458"].dropna(subset=["nilai"])
    tahun = sorted(a["periode"].unique())
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.boxplot([a[a["periode"] == t]["nilai"] for t in tahun], tick_labels=tahun)
    ax.set_title("var1458: angka melek aksara (%) antarprovinsi per tahun")
    ax.set_xlabel("Tahun"); ax.set_ylabel("Persen")
    fig.tight_layout(); fig.savefig(GAMBAR / "var1458_boxplot_per_tahun.png", dpi=150); plt.close(fig)

    # b. var1458: deret waktu semua provinsi
    fig, ax = plt.subplots(figsize=(9, 4.5))
    for w, g in a.groupby("wilayah"):
        ax.plot(g["periode"], g["nilai"], color="#9aa5b1", lw=.8)
    i = df[(df["seri"] == "var1458") & (df["wilayah"] == INDONESIA)]
    ax.plot(i["periode"], i["nilai"], color="#c0392b", lw=2.2, label="Indonesia")
    ax.set_title("var1458: deret waktu per provinsi (abu-abu) dan Indonesia")
    ax.set_xlabel("Tahun"); ax.set_ylabel("Persen"); ax.legend()
    fig.tight_layout(); fig.savefig(GAMBAR / "var1458_deret_waktu.png", dpi=150); plt.close(fig)

    # c. rinci: boxplot per seri (9 seri)
    r = prov[prov["seri"].str.startswith("rinci")].dropna(subset=["nilai"])
    seri = sorted(r["seri"].unique())
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.boxplot([r[r["seri"] == s]["nilai"] for s in seri],
               tick_labels=[s.replace("rinci | ", "").replace(" | ", "\n") for s in seri])
    ax.set_title("sdg4_amh_rinci: sebaran nilai (%) per seri, semua provinsi dan tahun")
    ax.set_ylabel("Persen"); ax.tick_params(axis="x", labelsize=7)
    fig.tight_layout(); fig.savefig(GAMBAR / "rinci_boxplot_per_seri.png", dpi=150); plt.close(fig)

    # d. rinci: deret waktu per seri (small multiples)
    fig, axs = plt.subplots(3, 3, figsize=(12, 9), sharex=True, sharey=True)
    for ax, s in zip(axs.ravel(), seri):
        g = r[r["seri"] == s]
        for w, h in g.groupby("wilayah"):
            ax.plot(h["periode"], h["nilai"], color="#9aa5b1", lw=.6)
        ind = df[(df["seri"] == s) & (df["wilayah"] == INDONESIA)]
        ax.plot(ind["periode"], ind["nilai"], color="#c0392b", lw=1.8)
        ax.set_title(s.replace("rinci | ", ""), fontsize=8)
    fig.suptitle("sdg4_amh_rinci: deret waktu per provinsi (abu-abu) dan Indonesia (merah)")
    fig.tight_layout(); fig.savefig(GAMBAR / "rinci_deret_waktu_per_seri.png", dpi=150); plt.close(fig)

    # e. peta panas kekosongan (provinsi x tahun) untuk rinci
    k = df[df["seri"].str.startswith("rinci")].copy()
    k["kosong"] = k["nilai"].isna().astype(int)
    p = k.pivot_table(index="wilayah", columns="periode", values="kosong", aggfunc="mean")
    fig, ax = plt.subplots(figsize=(9, 9))
    im = ax.imshow(p.values, aspect="auto", cmap="Reds", vmin=0, vmax=1)
    ax.set_yticks(range(len(p))); ax.set_yticklabels(p.index, fontsize=6)
    ax.set_xticks(range(len(p.columns))); ax.set_xticklabels(p.columns, rotation=90, fontsize=7)
    ax.set_title("sdg4_amh_rinci: porsi sel kosong per provinsi dan tahun")
    fig.colorbar(im, ax=ax, shrink=.6)
    fig.tight_layout(); fig.savefig(GAMBAR / "rinci_kekosongan.png", dpi=150); plt.close(fig)


def md_tabel(t, maks=None):
    t = t.head(maks) if maks else t
    k = list(t.columns)
    baris = ["| " + " | ".join(k) + " |", "|" + "|".join(["---"] * len(k)) + "|"]
    for _, b in t.iterrows():
        baris.append("| " + " | ".join("" if pd.isna(v) else str(v) for v in b) + " |")
    return "\n".join(baris)


def tulis_laporan(per_seri, kosong, anomali):
    ringkas_anom = anomali.groupby(["seri", "metode"]).size().rename("jumlah").reset_index()
    teks = f"""# Profil awal AMH: var1458 dan sdg4_amh_rinci (Tahap 2)

Dibuat oleh `src/silver/profil_amh.py`. Tujuan tahap ini menemukan, bukan memperbaiki.
Data: `data/raw/bps/2026-10-17/` (sdg4_amh.csv dan sdg4_amh_rinci.csv), tidak diubah.
Statistik per seri dihitung pada tingkat provinsi (Indonesia dikeluarkan dan dilaporkan terpisah).

## Statistik deskriptif per seri
Rinci lengkap per provinsi ada di `reports/profil/statistik_provinsi.csv`.

{md_tabel(per_seri)}

## Sel kosong
{len(kosong)} kombinasi seri dan provinsi memiliki sel kosong (daftar lengkap di `reports/profil/sel_kosong.csv`).
Pola kosong ini diperlakukan sebagai temuan, bukan galat: tidak diisi dan tidak dihapus pada tahap ini.

## Calon anomali
Metode: (1) IQR lintas provinsi dengan pagar {IQR_K} x IQR per seri dan periode,
(2) z-score dalam deret satu provinsi dengan batas |z| >= {Z_BATAS},
(3) lompatan antartahun di luar pagar {IQR_LOMPAT} x IQR atas selisih tahunan.
Daftar lengkap (provinsi, periode, alasan) ada di `reports/profil/calon_anomali.csv`.
Calon belum tentu salah. Pemilahan antara nilai asli, patahan deret, dan galat input dikerjakan di tugas #15.

{md_tabel(ringkas_anom)}

## Grafik
- `reports/gambar/var1458_boxplot_per_tahun.png`
- `reports/gambar/var1458_deret_waktu.png`
- `reports/gambar/rinci_boxplot_per_seri.png`
- `reports/gambar/rinci_deret_waktu_per_seri.png`
- `reports/gambar/rinci_kekosongan.png`

![var1458 boxplot](gambar/var1458_boxplot_per_tahun.png)
![var1458 deret waktu](gambar/var1458_deret_waktu.png)
![rinci boxplot](gambar/rinci_boxplot_per_seri.png)
![rinci deret waktu](gambar/rinci_deret_waktu_per_seri.png)
![rinci kekosongan](gambar/rinci_kekosongan.png)

## Catatan temuan (isi sendiri setelah membaca keluaran)
- 
"""
    (ROOT / "reports" / "profil_amh.md").write_text(teks, encoding="utf-8")


def jalankan():
    n, salah = periksa()
    assert not salah, f"berkas mentah tidak cocok dengan MANIFEST: {salah}"
    print(f"sha256 raw OK ({n} berkas)")
    df = baca_data()
    OUT.mkdir(parents=True, exist_ok=True)
    per_seri, per_prov = statistik(df)
    kosong = laporan_kosong(df)
    anomali = calon_anomali(df)
    per_seri.to_csv(OUT / "statistik_seri.csv", index=False)
    per_prov.to_csv(OUT / "statistik_provinsi.csv", index=False)
    kosong.to_csv(OUT / "sel_kosong.csv", index=False)
    anomali.to_csv(OUT / "calon_anomali.csv", index=False)
    gambar(df)
    tulis_laporan(per_seri, kosong, anomali)
    print(per_seri.to_string(index=False))
    print(f"\nsel kosong: {len(kosong)} kombinasi; calon anomali: {len(anomali)} baris")
    print(anomali.groupby(["seri", "metode"]).size())


if __name__ == "__main__":
    jalankan()