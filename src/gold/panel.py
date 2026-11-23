"""Tahap 4 - Panel Gold provinsi x periode x indikator dari Silver (seri utama BPS).

Masukan : DataFrame Silver dari src.silver.jalankan().
Keluaran: tiga tabel Parquet di data/gold/
  - panel_provinsi.parquet                      panel panjang: satu baris = satu sel (provinsi, periode, indikator)
  - panel_lebar.parquet                         panel lebar: satu baris = (provinsi, periode), satu kolom per indikator
  - pemeriksaan_total_rinci_vs_ringkas.parquet  total tabel rinci vs var1458 per provinsi dan tahun

Aturan (log-keputusan.csv):
- Indikator = angka melek aksara menurut rincian: amh_<rincian>, sembilan indikator (K-015).
- Grid lengkap 38 provinsi x tahun x indikator; sel kosong tetap menjadi baris dengan status_sel dari aturan K-004,
  tidak diimputasi. Indonesia (9999) tidak ikut panel provinsi (K-005).
- Nilai total: var1458 untuk 2014-2025, tabel rinci untuk 2009-2013 (K-003); semua rincian lain dari tabel rinci.
  Nilai seri lain pada sel yang sama disimpan di nilai_alternatif; tidak dibuang atau dirata-ratakan (K-008).
- Nilai tidak diubah: tanpa konversi satuan, normalisasi, atau transformasi. kategori_anomali ikut apa adanya (K-006).
- Setiap sel terisi membawa kunci Silver asalnya (sumber, seri_kode, wilayah_kode, periode, rincian, _berkas_raw);
  jalankan() memeriksa bahwa semuanya cocok kembali ke Silver.
"""
from pathlib import Path

import pandas as pd

from src.silver.wilayah import INDONESIA, kamus_wilayah

ROOT = Path(__file__).resolve().parents[2]
GOLD = ROOT / "data" / "gold"
RINCI, RINGKAS = "tabel:sdg4_amh_rinci", "var1458"
TAHUN_RINGKAS = "2014"          # var1458 menjadi sumber kanonik total sejak 2014 (K-003)
URUTAN_RINCIAN = ["total", "perkotaan", "perdesaan", "laki-laki", "perempuan",
                  "perkotaan_laki-laki", "perkotaan_perempuan", "perdesaan_laki-laki", "perdesaan_perempuan"]
STATUS = ["terisi", "belum_ada_wilayah", "belum_terbit", "tidak_berlaku", "missing"]
KUNCI_PANEL = ["wilayah_kode", "periode", "indikator"]
KUNCI_SILVER = ["sumber", "seri_kode", "wilayah_kode", "periode", "rincian", "_berkas_raw"]


def _seri_utama(silver: pd.DataFrame) -> pd.DataFrame:
    """Baris Silver untuk panel: dua seri BPS, tanpa baris Indonesia; satu satuan."""
    s = silver[(silver["sumber"] == "bps") & (silver["wilayah_kode"] != INDONESIA)]
    assert set(s["seri_kode"]) == {RINCI, RINGKAS}, f"seri utama tidak seperti dugaan: {sorted(set(s['seri_kode']))}"
    assert s["satuan"].nunique() == 1, f"satuan berbeda dalam satu kolom nilai: {sorted(s['satuan'].unique())}"
    assert set(s["rincian"]) == set(URUTAN_RINCIAN), f"rincian baru di Silver: {sorted(set(s['rincian']) - set(URUTAN_RINCIAN))}"
    return s


def _kanonik(s: pd.DataFrame) -> pd.DataFrame:
    rinci, ringkas = s[s["seri_kode"] == RINCI], s[s["seri_kode"] == RINGKAS]
    total_rinci = rinci[(rinci["rincian"] == "total") & (rinci["periode"] < TAHUN_RINGKAS)]
    total_ringkas = ringkas[ringkas["periode"] >= TAHUN_RINGKAS]
    rincian_lain = rinci[rinci["rincian"] != "total"]
    return pd.concat([total_ringkas, total_rinci, rincian_lain], ignore_index=True)


def panel_provinsi(silver: pd.DataFrame) -> pd.DataFrame:
    from src.silver.grid_amh import status_sel          # aturan status sel tahap 3 (K-004), dipakai apa adanya
    s = _seri_utama(silver)
    k = _kanonik(s)
    _, kode_nama = kamus_wilayah()
    provinsi = sorted(c for c in kode_nama if c != INDONESIA)
    tahun = list(range(int(s["periode"].min()), int(s["periode"].max()) + 1))
    peta = s[["rincian", "daerah", "jenis_kelamin"]].drop_duplicates()
    assert peta["rincian"].is_unique, "satu rincian punya dua pasang daerah dan jenis kelamin"
    peta = peta.set_index("rincian")

    isi = k.assign(_tahun=k["periode"].astype(int)).groupby(["wilayah_kode", "rincian"])["_tahun"].apply(set).to_dict()
    grid = pd.MultiIndex.from_product([provinsi, tahun, URUTAN_RINCIAN],
                                      names=["wilayah_kode", "tahun", "rincian"]).to_frame(index=False)
    grid["periode"] = grid["tahun"].astype(str)
    grid["status_sel"] = [status_sel(isi.get((w, r), set()), w, t)
                          for w, t, r in zip(grid["wilayah_kode"], grid["tahun"], grid["rincian"])]

    nilai = k[["wilayah_kode", "periode", "rincian", "seri_kode", "nilai", "kategori_anomali", "_berkas_raw", "_sha256_raw"]]
    p = grid.merge(nilai, on=["wilayah_kode", "periode", "rincian"], how="left", validate="one_to_one")
    p = p.rename(columns={"seri_kode": "seri_kanonik"})

    alt = s[(s["seri_kode"] == RINCI) & (s["rincian"] == "total") & (s["periode"] >= TAHUN_RINGKAS)]
    alt = alt[["wilayah_kode", "periode", "rincian", "nilai"]].rename(columns={"nilai": "nilai_alternatif"})
    p = p.merge(alt, on=["wilayah_kode", "periode", "rincian"], how="left", validate="one_to_one")
    p["seri_alternatif"] = p["nilai_alternatif"].notna().map({True: RINCI, False: None})

    p["sumber"], p["satuan"], p["kode_sdg"] = "bps", s["satuan"].iloc[0], s["kode_sdg"].iloc[0]
    p["nama_wilayah"] = p["wilayah_kode"].map(kode_nama)
    p["indikator"] = "amh_" + p["rincian"]
    p["daerah"], p["jenis_kelamin"] = p["rincian"].map(peta["daerah"]), p["rincian"].map(peta["jenis_kelamin"])
    urut = {r: i for i, r in enumerate(URUTAN_RINCIAN)}
    p = p.sort_values(["wilayah_kode", "tahun", "rincian"], key=lambda c: c.map(urut) if c.name == "rincian" else c)
    kolom = ["wilayah_kode", "nama_wilayah", "periode", "tahun", "indikator", "rincian", "daerah", "jenis_kelamin",
             "nilai", "satuan", "status_sel", "kode_sdg", "kategori_anomali", "nilai_alternatif", "seri_alternatif",
             "sumber", "seri_kanonik", "_berkas_raw", "_sha256_raw"]
    return p[kolom].reset_index(drop=True)


def panel_lebar(panel: pd.DataFrame) -> pd.DataFrame:
    w = panel.pivot(index=["wilayah_kode", "nama_wilayah", "periode", "tahun"], columns="indikator", values="nilai")
    w = w[["amh_" + r for r in URUTAN_RINCIAN]].reset_index()
    w.columns.name = None
    return w


def pemeriksaan_total(silver: pd.DataFrame) -> pd.DataFrame:
    """Total tabel rinci vs var1458 pada provinsi dan tahun yang sama (2014-2025). Selisih dilaporkan, tidak disamakan."""
    s = _seri_utama(silver)
    a = s[s["seri_kode"] == RINGKAS][["wilayah_kode", "nama_wilayah", "periode", "nilai", "_berkas_raw", "_sha256_raw"]]
    a.columns = ["wilayah_kode", "nama_wilayah", "periode", "nilai_var1458", "_berkas_raw_var1458", "_sha256_raw_var1458"]
    b = s[(s["seri_kode"] == RINCI) & (s["rincian"] == "total") & (s["periode"] >= TAHUN_RINGKAS)]
    b = b[["wilayah_kode", "periode", "nilai", "_berkas_raw", "_sha256_raw"]]
    b.columns = ["wilayah_kode", "periode", "nilai_rinci_total", "_berkas_raw_rinci", "_sha256_raw_rinci"]
    m = a.merge(b, on=["wilayah_kode", "periode"], how="outer", validate="one_to_one")
    m["selisih"] = (m["nilai_rinci_total"] - m["nilai_var1458"]).round(2)
    m["status_pemeriksaan"] = "berbeda"
    m.loc[m["selisih"].abs() < 1e-9, "status_pemeriksaan"] = "sama"
    m.loc[m["nilai_rinci_total"].isna(), "status_pemeriksaan"] = "hanya_var1458"
    m.loc[m["nilai_var1458"].isna(), "status_pemeriksaan"] = "hanya_rinci"
    m["dalam_toleransi_0_01"] = m["selisih"].abs() <= 0.01 + 1e-9
    return m.sort_values(["wilayah_kode", "periode"]).reset_index(drop=True)


def periksa(silver: pd.DataFrame, panel: pd.DataFrame, lebar: pd.DataFrame) -> dict:
    """Pemeriksaan yang menghentikan pipeline bila gagal; mengembalikan angka ringkasan."""
    dup = int(panel.duplicated(KUNCI_PANEL).sum())
    assert dup == 0, f"{dup} kunci panel (provinsi, periode, indikator) kembar"
    assert panel["satuan"].nunique() == 1 and panel["nilai"].dropna().between(0, 100).all(), "satuan atau rentang nilai salah"
    assert set(panel["status_sel"]) <= set(STATUS) and not (panel["status_sel"] == "missing").any(), "ada sel missing sejati"
    assert (panel["nilai"].notna() == (panel["status_sel"] == "terisi")).all(), "status_sel tidak sejalan dengan nilai"
    assert len(lebar) == panel[["wilayah_kode", "periode"]].drop_duplicates().shape[0], "panel lebar tidak sejalan dengan panel panjang"
    # jejak: setiap sel terisi kembali ke tepat satu baris Silver dengan nilai, sidik, dan tanda anomali yang sama
    isi = panel[panel["status_sel"] == "terisi"].rename(columns={"seri_kanonik": "seri_kode"})
    gabung = isi.merge(silver, on=KUNCI_SILVER, how="left", suffixes=("", "_silver"), validate="one_to_one", indicator=True)
    assert (gabung["_merge"] == "both").all(), "ada sel Gold yang tidak ditemukan di Silver"
    assert (gabung["nilai"] == gabung["nilai_silver"]).all() and (gabung["_sha256_raw"] == gabung["_sha256_raw_silver"]).all(), \
        "nilai atau sidik Gold berbeda dari Silver"
    assert ((gabung["kategori_anomali"] == gabung["kategori_anomali_silver"]) |
            (gabung["kategori_anomali"].isna() & gabung["kategori_anomali_silver"].isna())).all(), "tanda anomali berbeda dari Silver"
    return {"sel_terisi_terlacak": len(gabung)}


def ringkasan(panel: pd.DataFrame, lebar: pd.DataFrame, pemeriksaan: pd.DataFrame) -> dict:
    sc = panel["status_sel"].value_counts()
    return {"seri_panel": int(panel["seri_kanonik"].nunique()), "indikator_panel": int(panel["indikator"].nunique()),
            "baris_gold": len(panel), "baris_panel_lebar": len(lebar), "baris_pemeriksaan_total": len(pemeriksaan),
            **{f"sel_{k}": int(sc.get(k, 0)) for k in STATUS},
            "sel_ditandai_anomali": int(panel["kategori_anomali"].notna().sum()),
            "total_berbeda": int((pemeriksaan["status_pemeriksaan"] == "berbeda").sum())}


def tulis(tabel: dict, folder: Path = GOLD) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    for nama, df in tabel.items():
        df.to_parquet(folder / f"{nama}.parquet", index=False)


def jalankan(silver: pd.DataFrame) -> dict:
    panel = panel_provinsi(silver)
    lebar = panel_lebar(panel)
    pem = pemeriksaan_total(silver)
    periksa(silver, panel, lebar)
    tabel = {"panel_provinsi": panel, "panel_lebar": lebar, "pemeriksaan_total_rinci_vs_ringkas": pem}
    tulis(tabel)
    r = ringkasan(panel, lebar, pem)
    print(f"Gold: panel {r['baris_gold']} baris ({r['sel_terisi']} terisi, {r['sel_belum_ada_wilayah']} belum ada wilayah, "
          f"{r['sel_belum_terbit']} belum terbit, {r['sel_tidak_berlaku']} tidak berlaku, {r['sel_missing']} missing), "
          f"panel lebar {r['baris_panel_lebar']}, pemeriksaan total {r['baris_pemeriksaan_total']} -> {GOLD.relative_to(ROOT)}/")
    return tabel
