"""Tahap 8 (mulai Sprint 1) — Validasi dasar Silver dengan Pandera."""
from pathlib import Path
import pandas as pd

try:
    import pandera.pandas as pa
except ImportError:
    import pandera as pa

ROOT = Path(__file__).resolve().parents[2]
SILVER = ROOT / "data" / "silver" / "silver.parquet"
LAPORAN = ROOT / "reports" / "validasi.md"
KUNCI = ["sumber", "seri_kode", "wilayah_kode", "periode", "rincian", "_berkas_raw"]

KODE_WILAYAH_SAH = {
    1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 1900, 2100,
    3100, 3200, 3300, 3400, 3500, 3600, 5100, 5200, 5300,
    6100, 6200, 6300, 6400, 6500, 7100, 7200, 7300, 7400, 7500, 7600,
    8100, 8200, 9100, 9200, 9400, 9500, 9600, 9700, 9999,
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


def jalankan(silver=None, gold=None):
    df = pd.read_parquet(SILVER) if SILVER.exists() else silver
    hasil = []

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

    LAPORAN.parent.mkdir(parents=True, exist_ok=True)
    baris_md = ["# Laporan Validasi Silver\n", "## Ringkasan Aturan\n", "| Aturan | Status | Keterangan |", "|---|---|---|"]
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
        raise AssertionError("Ada aturan validasi Silver yang gagal")
    from src.validasi.kamus_data import buat_kamus_data
    buat_kamus_data(df)
    
    return {"aturan_validasi": len(hasil), "aturan_lolos": lolos}


if __name__ == "__main__":
    jalankan()
