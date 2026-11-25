"""Tahap 4 - Panel Gold provinsi x periode x indikator dari Silver (seri utama BPS).

Masukan : DataFrame Silver dari src.silver.jalankan().
Keluaran: tiga tabel Parquet di data/gold/
  - panel_provinsi.parquet                      panel panjang: satu baris = satu sel (provinsi, periode, indikator)
  - panel_lebar.parquet                         panel lebar: satu baris = (provinsi, periode), satu kolom per indikator
  - pemeriksaan_total_rinci_vs_ringkas.parquet  total tabel rinci vs var1458 per provinsi dan tahun
  - reports/panel_gold.md                       laporan bukti: hasil pipeline, keunikan kunci, keterlacakan, metrik

Menelusuri satu sel sampai baris berkas mentah:  py -m src.gold.panel --telusuri 9400 2024 amh_total

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
import csv
import json
import sys
from functools import lru_cache
from pathlib import Path

import pandas as pd

from src.silver.wilayah import INDONESIA, kamus_wilayah

ROOT = Path(__file__).resolve().parents[2]
GOLD = ROOT / "data" / "gold"
LAPORAN = ROOT / "reports" / "panel_gold.md"
NIM_PEMILIK = "124450121"
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


@lru_cache(maxsize=None)
def _mentah(berkas: str) -> pd.DataFrame:
    """CSV mentah BPS dengan kunci panel dan nomor baris berkas (baris 1 = header). Dibaca langsung, tidak lewat ekstraksi."""
    from src.common.manifest import RAW
    from src.silver.bangun import DAERAH, JENIS_KELAMIN, rincian
    from src.silver.wilayah import kamus_wilayah as kamus, kode_dari_nama
    d = pd.read_csv(RAW / berkas)
    d["baris_berkas"] = d.index + 2
    if "wilayah_id" in d.columns:                                  # var1458
        d["wilayah_kode"], d["rincian"] = d["wilayah_id"].astype("int64"), "total"
    else:                                                          # tabel rinci
        nama_kode, _ = kamus()
        peta = {n: kode_dari_nama(n, nama_kode) for n in d["wilayah"].unique()}
        d["wilayah_kode"] = d["wilayah"].map(peta).astype("int64")
        d["rincian"] = [rincian(DAERAH[a], JENIS_KELAMIN[b]) for a, b in zip(d["daerah"], d["jenis_kelamin"])]
    d["periode"] = d["tahun"].astype(str)
    return d


def audit_jejak(silver: pd.DataFrame, panel: pd.DataFrame) -> dict:
    """Setiap sel terisi -> satu baris Silver (sudah diperiksa di periksa()) -> satu baris berkas mentah dengan nilai sama."""
    from src.common import manifest
    isi = panel[panel["status_sel"] == "terisi"]
    terlacak, nilai_beda, per_berkas = 0, 0, {}
    sidik_cocok = True
    daftar = manifest.baca()
    for berkas, g in isi.groupby("_berkas_raw"):
        m = g.merge(_mentah(berkas), on=["wilayah_kode", "periode", "rincian"], how="left", suffixes=("", "_mentah"),
                    validate="one_to_one", indicator=True)
        assert (m["_merge"] == "both").all(), f"sel Gold tanpa baris di {berkas}"
        terlacak += len(m)
        nilai_beda += int((m["nilai"] != m["nilai_mentah"]).sum())
        per_berkas[berkas] = len(m)
        hitung = manifest.sha256(manifest.RAW / berkas)
        sidik_cocok &= (hitung == daftar[berkas]) and bool((g["_sha256_raw"] == hitung).all())
    assert nilai_beda == 0, f"{nilai_beda} nilai Gold berbeda dari berkas mentah"
    assert sidik_cocok, "sidik sha256 berkas mentah tidak sama dengan MANIFEST.csv atau kolom _sha256_raw"
    return {"sel_terisi": len(isi), "sel_terlacak_mentah": terlacak, "nilai_beda": nilai_beda,
            "per_berkas": per_berkas, "sidik_cocok": bool(sidik_cocok)}


def telusuri(panel: pd.DataFrame, silver: pd.DataFrame, wilayah_kode: int, periode, indikator: str) -> dict:
    """Rantai jejak satu sel: Gold -> Silver -> baris berkas mentah (dengan nomor baris dan sha256)."""
    from src.common import manifest
    g = panel[(panel["wilayah_kode"] == int(wilayah_kode)) & (panel["periode"] == str(periode)) & (panel["indikator"] == indikator)]
    if len(g) != 1:
        raise KeyError(f"sel ({wilayah_kode}, {periode}, {indikator}) tidak ada di panel")
    g = g.iloc[0]
    hasil = {"gold": {k: (None if pd.isna(v) else v) for k, v in g.items() if k not in ("_sha256_raw",)}}
    if g["status_sel"] != "terisi":
        hasil["catatan"] = f"sel kosong ({g['status_sel']}): tidak ada baris Silver maupun baris berkas mentah untuk sel ini"
        return hasil
    sv = silver[(silver["sumber"] == g["sumber"]) & (silver["seri_kode"] == g["seri_kanonik"]) & (silver["wilayah_kode"] == g["wilayah_kode"])
                & (silver["periode"] == g["periode"]) & (silver["rincian"] == g["rincian"]) & (silver["_berkas_raw"] == g["_berkas_raw"])]
    assert len(sv) == 1, f"{len(sv)} baris Silver untuk satu sel Gold"
    sv = sv.iloc[0]
    mt = _mentah(g["_berkas_raw"])
    mt = mt[(mt["wilayah_kode"] == g["wilayah_kode"]) & (mt["periode"] == g["periode"]) & (mt["rincian"] == g["rincian"])]
    assert len(mt) == 1, f"{len(mt)} baris mentah untuk satu sel Gold"
    mt = mt.iloc[0]
    hasil["silver"] = {k: (None if pd.isna(v) else v) for k, v in sv.items()}
    hasil["mentah"] = {"berkas": g["_berkas_raw"], "baris_berkas": int(mt["baris_berkas"]),
                       "isi": {k: (None if pd.isna(v) else v) for k, v in mt.items() if k not in ("wilayah_kode", "rincian", "periode", "baris_berkas")},
                       "sha256_dihitung": manifest.sha256(manifest.RAW / g["_berkas_raw"]), "sha256_manifest": manifest.baca()[g["_berkas_raw"]]}
    hasil["catatan"] = "nilai Gold = nilai Silver = nilai berkas mentah" if g["nilai"] == sv["nilai"] == mt["nilai"] else "NILAI TIDAK SAMA"
    return hasil


def _teks_jejak(h: dict) -> list:
    g = h["gold"]
    baris = [f"Gold    : wilayah {g['wilayah_kode']} ({g['nama_wilayah']}), periode {g['periode']}, indikator {g['indikator']}: nilai {g['nilai']} {g['satuan']}, status {g['status_sel']}"
             + (f", kategori_anomali {g['kategori_anomali']}" if g.get("kategori_anomali") else "")
             + (f", nilai_alternatif {g['nilai_alternatif']} ({g['seri_alternatif']})" if g.get("nilai_alternatif") is not None else "")]
    if "silver" in h:
        s, m = h["silver"], h["mentah"]
        baris += [f"Silver  : {s['sumber']} / {s['seri_kode']} / wilayah {s['wilayah_kode']} / {s['periode']} / {s['rincian']} / {s['_berkas_raw']}: nilai {s['nilai']}",
                  f"Mentah  : {m['berkas']}, baris {m['baris_berkas']}: nilai {m['isi'].get('nilai')}",
                  f"sha256  : {m['sha256_dihitung']} (dihitung ulang), sama dengan MANIFEST.csv: {m['sha256_dihitung'] == m['sha256_manifest']}"]
    baris.append(f"Hasil   : {h['catatan']}")
    return baris


def _contoh(panel: pd.DataFrame, silver: pd.DataFrame) -> list:
    """Enam sel contoh yang dipilih tetap: awal deret, hasil pilihan var1458 vs tabel rinci, bertanda anomali, rincian, dan dua jenis sel kosong."""
    daftar = [(1100, 2009, "amh_total"), (1100, 2017, "amh_total"), (9400, 2024, "amh_total"),
              (3100, 2025, "amh_perkotaan_perempuan"), (9200, 2023, "amh_total"), (3100, 2020, "amh_perdesaan")]
    return [telusuri(panel, silver, *k) for k in daftar]


def metrik_dihitung(silver: pd.DataFrame, panel: pd.DataFrame, log: Path = ROOT / "log-keputusan.csv") -> dict:
    d = {"seri_silver": int(silver["seri_kode"].nunique()), "rincian_dienkode": int(silver["rincian"].nunique()),
         "baris_silver": int(len(silver)), "seri_panel": int(panel["seri_kanonik"].nunique()), "baris_gold": int(len(panel))}
    if log.exists():
        with open(log, encoding="utf-8-sig", newline="") as f:
            d["keputusan_dicatat"] = sum(1 for r in csv.DictReader(f) if r.get("nim") == NIM_PEMILIK)
    return d


def tulis_laporan(silver, panel, lebar, pem, audit, jalur: Path = LAPORAN) -> Path:
    r = ringkasan(panel, lebar, pem)
    kunci = panel[KUNCI_PANEL].drop_duplicates()
    hitung = metrik_dihitung(silver, panel)
    berkas_metrik = ROOT / "results" / NIM_PEMILIK / "metrics.json"
    ada = json.loads(berkas_metrik.read_text(encoding="utf-8")).get("metrik", {}) if berkas_metrik.exists() else None
    L = ["# Laporan panel Gold provinsi x periode x indikator (Tahap 4)", "",
         "Dibuat otomatis oleh `python pipeline.py` (`src/gold/panel.py`); tidak ada langkah tangan. Isinya sengaja tanpa waktu dan nomor commit supaya sama setiap kali pipeline dijalankan.", "",
         "## 1. Hasil pipeline", "",
         f"- `data/gold/panel_provinsi.parquet`: {r['baris_gold']} baris = 38 provinsi x 17 tahun (2009-2025) x {r['indikator_panel']} indikator (`amh_<rincian>`).",
         f"- `data/gold/panel_lebar.parquet`: {r['baris_panel_lebar']} baris (provinsi x tahun, satu kolom nilai per indikator).",
         f"- `data/gold/pemeriksaan_total_rinci_vs_ringkas.parquet`: {r['baris_pemeriksaan_total']} pasangan provinsi-tahun; "
         f"{int((pem['status_pemeriksaan'] == 'sama').sum())} sama, {r['total_berbeda']} berbeda (periode: {', '.join(sorted(pem[pem['status_pemeriksaan'] == 'berbeda']['periode'].unique()))}), "
         f"{int(pem[pem['status_pemeriksaan'] == 'berbeda']['dalam_toleransi_0_01'].sum())} di antaranya dalam toleransi 0,01.",
         f"- Status sel: {r['sel_terisi']} terisi, {r['sel_belum_ada_wilayah']} belum_ada_wilayah, {r['sel_belum_terbit']} belum_terbit, {r['sel_tidak_berlaku']} tidak_berlaku, {r['sel_missing']} missing (aturan K-004).",
         f"- Satuan: {panel['satuan'].iloc[0]} untuk seluruh kolom `nilai`; nilai tidak diubah; rentang {panel['nilai'].min():.2f} sampai {panel['nilai'].max():.2f}.",
         f"- Nilai total: var1458 untuk 2014-2025, tabel rinci untuk 2009-2013 (K-003); {int(panel['nilai_alternatif'].notna().sum())} nilai tabel rinci pada sel yang sama disimpan di `nilai_alternatif`.",
         f"- {r['sel_ditandai_anomali']} sel membawa `kategori_anomali` dari Silver (K-006); tidak ada sel yang disaring.", "",
         "## 2. Keunikan kunci", "",
         f"- Kunci panel: `{', '.join(KUNCI_PANEL)}`.",
         f"- Baris: {len(panel)}; kombinasi kunci unik: {len(kunci)}; kunci kembar: {len(panel) - len(kunci)}.",
         "- Pemeriksaan ini dijalankan di dalam pipeline (`periksa()`); bila ada kunci kembar, pipeline berhenti.", "",
         "## 3. Keterlacakan baris", "",
         f"- {audit['sel_terisi']} sel terisi -> tepat satu baris Silver (kunci: {', '.join(KUNCI_SILVER)}): nilai, sidik sumber, dan tanda anomali sama.",
         f"- {audit['sel_terlacak_mentah']} dari {audit['sel_terisi']} sel terlacak lebih jauh ke satu baris berkas mentah dengan nilai sama (selisih nilai: {audit['nilai_beda']}):"]
    L += [f"  - `{b}`: {n} sel" for b, n in audit["per_berkas"].items()]
    L += [f"- sha256 setiap berkas mentah dihitung ulang dan sama dengan `data/raw/MANIFEST.csv` dan kolom `_sha256_raw`: {'ya' if audit['sidik_cocok'] else 'TIDAK'}.",
          f"- {len(panel) - r['sel_terisi']} sel kosong tidak punya baris Silver (memang tidak ada nilai di sumber); statusnya menjelaskan alasannya.", "",
          "Contoh penelusuran (sel dipilih tetap):", ""]
    for h in _contoh(panel, silver):
        L += ["```"] + _teks_jejak(h) + ["```", ""]
    L += ["Menelusuri sel mana pun: `py -m src.gold.panel --telusuri <wilayah_kode> <periode> <indikator>`, misalnya `py -m src.gold.panel --telusuri 9400 2024 amh_total`.", "",
          "## 4. Metrik", "",
          "Dihitung pipeline dibandingkan dengan `results/" + NIM_PEMILIK + "/metrics.json`:", ""]
    for k, v in hitung.items():
        if ada is None:
            L.append(f"- `{k}`: dihitung {v}; metrics.json belum ada")
        else:
            L.append(f"- `{k}`: dihitung {v}; di metrics.json {ada.get(k, 'tidak ada')} ({'cocok' if ada.get(k) == v else 'BEDA'})")
    L += ["", "Perintah menulis ulang metrics (satu baris, memuat metrik Sprint 1 dan Sprint 2):", "",
          "```", "py -m src.common.hasil " + NIM_PEMILIK + " " + " ".join(f"{k}={v}" for k, v in hitung.items()), "```", ""]
    jalur.parent.mkdir(parents=True, exist_ok=True)
    jalur.write_text("\n".join(L), encoding="utf-8")
    return jalur


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 4 or argv[0] != "--telusuri":
        print("Pemakaian: py -m src.gold.panel --telusuri <wilayah_kode> <periode> <indikator>\n"
              "Contoh   : py -m src.gold.panel --telusuri 9400 2024 amh_total   (jalankan python pipeline.py dulu)")
        return 2
    panel = pd.read_parquet(GOLD / "panel_provinsi.parquet")
    silver = pd.read_parquet(ROOT / "data" / "silver" / "silver.parquet")
    try:
        print("\n".join(_teks_jejak(telusuri(panel, silver, int(argv[1]), argv[2], argv[3]))))
    except (KeyError, ValueError) as e:
        print(f"Tidak dapat menelusuri: {e}. Periksa wilayah_kode (angka), periode (mis. 2024), dan indikator (mis. amh_total).")
        return 1
    return 0


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
    audit = audit_jejak(silver, panel)
    tulis_laporan(silver, panel, lebar, pem, audit)
    r = ringkasan(panel, lebar, pem)
    print(f"Gold: panel {r['baris_gold']} baris ({r['sel_terisi']} terisi, {r['sel_belum_ada_wilayah']} belum ada wilayah, "
          f"{r['sel_belum_terbit']} belum terbit, {r['sel_tidak_berlaku']} tidak berlaku, {r['sel_missing']} missing), "
          f"panel lebar {r['baris_panel_lebar']}, pemeriksaan total {r['baris_pemeriksaan_total']}; jejak ke berkas mentah "
          f"{audit['sel_terlacak_mentah']}/{audit['sel_terisi']} -> {GOLD.relative_to(ROOT)}/, {LAPORAN.relative_to(ROOT)}")
    return tabel


if __name__ == "__main__":
    sys.exit(main())
