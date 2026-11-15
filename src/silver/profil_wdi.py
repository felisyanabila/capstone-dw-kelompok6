"""Tahap 2: profil seri pembanding SE.ADT.LITR.ZS (WDI) dan kandidat rincian yang sebanding.

Hanya membaca data/raw, tidak mengubahnya. Menemukan, bukan memperbaiki.
Jalankan dari akar repo:  python src/silver/profil_wdi.py
"""
import json
import sys
from pathlib import Path

import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.common.manifest import periksa  # noqa: E402

WDI = ROOT / "data" / "raw" / "wdi" / "2026-10-20"
BPS = ROOT / "data" / "raw" / "bps" / "2026-10-17"
OUT = ROOT / "reports" / "profil"
GAMBAR = ROOT / "reports" / "gambar"
INDONESIA = "INDONESIA"

# keluarga indikator melek aksara yang ikut dalam berkas WDI: (umur, jenis kelamin)
KELUARGA = {
    "SE.ADT.LITR.ZS": ("15 tahun ke atas", "total"),
    "SE.ADT.LITR.MA.ZS": ("15 tahun ke atas", "laki-laki"),
    "SE.ADT.LITR.FE.ZS": ("15 tahun ke atas", "perempuan"),
    "SE.ADT.1524.LT.ZS": ("15 sampai 24 tahun", "total"),
    "SE.ADT.1524.LT.MA.ZS": ("15 sampai 24 tahun", "laki-laki"),
    "SE.ADT.1524.LT.FE.ZS": ("15 sampai 24 tahun", "perempuan"),
    "SE.ADT.1524.LT.FM.ZS": ("15 sampai 24 tahun", "rasio perempuan banding laki-laki"),
}

# padanan di tabel rinci BPS (daerah gabungan, Indonesia): kode indikator -> jenis kelamin rinci
PADANAN_RINCI = {
    "SE.ADT.LITR.ZS": "Laki-laki+Perempuan",
    "SE.ADT.LITR.MA.ZS": "Laki-laki",
    "SE.ADT.LITR.FE.ZS": "Perempuan",
}


def baca_wdi():
    d = json.load(open(WDI / "data" / "kelompok-03-hal-01.json", encoding="utf-8"))[1]
    meta = json.load(open(WDI / "metadata" / "sumber2_indikator.json", encoding="utf-8"))[1]
    nama = {m["id"]: m for m in meta}
    baris = []
    for r in d:
        k = r["indicator"]["id"]
        if k in KELUARGA:
            baris.append({
                "indikator": k, "tahun": int(r["date"]), "nilai": r["value"],
                "unit_api": r.get("unit", ""),
            })
    df = pd.DataFrame(baris)
    df["nama"] = df["indikator"].map(lambda k: nama[k]["name"])
    df["umur"] = df["indikator"].map(lambda k: KELUARGA[k][0])
    df["jenis_kelamin"] = df["indikator"].map(lambda k: KELUARGA[k][1])
    df["ada"] = df["nilai"].notna()
    return df.sort_values(["indikator", "tahun"]).reset_index(drop=True), nama


def baca_bps_indonesia():
    a = pd.read_csv(BPS / "sdg4_amh.csv")
    a = a[a["wilayah"].str.upper() == INDONESIA][["tahun", "nilai"]].rename(columns={"nilai": "var1458"})
    r = pd.read_csv(BPS / "sdg4_amh_rinci.csv")
    r = r[(r["wilayah"].str.upper() == INDONESIA) & (r["daerah"] == "Perkotaan + Perdesaan")]
    r = r.pivot(index="tahun", columns="jenis_kelamin", values="nilai").reset_index()
    return a, r


def ringkasan(df, a, r):
    tahun_var, tahun_rinci = set(a["tahun"]), set(r["tahun"])
    hasil = []
    for k, g in df.groupby("indikator"):
        ada = g[g["ada"]]["tahun"].tolist()
        hasil.append({
            "indikator": k, "nama": g["nama"].iloc[0], "umur": g["umur"].iloc[0],
            "jenis_kelamin": g["jenis_kelamin"].iloc[0], "daerah": "tidak ada (hanya nasional)",
            "n_tahun_ada": len(ada), "n_tahun_diminta": len(g),
            "tahun_pertama": min(ada) if ada else None, "tahun_terakhir": max(ada) if ada else None,
            "unit_di_api": g["unit_api"].iloc[0] or "(kosong)",
            "satuan_dari_nama": "indeks (GPI)" if "GPI" in g["nama"].iloc[0] else "persen",
            "tahun_ada": " ".join(map(str, ada)),
            "irisan_var1458": " ".join(str(t) for t in ada if t in tahun_var),
            "irisan_rinci": " ".join(str(t) for t in ada if t in tahun_rinci),
        })
    return pd.DataFrame(hasil)


def perbandingan(df, a, r):
    """Nilai WDI vs BPS Indonesia pada tahun beririsan (selisih dijelaskan di tahap 6)."""
    baris = []
    for k, jk in PADANAN_RINCI.items():
        g = df[(df["indikator"] == k) & df["ada"]][["tahun", "nilai"]].rename(columns={"nilai": "wdi"})
        m = g.merge(r[["tahun", jk]].rename(columns={jk: "bps_rinci"}), on="tahun", how="inner")
        if k == "SE.ADT.LITR.ZS":
            m = m.merge(a, on="tahun", how="left")
        else:
            m["var1458"] = float("nan")
        m.insert(0, "indikator", k)
        baris.append(m)
    b = pd.concat(baris, ignore_index=True)
    b["selisih_wdi_rinci"] = (b["wdi"] - b["bps_rinci"]).round(2) + 0.0   # + 0.0 membuang tanda minus pada nol
    b["selisih_wdi_var1458"] = (b["wdi"] - b["var1458"]).round(2) + 0.0
    b["wdi"] = b["wdi"].round(2)
    return b


def kandidat(rg):
    irisan = {x["indikator"]: x for x in rg.to_dict("records")}
    baris = []
    def tambah(k, padanan, status, alasan):
        baris.append({"indikator_wdi": k, "padanan_bps": padanan, "status": status,
                      "tahun_irisan_rinci": irisan[k]["irisan_rinci"],
                      "tahun_irisan_var1458": irisan[k]["irisan_var1458"], "alasan": alasan})
    tambah("SE.ADT.LITR.ZS", "var1458 Indonesia; rinci Indonesia, Perkotaan + Perdesaan, Laki-laki+Perempuan",
           "kandidat utama",
           "umur sama (15 tahun ke atas), total semua jenis kelamin dan daerah, satuan persen, tingkat nasional")
    tambah("SE.ADT.LITR.MA.ZS", "rinci Indonesia, Perkotaan + Perdesaan, Laki-laki", "kandidat",
           "umur sama (15 tahun ke atas), jenis kelamin laki-laki, nasional")
    tambah("SE.ADT.LITR.FE.ZS", "rinci Indonesia, Perkotaan + Perdesaan, Perempuan", "kandidat",
           "umur sama (15 tahun ke atas), jenis kelamin perempuan, nasional")
    for k in ["SE.ADT.1524.LT.ZS", "SE.ADT.1524.LT.MA.ZS", "SE.ADT.1524.LT.FE.ZS"]:
        tambah(k, "tidak ada", "ditolak",
               "rentang umur 15 sampai 24 tahun, sedangkan seri BPS 15 tahun ke atas; definisi penduduk berbeda")
    tambah("SE.ADT.1524.LT.FM.ZS", "tidak ada", "ditolak",
           "berupa rasio (indeks paritas), bukan persen; juga rentang umur 15 sampai 24 tahun")
    baris.append({"indikator_wdi": "(rincian daerah)", "padanan_bps": "rinci Perkotaan dan Perdesaan",
                  "status": "tidak ada padanan",
                  "tahun_irisan_rinci": "", "tahun_irisan_var1458": "",
                  "alasan": "WDI hanya nasional gabungan; tidak ada pemisahan perkotaan dan perdesaan"})
    return pd.DataFrame(baris)


def gambar(df, a, r):
    GAMBAR.mkdir(parents=True, exist_ok=True)
    # ketersediaan indikator x tahun
    p = df.pivot(index="indikator", columns="tahun", values="ada").astype(float)
    fig, ax = plt.subplots(figsize=(12, 3.5))
    ax.imshow(p.values, aspect="auto", cmap="Blues", vmin=0, vmax=1)
    ax.set_yticks(range(len(p))); ax.set_yticklabels(p.index, fontsize=7)
    kol = list(p.columns)
    pos = [i for i, t in enumerate(kol) if t % 5 == 0]
    ax.set_xticks(pos); ax.set_xticklabels([kol[i] for i in pos], fontsize=7)
    ax.set_title("SE.ADT.LITR.ZS dan keluarganya: ada (biru) atau kosong (putih) per tahun, Indonesia")
    fig.tight_layout(); fig.savefig(GAMBAR / "wdi_ketersediaan.png", dpi=150); plt.close(fig)

    # WDI total vs BPS
    w = df[(df["indikator"] == "SE.ADT.LITR.ZS") & df["ada"]]
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(w["tahun"], w["nilai"], "o-", label="WDI SE.ADT.LITR.ZS")
    ax.plot(a["tahun"], a["var1458"], "s--", label="BPS var1458 (Indonesia)")
    t = r[["tahun", "Laki-laki+Perempuan"]]
    ax.plot(t["tahun"], t["Laki-laki+Perempuan"], "^:", label="BPS rinci (Indonesia, total)")
    ax.set_title("Angka melek aksara 15 tahun ke atas: WDI dan BPS, Indonesia")
    ax.set_xlabel("Tahun"); ax.set_ylabel("Persen"); ax.legend()
    fig.tight_layout(); fig.savefig(GAMBAR / "wdi_vs_bps_indonesia.png", dpi=150); plt.close(fig)


def md_tabel(t):
    k = list(t.columns)
    baris = ["| " + " | ".join(k) + " |", "|" + "|".join(["---"] * len(k)) + "|"]
    for _, b in t.iterrows():
        baris.append("| " + " | ".join("" if pd.isna(v) else str(v) for v in b) + " |")
    return "\n".join(baris)


def tulis_laporan(rg, kd, pb):
    jalur = ROOT / "reports" / "profil_wdi.md"
    catatan = "## Catatan temuan\n\n(belum diisi)\n"
    if jalur.exists():  # jangan hapus catatan temuan yang sudah ditulis
        lama = jalur.read_text(encoding="utf-8")
        i = lama.find("## Catatan temuan")
        if i != -1:
            catatan = lama[i:]
    kolom = ["indikator", "umur", "jenis_kelamin", "n_tahun_ada", "tahun_pertama", "tahun_terakhir",
             "unit_di_api", "satuan_dari_nama", "irisan_var1458", "irisan_rinci"]
    teks = f"""# Profil seri pembanding SE.ADT.LITR.ZS (WDI), Tahap 2

Dibuat oleh `src/silver/profil_wdi.py`. Data: `data/raw/wdi/2026-10-20/` (tidak diubah).
Hasil dipakai untuk memilih rincian yang sebanding pada tahap 6.

## Ketersediaan per indikator
Tabel lengkap seri x periode x rincian: `reports/profil/wdi_ketersediaan.csv`.
Ringkasan per indikator: `reports/profil/wdi_ringkasan_indikator.csv`.

{md_tabel(rg[kolom])}

![ketersediaan](gambar/wdi_ketersediaan.png)

## Kandidat rincian yang sebanding dengan seri utama
Berkas: `reports/profil/wdi_kandidat_sebanding.csv`.

{md_tabel(kd)}

## Nilai pada tahun beririsan (bahan tahap 6)
Selisih hanya dicatat di sini. Penjelasannya dikerjakan pada tahap 6.
Berkas: `reports/profil/wdi_vs_bps_tahun_beririsan.csv`.

{md_tabel(pb)}

![perbandingan](gambar/wdi_vs_bps_indonesia.png)

{catatan}"""
    jalur.write_text(teks, encoding="utf-8")


def jalankan():
    n, salah = periksa()
    assert not salah, f"berkas mentah tidak cocok dengan MANIFEST: {salah}"
    print(f"sha256 raw OK ({n} berkas)")
    df, _ = baca_wdi()
    a, r = baca_bps_indonesia()
    rg = ringkasan(df, a, r)
    kd = kandidat(rg)
    pb = perbandingan(df, a, r)
    OUT.mkdir(parents=True, exist_ok=True)
    df.drop(columns=["unit_api"]).to_csv(OUT / "wdi_ketersediaan.csv", index=False)
    rg.to_csv(OUT / "wdi_ringkasan_indikator.csv", index=False)
    kd.to_csv(OUT / "wdi_kandidat_sebanding.csv", index=False)
    pb.to_csv(OUT / "wdi_vs_bps_tahun_beririsan.csv", index=False)
    gambar(df, a, r)
    tulis_laporan(rg, kd, pb)
    print(rg[["indikator", "n_tahun_ada", "tahun_pertama", "tahun_terakhir", "irisan_var1458", "irisan_rinci"]].to_string(index=False))
    print(kd[["indikator_wdi", "status"]].to_string(index=False))
    print(pb.to_string(index=False))


if __name__ == "__main__":
    jalankan()