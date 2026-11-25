import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
KATEGORI_SAH = {
    "definisi berbeda",
    "metode berbeda",
    "vintage berbeda",
    "cakupan berbeda",
    "belum terjelaskan",
}


def muat_wdi_literasi_indonesia(raw_root: Path = ROOT / "data" / "raw") -> pd.DataFrame:
    """Ambil seri WDI SE.ADT.LITR.ZS untuk Indonesia (IDN / wilayah_kode 9999)."""
    jalur_wdi = raw_root / "wdi" / "2026-10-20" / "data" / "kelompok-03-hal-01.json"
    data = json.load(open(jalur_wdi, encoding="utf-8"))
    rows = data[1] if isinstance(data, list) and len(data) > 1 and isinstance(data[1], list) else []
    records = []
    for item in rows:
        kode_ind = (item.get("indicator") or {}).get("id")
        iso3 = item.get("countryiso3code")
        if kode_ind == "SE.ADT.LITR.ZS" and iso3 == "IDN":
            periode = str(item.get("date", "")).strip()
            val = item.get("value")
            if periode.isdigit() and val is not None:
                records.append({
                    "wilayah_kode": 9999,
                    "nama_wilayah": "Indonesia",
                    "periode": periode,
                    "nilai_pembanding": float(val),
                })
    return pd.DataFrame(records).drop_duplicates(subset=["wilayah_kode", "periode"])


def _klasifikasi_wdi(row) -> tuple[str, str]:
    if pd.isna(row["nilai_utama"]) or pd.isna(row["nilai_pembanding"]):
        return (
            "cakupan berbeda",
            "Salah satu sumber tidak memiliki observasi pada periode ini; baris tetap dipertahankan tanpa imputasi.",
        )
    selisih = abs(float(row["selisih"]))
    if selisih == 0:
        return ("definisi berbeda", "Nilai identik pada periode ini, meski sumber WDI vs BPS memiliki perbedaan definisi/metode survei.")
    return (
        "definisi berbeda",
        f"Selisih {row['selisih']:.4f} poin: BPS memakai definisi melek aksara nasional (Susenas/SDG 4.6.1), sedangkan WDI SE.ADT.LITR.ZS mengikuti standar/kompilasi UNESCO Institute for Statistics (UIS) serta ketersediaan tahun rilis WDI.",
    )


def _klasifikasi_rinci_vs_var1458(row) -> tuple[str, str]:
    if pd.isna(row["nilai_utama"]) or pd.isna(row["nilai_pembanding"]):
        return (
            "cakupan berbeda",
            "Periode atau wilayah tidak tersedia pada salah satu tabel BPS; baris tetap ditampilkan.",
        )
    selisih = abs(float(row["selisih"]))
    if selisih == 0:
        return (
            "metode berbeda",
            "Angka total tabel rinci ('Perkotaan + Perdesaan' & 'Laki-laki+Perempuan') sama persis dengan var1458 pada wilayah dan tahun ini.",
        )
    return (
        "belum terjelaskan",
        f"Dugaan: perbedaan pembulatan/penimbang/revisi antar-tabel BPS (selisih {row['selisih']:.4f} poin pada periode {row['periode']}). Bukti yang dicek: membandingkan langsung nilai pada wilayah_kode dan periode yang sama di sdg4_amh_rinci.csv dan sdg4_amh.csv.",
    )


def bangun_rekonsiliasi(
    df_var1458: pd.DataFrame,
    df_rinci_total: pd.DataFrame,
    df_wdi_idn: pd.DataFrame,
) -> pd.DataFrame:
    """Gabungkan seri utama dengan pembandingnya tanpa menghapus selisih atau periode tanpa pasangan."""
    # Pasangan 1: Total tabel rinci vs var1458 (provinsi & tahun yang sama)
    p1 = pd.merge(
        df_rinci_total[["wilayah_kode", "nama_wilayah", "periode", "nilai"]].rename(columns={"nilai": "nilai_utama"}),
        df_var1458[["wilayah_kode", "nama_wilayah", "periode", "nilai"]].rename(columns={"nilai": "nilai_pembanding"}),
        on=["wilayah_kode", "periode"],
        how="outer",
        suffixes=("_rinci", "_var"),
    )
    p1["pasangan"] = "rinci_total_vs_var1458"
    p1["nama_wilayah"] = p1["nama_wilayah_rinci"].fillna(p1["nama_wilayah_var"])
    p1["selisih"] = p1["nilai_utama"] - p1["nilai_pembanding"]
    klas_p1 = p1.apply(_klasifikasi_rinci_vs_var1458, axis=1)
    p1["kategori"] = [k[0] for k in klas_p1]
    p1["catatan_bukti"] = [k[1] for k in klas_p1]

    # Pasangan 2: var1458 baris Indonesia (9999) vs WDI SE.ADT.LITR.ZS pada tahun yang tersedia di WDI
    var_idn = df_var1458[df_var1458["wilayah_kode"] == 9999][["wilayah_kode", "nama_wilayah", "periode", "nilai"]].rename(
        columns={"nilai": "nilai_utama"}
    )
    p2 = pd.merge(
        var_idn,
        df_wdi_idn[["wilayah_kode", "nama_wilayah", "periode", "nilai_pembanding"]],
        on=["wilayah_kode", "periode"],
        how="outer",
        suffixes=("_bps", "_wdi"),
    )
    p2["pasangan"] = "var1458_idn_vs_wdi_litr"
    p2["nama_wilayah"] = p2["nama_wilayah_bps"].fillna(p2["nama_wilayah_wdi"]).fillna("Indonesia")
    p2["selisih"] = p2["nilai_utama"] - p2["nilai_pembanding"]
    klas_p2 = p2.apply(_klasifikasi_wdi, axis=1)
    p2["kategori"] = [k[0] for k in klas_p2]
    p2["catatan_bukti"] = [k[1] for k in klas_p2]

    kolom_keluaran = [
        "pasangan",
        "wilayah_kode",
        "nama_wilayah",
        "periode",
        "nilai_utama",
        "nilai_pembanding",
        "selisih",
        "kategori",
        "catatan_bukti",
    ]
    gabung = pd.concat(
        [p1[kolom_keluaran], p2[kolom_keluaran]],
        ignore_index=True,
    )
    gabung["wilayah_kode"] = gabung["wilayah_kode"].astype(int)
    gabung["periode"] = gabung["periode"].astype(str)
    return gabung.sort_values(["pasangan", "wilayah_kode", "periode"]).reset_index(drop=True)
