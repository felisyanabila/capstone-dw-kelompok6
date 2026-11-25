import json
from pathlib import Path
import pandas as pd
from src.common.manifest import RAW, baca

ROOT = Path(__file__).resolve().parents[2]


def jalankan(raw_root: Path = RAW):
    """Baca berkas mentah BPS dan WDI menjadi DataFrame mentah ber-provenans."""
    raw_path = Path(raw_root)
    manifest = baca(raw_path)

    berkas_amh = "bps/2026-10-17/sdg4_amh.csv"
    df_amh = pd.read_csv(raw_path / berkas_amh)
    df_amh["_berkas_raw"] = berkas_amh
    df_amh["_sha256_raw"] = manifest[berkas_amh]

    berkas_rinci = "bps/2026-10-17/sdg4_amh_rinci.csv"
    df_rinci = pd.read_csv(raw_path / berkas_rinci)
    df_rinci["_berkas_raw"] = berkas_rinci
    df_rinci["_sha256_raw"] = manifest[berkas_rinci]

    berkas_wdi = "wdi/2026-10-20/data/kelompok-03-hal-01.json"
    raw_wdi = json.load(open(raw_path / berkas_wdi, encoding="utf-8"))
    rows_wdi = raw_wdi[1] if isinstance(raw_wdi, list) and len(raw_wdi) > 1 and isinstance(raw_wdi[1], list) else []
    wdi_records = []
    for item in rows_wdi:
        ind = item.get("indicator") or {}
        country = item.get("country") or {}
        wdi_records.append({
            "indicator_id": ind.get("id"),
            "indicator_value": ind.get("value"),
            "country_id": country.get("id"),
            "country_value": country.get("value"),
            "countryiso3code": item.get("countryiso3code"),
            "date": item.get("date"),
            "value": item.get("value"),
            "unit": item.get("unit"),
            "obs_status": item.get("obs_status"),
            "decimal": item.get("decimal"),
        })
    df_wdi = pd.DataFrame(wdi_records)
    df_wdi["_berkas_raw"] = berkas_wdi
    df_wdi["_sha256_raw"] = manifest[berkas_wdi]

    return {
        "bps_amh": df_amh,
        "bps_rinci": df_rinci,
        "wdi": df_wdi,
    }
