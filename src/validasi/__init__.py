"""Tahap 8 — Validasi Silver, Gold, dan Rekonsiliasi dengan Pandera."""
from pathlib import Path
import pandas as pd

try:
    import pandera.pandas as pa
except ImportError:
    import pandera as pa

ROOT = Path(__file__).resolve().parents[2]
SILVER = ROOT / "data" / "silver" / "silver.parquet"
GOLD_DIR = ROOT / "data" / "gold"
LAPORAN = ROOT / "reports" / "validasi.md"
KUNCI = ["sumber", "seri_kode", "wilayah_kode", "periode", "rincian", "_berkas_raw"]

KODE_WILAYAH_SAH = {
    1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 1900, 2100,
    3100, 3200, 3300, 3400, 3500, 3600, 5100, 5200, 5300,
    6100, 6200, 6300, 6400, 6500, 7100, 7200, 7300, 7400, 7500, 7600,
    8100, 8200, 9100, 9200, 9400, 9500, 9600, 9700, 9999,
}

KATEGORI_REKONSILIASI_SAH = {
    "definisi berbeda",
    "metode berbeda",
    "vintage berbeda",
    "cakupan berbeda",
    "belum terjelaskan",
    "tanpa pasangan",
}

SKEMA = pa.DataFrameSchema(
    {
        "sumber": pa.Column(str, pa.Check.isin(["bps", "wdi"]), nullable=False),
        "seri_kode": pa.Column(str, nullable=False),
        "wilayah_kode": pa.Column("int64", pa.Check.isin(KODE_WILAYAH_SAH), nullable=False, coerce=True),
        "nama_wilayah": pa.Column(str, nullable=False),
        "periode": pa.Column(str, pa.Check.str_matches(r"^\d{4}$"), nullable=False),
        "jenis_periode": pa.Column(str, pa.Check.equal_to("tahun"), nullable=False),
        "rincian": pa.Column(str, nullable=False),
        "nilai": pa.Column("float64", pa.Check.in_range(0, 100), nullable=False, coerce=True),
        "satuan": pa.Column(str, pa.Check.equal_to("persen"), nullable=False),
        "_berkas_raw": pa.Column(str, nullable=False),
        "_sha256_raw": pa.Column(str, pa.Check.str_length(64, 64), nullable=False),
    },
    unique=KUNCI,
    strict=False,
)


def _muat_tabel_gold(gold):
    """Mengambil panel_provinsi (memuat status_sel & jejak Silver) dan rekonsiliasi secara eksplisit."""
    df_panel, df_rekon = None, None

    if isinstance(gold, dict):
        for kunci in ("panel_provinsi", "panel_lebar", "panel", "gold_panel"):
            if isinstance(gold.get(kunci), pd.DataFrame):
                df_panel = gold[kunci]
                break
        if isinstance(gold.get("rekonsiliasi"), pd.DataFrame):
            df_rekon = gold["rekonsiliasi"]
    elif isinstance(gold, pd.DataFrame):
        df_panel = gold

    if df_panel is None and GOLD_DIR.exists():
        for nama_berkas in ("panel_provinsi.parquet", "panel_lebar.parquet", "gold_panel.parquet"):
            path_kandidat = GOLD_DIR / nama_berkas
            if path_kandidat.exists():
                df_panel = pd.read_parquet(path_kandidat)
                break

    if df_rekon is None and GOLD_DIR.exists():
        path_rekon = GOLD_DIR / "rekonsiliasi.parquet"
        if path_rekon.exists():
            df_rekon = pd.read_parquet(path_rekon)

    return df_panel, df_rekon


def jalankan(silver=None, gold=None):
    df = pd.read_parquet(SILVER) if SILVER.exists() else silver
    hasil = []

    # --- ATURAN VALIDASI SILVER (SPRINT 1) ---
    # 1. Skema Pandera & rentang nilai 0-100
    try:
        SKEMA.validate(df, lazy=True)
        hasil.append(("skema_dan_rentang_0_100", True, f"lolos ({len(df):,} baris, rentang {df['nilai'].min():.2f}-{df['nilai'].max():.2f})"))
    except pa.errors.SchemaErrors as e:
        hasil.append(("skema_dan_rentang_0_100", False, f"{len(e.failure_cases)} pelanggaran"))

    # 2. Keunikan kunci Silver
    dup = int(df.duplicated(KUNCI).sum())
    hasil.append(("keunikan_kunci_silver", dup == 0, f"{dup} duplikat kunci"))

    # 3. Konsistensi satuan per seri
    satuan_ganda = int((df.groupby("seri_kode")["satuan"].nunique() != 1).sum())
    hasil.append(("konsistensi_satuan_seri", satuan_ganda == 0, f"{df['seri_kode'].nunique()} seri bersatuan tunggal"))

    # 4. Satu angka total kanonik per provinsi x tahun (K-003)
    prov = df[df["wilayah_kode"] != 9999]
    kanonik = pd.concat([
        prov[(prov["seri_kode"] == "tabel:sdg4_amh_rinci") & (prov["rincian"] == "total") & (prov["periode"] < "2014")],
        prov[(prov["seri_kode"] == "var1458") & (prov["periode"] >= "2014")],
    ])
    ganda_kanonik = int((kanonik.groupby(["wilayah_kode", "periode"]).size() != 1).sum())
    hasil.append(("satu_total_kanonik_prov_tahun", ganda_kanonik == 0, f"{len(kanonik)} sel kanonik, {ganda_kanonik} ganda"))

    # 5. Laporan selisih total rinci vs ringkas (dilaporkan, tidak disamakan paksa)
    rinci = df[(df["seri_kode"] == "tabel:sdg4_amh_rinci") & (df["rincian"] == "total")]
    ringkas = df[df["seri_kode"] == "var1458"]
    irisan = pd.merge(rinci, ringkas, on=["wilayah_kode", "periode"], suffixes=("_rinci", "_var1458"))
    irisan["selisih"] = (irisan["nilai_rinci"] - irisan["nilai_var1458"]).round(4)
    beda = irisan[irisan["selisih"].abs() > 1e-6].sort_values(["wilayah_kode", "periode"])
    hasil.append(("laporan_selisih_rinci_ringkas", len(irisan) > 0, f"{len(beda)} dari {len(irisan)} sel berselisih (tahun {sorted(beda['periode'].unique())})"))

    # --- ATURAN VALIDASI GOLD & REKONSILIASI (SPRINT 2) ---
    df_panel, df_rekon = _muat_tabel_gold(gold)

    if df_panel is not None and not df_panel.empty:
        kunci_panel = [c for c in ["wilayah_kode", "periode", "indikator", "rincian"] if c in df_panel.columns]

        # 6. Kunci panel Gold unik
        dup_gold = int(df_panel.duplicated(kunci_panel).sum())
        hasil.append(("gold_kunci_panel_unik", dup_gold == 0, f"{dup_gold} duplikat kunci ({', '.join(kunci_panel)})"))

        # 7. Satuan satu per indikator (kecualikan kolom tahun & metadata)
        if "satuan" in df_panel.columns:
            kolom_grup = "indikator" if "indikator" in df_panel.columns else "rincian"
            sat_ganda = int((df_panel.groupby(kolom_grup)["satuan"].nunique() != 1).sum())
            hasil.append(("gold_satuan_satu_per_indikator", sat_ganda == 0, f"{df_panel[kolom_grup].nunique()} indikator bersatuan tunggal"))
        else:
            kolom_non_indikator = {"wilayah_kode", "nama_wilayah", "periode", "tahun", "jenis_periode", "satuan", "sumber", "status_sel"}
            kolom_ind = [c for c in df_panel.columns if c not in kolom_non_indikator and not str(c).startswith("_")]
            num_cols = df_panel[kolom_ind].select_dtypes(include="number")
            di_luar_rentang = int(((num_cols < 0) | (num_cols > 100)).sum().sum())
            hasil.append(("gold_satuan_satu_per_indikator", di_luar_rentang == 0, f"satuan konsisten (persen 0-100 pada {len(num_cols.columns)} indikator)"))

        # 8. Setiap sel Gold berstatus terisi punya pasangan di Silver
        pasangan_silver = set(zip(df["wilayah_kode"].astype(int), df["periode"].astype(str)))
        if "status_sel" in df_panel.columns:
            df_terisi = df_panel[df_panel["status_sel"].astype(str).str.lower() == "terisi"]
        elif "nilai" in df_panel.columns:
            df_terisi = df_panel[df_panel["nilai"].notna()]
        else:
            kolom_non_indikator = {"wilayah_kode", "nama_wilayah", "periode", "tahun", "jenis_periode", "satuan", "sumber", "status_sel"}
            kolom_ind = [c for c in df_panel.columns if c not in kolom_non_indikator and not str(c).startswith("_")]
            df_terisi = df_panel[df_panel[kolom_ind].notna().any(axis=1)]

        pasangan_gold_terisi = set(zip(df_terisi["wilayah_kode"].astype(int), df_terisi["periode"].astype(str)))
        tanpa_induk = len(pasangan_gold_terisi - pasangan_silver)
        hasil.append(("gold_setiap_sel_punya_pasangan_silver", tanpa_induk == 0, f"{len(pasangan_gold_terisi)} sel terisi diperiksa, {tanpa_induk} tanpa pasangan Silver"))

    if df_rekon is not None and not df_rekon.empty:
        # 9. Setiap baris rekonsiliasi berpasangan punya kategori sah ("belum terjelaskan", dll.)
        kolom_kat = next((c for c in df_rekon.columns if "kategori" in c.lower()), None)
        if kolom_kat is None:
            hasil.append(("rekonsiliasi_kategori_baris_berpasangan", False, "kolom kategori tidak ditemukan"))
        else:
            if "_asal" in df_rekon.columns:
                berpasangan = df_rekon[df_rekon["_asal"] == "both"]
            else:
                kolom_nilai = [c for c in df_rekon.columns if "nilai" in c.lower()]
                berpasangan = df_rekon.dropna(subset=kolom_nilai) if len(kolom_nilai) >= 2 else df_rekon

            kat_bersih = berpasangan[kolom_kat].fillna("").astype(str).str.strip().str.lower()
            tidak_sah = int((~kat_bersih.isin(KATEGORI_REKONSILIASI_SAH)).sum())
            hasil.append((
                "rekonsiliasi_kategori_baris_berpasangan",
                tidak_sah == 0 and len(berpasangan) > 0,
                f"{len(berpasangan)} baris berpasangan diperiksa, {tidak_sah} kategori kosong/tidak sah",
            ))

    # --- TULIS LAPORAN VALIDASI ---
    LAPORAN.parent.mkdir(parents=True, exist_ok=True)
    baris_md = ["# Laporan Validasi Silver & Gold\n", "## Ringkasan Aturan\n", "| Aturan | Status | Keterangan |", "|---|---|---|"]
    for nama, ok, ket in hasil:
        status = "LOLOS" if ok else "GAGAL"
        print(f"           [{status}] {nama}: {ket}")
        baris_md.append(f"| `{nama}` | **{status}** | {ket} |")

    baris_md.append("\n## Selisih Total Rinci vs Ringkas (`var1458`)\n")
    baris_md.append("| Kode | Wilayah | Tahun | Total Rinci | Total var1458 | Selisih |")
    baris_md.append("|---|---|---|---:|---:|---:|")
    for r in beda.itertuples(index=False):
        baris_md.append(f"| {r.wilayah_kode} | {r.nama_wilayah_rinci} | {r.periode} | {r.nilai_rinci:.2f} | {r.nilai_var1458:.2f} | {r.selisih:+.2f} |")

    LAPORAN.write_text("\n".join(baris_md) + "\n", encoding="utf-8")

    lolos = sum(ok for _, ok, _ in hasil)
    print(f"           Validasi: {lolos}/{len(hasil)} aturan lolos -> {LAPORAN.relative_to(ROOT)}")
    if lolos < len(hasil):
        raise AssertionError("Ada aturan validasi yang gagal")
    return {"aturan_validasi": len(hasil), "aturan_lolos": lolos}


if __name__ == "__main__":
    jalankan()
