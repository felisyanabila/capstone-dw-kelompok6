"""Memeriksa panel Gold (data/gold/) terhadap data mentah, Silver, dan grid tahap 3 lewat jalur terpisah.

Jalankan di folder utama repo SETELAH `py pipeline.py`:
    py verifikasi_panel_gold.py

Hanya membaca. Alat sekali pakai: JANGAN di-commit.
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))
hasil = []


def cek(nama, ok, rinci=""):
    hasil.append(ok)
    print(f"[{'COCOK' if ok else 'BEDA '}] {nama}" + (f"  ({rinci})" if rinci else ""))


def main():
    gold, raw = ROOT / "data" / "gold", ROOT / "data" / "raw" / "bps" / "2026-10-17"
    p = pd.read_parquet(gold / "panel_provinsi.parquet")
    lebar = pd.read_parquet(gold / "panel_lebar.parquet")
    pem = pd.read_parquet(gold / "pemeriksaan_total_rinci_vs_ringkas.parquet")
    silver = pd.read_parquet(ROOT / "data" / "silver" / "silver.parquet")

    print("== laporan bukti dan metrik")
    lap = ROOT / "reports" / "panel_gold.md"
    teks = lap.read_text(encoding="utf-8") if lap.exists() else ""
    cek("reports/panel_gold.md ditulis pipeline: kunci kembar 0 dan 5169 dari 5169 sel terlacak ke berkas mentah",
        "kunci kembar: 0" in teks and "5169 dari 5169 sel terlacak" in teks)
    metrik = teks.split("## 4. Metrik")[-1] if teks else ""
    cek("results/124450121/metrics.json cocok dengan hitungan pipeline (seri_panel, baris_gold, dan metrik Sprint 1)",
        bool(teks) and "BEDA" not in metrik and "tidak ada" not in metrik, "; ".join(b.strip("- ") for b in metrik.splitlines() if "BEDA" in b or "tidak ada" in b)[:300])

    print("\n== bentuk dan kunci")
    cek("panel = 38 provinsi x 17 tahun x 9 indikator", len(p) == 38 * 17 * 9 and p.wilayah_kode.nunique() == 38 and p.periode.nunique() == 17 and p.indikator.nunique() == 9, f"{len(p)} baris")
    cek("kunci (wilayah_kode, periode, indikator) tidak kembar", int(p.duplicated(["wilayah_kode", "periode", "indikator"]).sum()) == 0)
    cek("Indonesia (9999) tidak ada di panel provinsi", not (p.wilayah_kode == 9999).any())
    cek("satu satuan (persen) dan nilai 0-100", p.satuan.nunique() == 1 and p.nilai.dropna().between(0, 100).all(), str(p.satuan.unique().tolist()))
    sc = p.status_sel.value_counts().to_dict()
    cek("status sel: 5169 terisi, 495 belum_ada_wilayah, 99 belum_terbit, 51 tidak_berlaku, 0 missing",
        sc == {"terisi": 5169, "belum_ada_wilayah": 495, "belum_terbit": 99, "tidak_berlaku": 51}, str(sc))

    print("\n== nilai terhadap data mentah (dihitung ulang dari CSV BPS)")
    a = pd.read_csv(raw / "sdg4_amh.csv")
    r = pd.read_csv(raw / "sdg4_amh_rinci.csv")
    nama = {w.upper(): k for k, w in zip(a.wilayah_id, a.wilayah)}
    r["kode"] = r.wilayah.str.upper().str.replace("KEPULAUAN", "KEP.", regex=False).map(nama)
    D = {"Perkotaan + Perdesaan": "", "Perkotaan": "perkotaan", "Perdesaan": "perdesaan"}
    J = {"Laki-laki+Perempuan": "", "Laki-laki": "laki-laki", "Perempuan": "perempuan"}
    r["rin"] = ["_".join(x for x in (D[d], J[j]) if x) or "total" for d, j in zip(r.daerah, r.jenis_kelamin)]
    r = r[(r.kode != 9999) & r.nilai.notna()]
    harap = r[~((r.rin == "total") & (r.tahun >= 2014))][["kode", "tahun", "rin", "nilai"]]
    v = a[a.wilayah_id != 9999][["wilayah_id", "tahun", "nilai"]].rename(columns={"wilayah_id": "kode"})
    v["rin"] = "total"
    harap = pd.concat([harap, v[["kode", "tahun", "rin", "nilai"]]], ignore_index=True)
    isi = p[p.status_sel == "terisi"]
    x = harap.merge(isi, left_on=["kode", "tahun", "rin"], right_on=["wilayah_kode", "tahun", "rincian"], how="outer", suffixes=("_mentah", "_gold"), indicator=True)
    cek("5169 sel terisi sama dengan data mentah (total: var1458 sejak 2014, sisanya tabel rinci)",
        (x["_merge"] == "both").all() and (x.nilai_mentah == x.nilai_gold).all(), f"{int((x['_merge'] == 'both').sum())} sel cocok, {int((x.nilai_mentah != x.nilai_gold).sum())} nilai beda")

    print("\n== jejak ke Silver")
    gb = isi.rename(columns={"seri_kanonik": "seri_kode"}).merge(
        silver, on=["sumber", "seri_kode", "wilayah_kode", "periode", "rincian", "_berkas_raw"], how="left", suffixes=("", "_s"), indicator=True)
    cek("setiap sel terisi kembali ke tepat satu baris Silver", (gb["_merge"] == "both").all() and len(gb) == len(isi), f"{len(gb)} dari {len(isi)} sel")
    cek("nilai dan sidik sumber sama dengan Silver", (gb.nilai == gb.nilai_s).all() and (gb._sha256_raw == gb._sha256_raw_s).all())
    cek("sel kosong tidak membawa jejak palsu", p[p.status_sel != "terisi"][["nilai", "seri_kanonik", "_berkas_raw"]].isna().all().all())

    print("\n== status sel terhadap grid tahap 3 (Gathfan)")
    from src.silver import grid_amh as g
    from src.silver.wilayah import kamus_wilayah
    nk, kn = kamus_wilayah()
    grid = g.bangun_grid(g.baca_pengamatan(nk), sorted(c for c in kn if c != 9999))
    rp = {f"rinci / {d} / {j}": "_".join(x for x in (D[d], J[j]) if x) or "total" for d in D for j in J}
    gr = grid[grid.seri.isin(rp)].assign(rincian=lambda d: d.seri.map(rp))
    y = gr.merge(p[["wilayah_kode", "tahun", "rincian", "status_sel"]], left_on=["wilayah_kode", "periode", "rincian"], right_on=["wilayah_kode", "tahun", "rincian"])
    nt = y[y.rincian != "total"]
    cek("status 8 rincian non-total sama dengan grid tahap 3", len(nt) == 38 * 17 * 8 and (nt.status == nt.status_sel).all(), f"{len(nt)} sel dibandingkan")

    print("\n== panel lebar dan tabel pemeriksaan")
    kolom_indikator = [c for c in lebar.columns if c not in ("wilayah_kode", "nama_wilayah", "periode")]
    cek("panel lebar: 580 baris (provinsi-tahun bernilai), hanya kolom kunci dan 9 indikator amh_, tanpa baris kosong",
        len(lebar) == 580 and len(kolom_indikator) == 9 and all(c.startswith("amh_") for c in kolom_indikator) and not lebar[kolom_indikator].isna().all(axis=1).any(),
        f"{len(lebar)} baris, {len(kolom_indikator)} kolom indikator")
    cek("nilai panel lebar sama dengan panel panjang",
        all(((lebar.set_index(["wilayah_kode", "periode"])[c]).sub(p[p.indikator == c].set_index(["wilayah_kode", "periode"])["nilai"]).dropna().abs().max()) == 0 for c in kolom_indikator))
    sp = pem.status_pemeriksaan.value_counts().to_dict()
    cek("pemeriksaan total: 415 pasangan, 382 sama, 33 berbeda (semuanya 2017), 1 di dalam toleransi 0,01",
        sp == {"sama": 382, "berbeda": 33} and set(pem[pem.status_pemeriksaan == "berbeda"].periode) == {"2017"} and int(pem[pem.status_pemeriksaan == "berbeda"].dalam_toleransi_0_01.sum()) == 1, str(sp))

    print(f"\nRingkasan: {sum(hasil)} dari {len(hasil)} pemeriksaan cocok.")
    return 0 if all(hasil) else 1


if __name__ == "__main__":
    sys.exit(main())
