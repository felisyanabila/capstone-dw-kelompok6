from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]

PETA_WILAYAH = {
    "ACEH": (1100, "Aceh"),
    "SUMATERA UTARA": (1200, "Sumatera Utara"),
    "SUMATERA BARAT": (1300, "Sumatera Barat"),
    "RIAU": (1400, "Riau"),
    "JAMBI": (1500, "Jambi"),
    "SUMATERA SELATAN": (1600, "Sumatera Selatan"),
    "BENGKULU": (1700, "Bengkulu"),
    "LAMPUNG": (1800, "Lampung"),
    "KEP. BANGKA BELITUNG": (1900, "Kepulauan Bangka Belitung"),
    "KEPULAUAN BANGKA BELITUNG": (1900, "Kepulauan Bangka Belitung"),
    "KEP. RIAU": (2100, "Kepulauan Riau"),
    "KEPULAUAN RIAU": (2100, "Kepulauan Riau"),
    "DKI JAKARTA": (3100, "DKI Jakarta"),
    "JAWA BARAT": (3200, "Jawa Barat"),
    "JAWA TENGAH": (3300, "Jawa Tengah"),
    "DI YOGYAKARTA": (3400, "DI Yogyakarta"),
    "JAWA TIMUR": (3500, "Jawa Timur"),
    "BANTEN": (3600, "Banten"),
    "BALI": (5100, "Bali"),
    "NUSA TENGGARA BARAT": (5200, "Nusa Tenggara Barat"),
    "NUSA TENGGARA TIMUR": (5300, "Nusa Tenggara Timur"),
    "KALIMANTAN BARAT": (6100, "Kalimantan Barat"),
    "KALIMANTAN TENGAH": (6200, "Kalimantan Tengah"),
    "KALIMANTAN SELATAN": (6300, "Kalimantan Selatan"),
    "KALIMANTAN TIMUR": (6400, "Kalimantan Timur"),
    "KALIMANTAN UTARA": (6500, "Kalimantan Utara"),
    "SULAWESI UTARA": (7100, "Sulawesi Utara"),
    "SULAWESI TENGAH": (7200, "Sulawesi Tengah"),
    "SULAWESI SELATAN": (7300, "Sulawesi Selatan"),
    "SULAWESI TENGGARA": (7400, "Sulawesi Tenggara"),
    "GORONTALO": (7500, "Gorontalo"),
    "SULAWESI BARAT": (7600, "Sulawesi Barat"),
    "MALUKU": (8100, "Maluku"),
    "MALUKU UTARA": (8200, "Maluku Utara"),
    "PAPUA BARAT": (9100, "Papua Barat"),
    "PAPUA BARAT DAYA": (9200, "Papua Barat Daya"),
    "PAPUA": (9400, "Papua"),
    "PAPUA SELATAN": (9500, "Papua Selatan"),
    "PAPUA TENGAH": (9600, "Papua Tengah"),
    "PAPUA PEGUNUNGAN": (9700, "Papua Pegunungan"),
    "INDONESIA": (9999, "Indonesia"),
}


def _petakan_wilayah(nama: str):
    kunci = str(nama or "").strip().upper()
    if kunci not in PETA_WILAYAH:
        raise ValueError(f"Nama wilayah tidak dikenal: {nama}")
    return PETA_WILAYAH[kunci]


def jalankan(mentah: dict, out_path: Path = ROOT / "data" / "silver" / "silver.parquet") -> pd.DataFrame:
    """Bersihkan dan seragamkan data mentah ke skema Silver."""
    baris_silver = []

    # 1. BPS var1458 (sdg4_amh.csv)
    for r in mentah["bps_amh"].to_dict("records"):
        if pd.isna(r.get("nilai")):
            continue
        kode, nama_baku = _petakan_wilayah(r.get("wilayah"))
        baris_silver.append({
            "sumber": "bps",
            "seri_kode": f"var{int(r['var_id'])}",
            "wilayah_kode": int(kode),
            "nama_wilayah": nama_baku,
            "periode": str(int(r["tahun"])),
            "jenis_periode": "tahun",
            "rincian": "total",
            "nilai": float(r["nilai"]),
            "satuan": "persen",
            "_berkas_raw": r["_berkas_raw"],
            "_sha256_raw": r["_sha256_raw"],
        })

    # 2. BPS tabel rinci (sdg4_amh_rinci.csv)
    for r in mentah["bps_rinci"].to_dict("records"):
        if pd.isna(r.get("nilai")):
            continue
        kode, nama_baku = _petakan_wilayah(r.get("wilayah"))
        rincian_label = f"daerah={str(r.get('daerah', '')).strip()}|jk={str(r.get('jenis_kelamin', '')).strip()}"
        baris_silver.append({
            "sumber": "bps",
            "seri_kode": "tabel:sdg4_amh_rinci",
            "wilayah_kode": int(kode),
            "nama_wilayah": nama_baku,
            "periode": str(int(r["tahun"])),
            "jenis_periode": "tahun",
            "rincian": rincian_label,
            "nilai": float(r["nilai"]),
            "satuan": "persen",
            "_berkas_raw": r["_berkas_raw"],
            "_sha256_raw": r["_sha256_raw"],
        })

    # 3. WDI SE.ADT.LITR.ZS untuk Indonesia (IDN -> 9999)
    for r in mentah["wdi"].to_dict("records"):
        if r.get("indicator_id") != "SE.ADT.LITR.ZS" or r.get("countryiso3code") != "IDN":
            continue
        if pd.isna(r.get("value")):
            continue
        periode_str = str(r.get("date", "")).strip()
        if not periode_str.isdigit():
            continue
        baris_silver.append({
            "sumber": "wdi",
            "seri_kode": "SE.ADT.LITR.ZS",
            "wilayah_kode": 9999,
            "nama_wilayah": "Indonesia",
            "periode": periode_str,
            "jenis_periode": "tahun",
            "rincian": "total",
            "nilai": float(r["value"]),
            "satuan": "persen",
            "_berkas_raw": r["_berkas_raw"],
            "_sha256_raw": r["_sha256_raw"],
        })

    df_silver = pd.DataFrame(baris_silver)
    df_silver["wilayah_kode"] = df_silver["wilayah_kode"].astype("int64")
    df_silver["nilai"] = df_silver["nilai"].astype("float64")
    df_silver = df_silver.drop_duplicates(
        subset=["sumber", "seri_kode", "wilayah_kode", "periode", "rincian", "_berkas_raw"],
        keep="last",
    ).reset_index(drop=True)

    out_file = Path(out_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    df_silver.to_parquet(out_file, index=False)
    return df_silver
