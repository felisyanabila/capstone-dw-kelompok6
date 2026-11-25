import sqlite3
from pathlib import Path
import pandas as pd
from src.gold.rekonsiliasi import bangun_rekonsiliasi, muat_wdi_literasi_indonesia

ROOT = Path(__file__).resolve().parents[2]


def jalankan(silver: pd.DataFrame, out_dir: Path = ROOT / "data" / "gold") -> dict:
    """Bentuk tabel Gold (panel + rekonsiliasi nasional) dan simpan ke Parquet serta SQLite."""
    gold_path = Path(out_dir)
    gold_path.mkdir(parents=True, exist_ok=True)

    df_var1458 = silver[(silver["sumber"] == "bps") & (silver["seri_kode"] == "var1458")].copy()
    df_rinci = silver[(silver["sumber"] == "bps") & (silver["seri_kode"] == "tabel:sdg4_amh_rinci")].copy()
    df_rinci_total = df_rinci[df_rinci["rincian"] == "daerah=Perkotaan + Perdesaan|jk=Laki-laki+Perempuan"].copy()

    df_wdi = silver[(silver["sumber"] == "wdi") & (silver["seri_kode"] == "SE.ADT.LITR.ZS")].copy()
    if df_wdi.empty:
        df_wdi_idn = muat_wdi_literasi_indonesia()
    else:
        df_wdi_idn = df_wdi[df_wdi["wilayah_kode"] == 9999][["wilayah_kode", "nama_wilayah", "periode", "nilai"]].rename(
            columns={"nilai": "nilai_pembanding"}
        )

    # Tabel panel utama (grid lengkap wilayah x periode untuk seri utama)
    wilayah_unik = df_var1458[["wilayah_kode", "nama_wilayah"]].drop_duplicates()
    periode_unik = sorted(set(df_var1458["periode"]).union(set(df_rinci_total["periode"])))
    grid = wilayah_unik.merge(pd.DataFrame({"periode": periode_unik}), how="cross")
    panel = (
        grid.merge(
            df_var1458[["wilayah_kode", "periode", "nilai"]].rename(columns={"nilai": "amh_var1458"}),
            on=["wilayah_kode", "periode"],
            how="left",
        )
        .merge(
            df_rinci_total[["wilayah_kode", "periode", "nilai"]].rename(columns={"nilai": "amh_rinci_total"}),
            on=["wilayah_kode", "periode"],
            how="left",
        )
        .sort_values(["wilayah_kode", "periode"])
        .reset_index(drop=True)
    )

    # Tabel rekonsiliasi (Tahap 6)
    rekonsiliasi = bangun_rekonsiliasi(
        df_var1458=df_var1458,
        df_rinci_total=df_rinci_total,
        df_wdi_idn=df_wdi_idn,
    )

    panel.to_parquet(gold_path / "panel_melek_aksara.parquet", index=False)
    rekonsiliasi.to_parquet(gold_path / "rekonsiliasi.parquet", index=False)

    with sqlite3.connect(gold_path / "gold.sqlite") as conn:
        panel.to_sql("panel_melek_aksara", conn, if_exists="replace", index=False)
        rekonsiliasi.to_sql("rekonsiliasi", conn, if_exists="replace", index=False)

    return {
        "panel_melek_aksara": panel,
        "rekonsiliasi": rekonsiliasi,
    }
