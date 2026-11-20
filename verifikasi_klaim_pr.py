"""Mereproduksi pemeriksaan klaim di deskripsi PR Sprint 1 terhadap data mentah dan laporan di repo.

Jalankan dari folder utama repo (setelah git pull origin main):
    py verifikasi_klaim_pr.py

Hanya membaca. Alat sekali pakai, TIDAK perlu di-commit. Hasilnya dipakai sebagai dasar komentar review.
"""
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))
RAW = ROOT / "data" / "raw"
hasil = []


def cek(nama, ok, rinci=""):
    hasil.append(ok)
    print(f"[{'COCOK' if ok else 'BEDA '}] {nama}" + (f"  ({rinci})" if rinci else ""))


def norm(df):
    d = df.copy()
    d["k"] = d["wilayah"].str.upper().str.replace("KEPULAUAN", "KEP.", regex=False)
    d["v"] = pd.to_numeric(d["nilai"].astype(str).replace({"-": None, "": None, "nan": None}), errors="coerce")
    return d


def main():
    a = pd.read_csv(RAW / "bps/2026-10-17/sdg4_amh.csv")
    r = pd.read_csv(RAW / "bps/2026-10-17/sdg4_amh_rinci.csv")
    r["wilayah"] = r["wilayah"].replace({"KEPULAUAN BANGKA BELITUNG": "KEP. BANGKA BELITUNG", "KEPULAUAN RIAU": "KEP. RIAU"})
    tot = r[(r.daerah == "Perkotaan + Perdesaan") & (r.jenis_kelamin == "Laki-laki+Perempuan")].dropna(subset=["nilai"])

    print("== PR #9-#13 (bukti unduh data)")
    from src.common import hasil as h
    klaim = "8c82f4533900ceb595082bd6dc49aecb4b06974a9ed00e213a8641b5ac528df9"
    cek("data_hash di PR sama dengan hash MANIFEST.csv", h.data_hash() == klaim)

    print("\n== PR #15 (profil var1458 dan rinci)")
    p = a[a.wilayah == "PAPUA"].set_index("tahun").nilai
    cek("Papua var1458 2023 -> 2024 = 84,22 -> 98,37", (p[2023], p[2024]) == (84.22, 98.37), f"{p[2023]} -> {p[2024]}")
    cek("sel kosong tabel rinci = 645", int(r.nilai.isna().sum()) == 645, str(int(r.nilai.isna().sum())))
    m = a.merge(tot, on=["wilayah", "tahun"], suffixes=("_a", "_r"))
    m["d"] = (m.nilai_r - m.nilai_a).round(2)
    b = m[m.d.abs() > 0.01]
    cek("total rinci vs var1458 berbeda di 32 provinsi (2017)", int((b.wilayah != "INDONESIA").sum()) == 32 and set(b.tahun) == {2017},
        f"{len(b)} sel termasuk Indonesia; tanpa toleransi {int((m.d.abs() > 0).sum())} sel")

    print("\n== PR #16 (profil WDI)")
    w = [o for o in json.load(open(RAW / "wdi/2026-10-20/data/kelompok-03-hal-01.json", encoding="utf-8"))[1] if o["indicator"]["id"] == "SE.ADT.LITR.ZS"]
    wv = {int(o["date"]): o["value"] for o in w if o["value"] is not None}
    nas = a[a.wilayah == "INDONESIA"].set_index("tahun").nilai
    nr = tot[tot.wilayah == "INDONESIA"].set_index("tahun").nilai
    cek("WDI: 13 dari 66 tahun terisi (1980-2020)", len(wv) == 13 and len(w) == 66, f"{len(wv)} dari {len(w)}")
    cek("irisan: 5 tahun dengan var1458, 8 tahun dengan rinci", len(set(wv) & set(nas.index)) == 5 and len(set(wv) & set(nr.index)) == 8)
    beda = {y: round(wv[y] - nr[y], 2) for y in sorted(set(wv) & set(nr.index)) if abs(wv[y] - nr[y]) > 0.005}
    cek("WDI sama dengan BPS kecuali 2010 (selisih sekitar 0,6)", list(beda) == [2010] and abs(beda[2010] + 0.59) < 0.02, str(beda))

    print("\n== PR #17 (grid dan kelengkapan)")
    k = pd.read_csv(ROOT / "reports/profil/kelengkapan_per_seri_tahun.csv")
    sk = pd.read_csv(ROOT / "reports/profil/sel_kosong.csv")
    cek("sel kosong di grid = 686 (n_grid - terisi) dan missing sejati 0", int(k.n_grid.sum() - k.terisi.sum()) == 686 and int(k.missing.sum()) == 0,
        f"missing sejati {int(k.missing.sum())}")
    lubang_var = 38 * a["tahun"].nunique() - int((a["wilayah"] != "INDONESIA").sum())
    cek("686 = 645 sel kosong data mentah rinci + 41 sel var1458 yang tidak ada di data mentah (38 provinsi x 12 tahun - baris provinsi)",
        int(r.nilai.isna().sum()) + lubang_var == 686, f"{int(r.nilai.isna().sum())} + {lubang_var}")
    cek("sel_kosong.csv (tahap 2) menjumlah 645 = sel kosong di data mentah rinci (berbeda ruang lingkup dengan 686 di grid tahap 3)",
        int(sk.n_kosong.sum()) == 645, f"menjumlah {int(sk.n_kosong.sum())}")

    print("\n== PR #18 (kategori anomali)")
    an = pd.read_csv(ROOT / "reports/profil/anomali_kategori.csv").drop_duplicates(["seri", "provinsi", "periode"])
    vc = an.kategori.value_counts().to_dict()
    cek("463 sel anomali: outlier_asli 441, patahan_metode 13, patahan_wilayah 7, revisi_snapshot 2",
        len(an) == 463 and vc.get("outlier_asli") == 441 and vc.get("patahan_metode") == 13 and vc.get("patahan_wilayah") == 7 and vc.get("revisi_snapshot") == 2, str(vc))
    cek("deduplikasi: 394 pasangan sama, 33 revisi dari 427 (toleransi 0,01)", len(m) == 427 and int((m.d.abs() <= 0.01).sum()) == 394, f"{int((m.d.abs() <= 0.01).sum())} sama")

    print("\n== PR #6 (pembaca JSON tabel rinci) vs CSV")
    try:
        import src.ekstraksi as ek
        j = norm(ek.baca_bps_json_rinci())
        c = norm(ek.baca_bps_csv_rinci())
        kunci = ["k", "daerah", "jenis_kelamin", "tahun"]
        dup = int(j.duplicated(kunci).sum())
        x = c.merge(j.drop_duplicates(kunci), on=kunci, how="outer", suffixes=("_c", "_j"), indicator=True)
        bt = x[x._merge == "both"]
        sama = int(((bt.v_c == bt.v_j) | (bt.v_c.isna() & bt.v_j.isna())).sum())
        cek("pembaca JSON rinci identik dengan CSV pada semua sel", len(j) == len(c) and dup == 0 and sama == len(c),
            f"{len(j)} baris JSON vs {len(c)} CSV; kunci kembar {dup}; sel cocok {sama}/{len(c)}; daerah terbaca {sorted(j.daerah.unique())}")
    except Exception as e:
        cek("pembaca JSON rinci", False, repr(e))

    print(f"\nRingkasan: {sum(hasil)} dari {len(hasil)} klaim cocok dengan data.")
    return 0 if all(hasil) else 1


if __name__ == "__main__":
    sys.exit(main())
