"""Tahap 4: menyusun Silver dari hasil ekstraksi (satu baris = satu angka yang punya nilai).

Masukan : kamus hasil src.ekstraksi.jalankan().
Keluaran: DataFrame Silver (11 kolom wajib + 4 kolom tambahan), ditulis ke data/silver/silver.parquet.

Aturan yang dipakai (panduan umum bagian 5.1 dan log-keputusan.csv):
- Berkas sumber tiap baris: CSV pratampil BPS dan JSON WDI. JSON BPS hanya uji silang, tidak masuk Silver.
- Baris tanpa nilai tidak disimpan; sel kosong dihitung di grid (K-004), tidak diimputasi.
- Wilayah: kode BPS x 100 lewat kamus var1458 (K-001, K-002); Indonesia = 9999.
- Satuan dan kode SDG dari katalog.py (K-009 s.d. K-014); periode tahunan, tidak ada agregasi.
- Rincian tabel rinci disimpan apa adanya sebagai kolom rincian, daerah, dan jenis_kelamin.
  Memilih rincian yang sebanding adalah urusan Gold.
- Angka tidak diubah. Kategori calon anomali (K-006) hanya ditempel sebagai kolom kategori_anomali.
- Dua angka berbeda untuk sel yang sama (var1458 vs total rinci, 2017) sama-sama disimpan;
  kunci Silver memuat _berkas_raw (K-008).
"""
from pathlib import Path

import pandas as pd

from src.silver.katalog import KATALOG
from src.silver.wilayah import INDONESIA, kamus_wilayah, kode_dari_nama

ROOT = Path(__file__).resolve().parents[2]
JALUR = ROOT / "data" / "silver" / "silver.parquet"

WAJIB = ["sumber", "seri_kode", "wilayah_kode", "nama_wilayah", "periode", "jenis_periode",
         "rincian", "nilai", "satuan", "_berkas_raw", "_sha256_raw"]
TAMBAHAN = ["kode_sdg", "daerah", "jenis_kelamin", "kategori_anomali"]
KOLOM = WAJIB + TAMBAHAN
KUNCI = ["sumber", "seri_kode", "wilayah_kode", "periode", "rincian", "_berkas_raw"]

DAERAH = {"Perkotaan + Perdesaan": "semua", "Perkotaan": "perkotaan", "Perdesaan": "perdesaan"}
JENIS_KELAMIN = {"Laki-laki+Perempuan": "semua", "Laki-laki": "laki-laki", "Perempuan": "perempuan"}
SERI_RINCI = "tabel:sdg4_amh_rinci"


def rincian(daerah: str, jenis_kelamin: str) -> str:
    """'semua' dibuang; sisanya digabung dengan garis bawah. Dua 'semua' = total."""
    bagian = [x for x in (daerah, jenis_kelamin) if x != "semua"]
    return "_".join(bagian) or "total"


def _lengkapi(df: pd.DataFrame, sumber: str, seri: str) -> pd.DataFrame:
    k = KATALOG[(sumber, seri)]
    df = df.copy()
    df["sumber"], df["seri_kode"] = sumber, seri
    df["jenis_periode"], df["satuan"], df["kode_sdg"] = k["jenis_periode"], k["satuan"], k["kode_sdg"]
    return df


def _var1458(mentah: pd.DataFrame, kode_nama: dict) -> pd.DataFrame:
    a = mentah
    assert (a["var_id"] == 1458).all(), "var_id selain 1458 di sdg4_amh.csv"
    assert (a["periode"] == "Tahun").all(), "ada periode non-tahunan di var1458; Silver tidak boleh meratakannya"
    assert a["nilai"].notna().all(), "var1458 tidak punya sel kosong (K-003); ada yang berubah di sumber?"
    assert set(a["satuan"].str.lower()) == {KATALOG[("bps", "var1458")]["satuan"]}, "satuan sumber tidak cocok dengan katalog"
    d = pd.DataFrame({
        "wilayah_kode": a["wilayah_id"].astype("int64"), "periode": a["tahun"].astype(str),
        "rincian": "total", "daerah": "semua", "jenis_kelamin": "semua", "nilai": a["nilai"].astype("float64"),
        "_berkas_raw": a["_berkas_raw"], "_sha256_raw": a["_sha256_raw"], "_seri_label": "var1458"})
    return _lengkapi(d, "bps", "var1458")


def _rinci(mentah: pd.DataFrame, nama_kode: dict) -> pd.DataFrame:
    r = mentah
    assert r["cek"].isna().all(), "kolom cek berisi nilai; perlu keputusan baru sebelum dibuang"
    r = r[r["nilai"].notna()]                       # sel kosong ('-' di HTML) tidak masuk Silver
    daerah, jk = r["daerah"].map(DAERAH), r["jenis_kelamin"].map(JENIS_KELAMIN)
    assert daerah.notna().all() and jk.notna().all(), "label daerah atau jenis kelamin baru di tabel rinci"
    d = pd.DataFrame({
        "wilayah_kode": r["wilayah"].map(lambda n: kode_dari_nama(n, nama_kode)).astype("int64"),
        "periode": r["tahun"].astype(str), "rincian": [rincian(a, b) for a, b in zip(daerah, jk)],
        "daerah": daerah.values, "jenis_kelamin": jk.values, "nilai": r["nilai"].astype("float64"),
        "_berkas_raw": r["_berkas_raw"], "_sha256_raw": r["_sha256_raw"],
        "_seri_label": "rinci / " + r["daerah"] + " / " + r["jenis_kelamin"]})
    return _lengkapi(d, "bps", SERI_RINCI)


def _wdi(mentah: pd.DataFrame) -> pd.DataFrame:
    w = mentah
    assert (w["indicator.id"] == "SE.ADT.LITR.ZS").all() and (w["countryiso3code"] == "IDN").all()
    assert w["date"].str.fullmatch(r"\d{4}").all(), "WDI memuat periode non-tahunan"
    w = w[w["value"].notna()]
    d = pd.DataFrame({
        "wilayah_kode": INDONESIA, "periode": w["date"], "rincian": "total", "daerah": "semua",
        "jenis_kelamin": "semua", "nilai": w["value"].astype("float64"),
        "_berkas_raw": w["_berkas_raw"], "_sha256_raw": w["_sha256_raw"], "_seri_label": "wdi"})
    return _lengkapi(d, "wdi", "SE.ADT.LITR.ZS")


def kategori_anomali() -> dict:
    """{(label seri, kode, periode): kategori} dari aturan K-006, memakai fungsi tahap 3 apa adanya."""
    from src.silver import anomali_amh as an, grid_amh as g, profil_amh as p
    nama_kode, kode_nama = kamus_wilayah()
    obs = g.baca_pengamatan(nama_kode)
    pat, galat = an.patahan_serentak(obs), an.galat_input(obs)
    dedup = an.deduplikasi(g.bandingkan_total(obs)["tabel"])
    kat = an.kategorikan(p.calon_anomali(p.baca_data()), obs, kode_nama, nama_kode, pat, galat, dedup)
    sel = kat.drop_duplicates(["seri", "kode", "periode"])
    return {(s, int(k), int(t)): c for s, k, t, c in zip(sel["seri"], sel["kode"], sel["periode"], sel["kategori"])}


def susun(mentah: dict) -> pd.DataFrame:
    nama_kode, kode_nama = kamus_wilayah()
    bagian = [_var1458(mentah["bps_sdg4_amh_csv"], kode_nama),
              _rinci(mentah["bps_sdg4_amh_rinci_csv"], nama_kode),
              _wdi(mentah["wdi_data"])]
    s = pd.concat(bagian, ignore_index=True)
    tak_dikenal = sorted(set(s["wilayah_kode"]) - set(kode_nama))
    assert not tak_dikenal, f"kode wilayah di luar kamus var1458: {tak_dikenal}"
    s["nama_wilayah"] = s["wilayah_kode"].map(kode_nama)
    flag = kategori_anomali()
    s["kategori_anomali"] = [flag.get((a, k, int(t))) if sm == "bps" else None
                             for a, k, t, sm in zip(s["_seri_label"], s["wilayah_kode"], s["periode"], s["sumber"])]
    s = s[KOLOM].sort_values(KUNCI).reset_index(drop=True)
    kembar = int(s.duplicated(KUNCI).sum())
    assert kembar == 0, f"{kembar} kunci Silver kembar"
    return s


def ringkasan(s: pd.DataFrame) -> dict:
    return {"baris_silver": len(s), "seri_silver": s["seri_kode"].nunique(),
            "rincian_dienkode": s["rincian"].nunique(), "berkas_sumber": s["_berkas_raw"].nunique(),
            "baris_ditandai_anomali": int(s["kategori_anomali"].notna().sum())}


def tulis(s: pd.DataFrame, jalur: Path = JALUR) -> Path:
    jalur.parent.mkdir(parents=True, exist_ok=True)
    s.to_parquet(jalur, index=False)
    return jalur
