"""Penyusun otomatis docs/data-dictionary.md dari data nyata Silver."""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SILVER = ROOT / "data" / "silver" / "silver.parquet"
MANIFEST = ROOT / "data" / "raw" / "MANIFEST.csv"
KELUARAN = ROOT / "docs" / "data-dictionary.md"

META_KOLOM = {
    "sumber": ("–", "nama folder tingkat pertama di `data/raw/` (`K-005`, `K-017`)", "Identitas penyedia data sumber (`bps` untuk BPS dan `wdi` untuk World Development Indicators Bank Dunia)."),
    "seri_kode": ("–", "nama berkas/katalog BPS & kode indikator WDI (`K-003`, `K-012`, `K-013`, `K-018`)", "Kode seri indikator baku: `var1458` & `tabel:sdg4_amh_rinci` (SDG 4.6.1 AMH 15+), serta `SE.ADT.LITR.ZS` (pembanding WDI)."),
    "wilayah_kode": ("kode BPS × 100 (atau `9999`)", "peta kode BPS 2 digit × 100 tata 38 provinsi 2025 (`K-001`, `K-002`, `K-005`, `K-018`)", "Kode wilayah baku lintas sumber: `9999` untuk nasional Indonesia dan `1100`–`9700` untuk 38 provinsi."),
    "nama_wilayah": ("–", "master nama wilayah `var1458` & label `Indonesia` WDI (`K-002`, `K-005`)", "Nama provinsi atau negara yang telah dinormalisasi ejaan dan kapitalisasinya."),
    "periode": ("`YYYY` (4 digit tahun)", "kolom tahun `var1458`, header tahun tabel rinci, & field `date` WDI (`K-014`, `K-015`)", "Tahun pengamatan indikator (cakupan WDI 1980–2024 dan BPS 2009–2025)."),
    "jenis_periode": ("–", "konstanta penyeragaman frekuensi (`K-014`)", "Granularitas waktu pengamatan; seluruh baris Silver berfrekuensi tahunan (`tahun`)."),
    "rincian": ("–", "hasil enkode daerah × jenis kelamin tabel rinci; `total` untuk `var1458` & WDI (`K-015`)", "Disagregasi demografis/spasial (`total`, `perkotaan`, `perdesaan`, `laki-laki`, `perempuan`, dan kombinasinya)."),
    "nilai": ("`persen` (`0–100`)", "angka pengamatan mentah tanpa imputasi maupun winsorizing (`K-007`, `K-008`, `K-016`, `K-019`)", "Persentase angka melek aksara penduduk usia 15 tahun ke atas."),
    "satuan": ("–", "penyeragaman label `Persen` / satuan implisit tabel rinci / unit WDI (`K-009`, `K-010`, `K-011`)", "Satuan pengukuran baku (`persen`) untuk seluruh seri pada tabel Silver."),
    "_berkas_raw": ("path relatif `data/raw/`", "jejak berkas sumber pada `data/raw/MANIFEST.csv` (`K-008`, `K-017`)", "Jalur relatif berkas mentah asal baris data; menjadi bagian kunci unik Silver."),
    "_sha256_raw": ("hex 64 karakter", "hash SHA-256 berkas sumber pada `data/raw/MANIFEST.csv` (`src/common/manifest.py`)", "Sidik jari kriptografis berkas mentah untuk verifikasi integritas dan keterlacakan data."),
    "kategori_anomali": ("–", "deteksi calon anomali di `src/silver/anomali_amh.py` (`K-006`, `K-007`, `K-019`)", "Label diagnostik calon anomali (`outlier_asli`, `patahan_metode`, `patahan_wilayah`, `revisi_snapshot`) tanpa mengubah `nilai`."),
}


def buat_kamus_data(silver=None):
    df = pd.read_parquet(SILVER) if SILVER.exists() else silver
    manifest = pd.read_csv(MANIFEST).set_index("berkas")

    baris_tabel = []
    for col in df.columns:
        s = df[col]
        kosong = int(s.isna().sum())
        boleh_kosong = f"ya ({kosong:,} kosong)" if kosong > 0 else "tidak (0 kosong)"
        if pd.api.types.is_numeric_dtype(s):
            rentang = f"`{s.min():.2f}` – `{s.max():.2f}`" if pd.api.types.is_float_dtype(s) else f"`{int(s.min())}` – `{int(s.max())}` ({s.nunique()} nilai unik)"
        else:
            unik = s.dropna().unique().tolist()
            rentang = ", ".join(f"`{u}`" for u in unik) if len(unik) <= 9 else f"{len(unik)} nilai unik (mis. `{unik[0]}`, `{unik[1]}`, `{unik[-1]}`)"
        satuan, asal, ket = META_KOLOM.get(col, ("–", "olahan Silver", "Kolom tabel Silver."))
        baris_tabel.append(f"| `{col}` | `{s.dtype}` | {satuan} | {boleh_kosong} | {rentang} | {asal} | {ket} |")

    sub = df[df["_berkas_raw"] == "bps/2026-10-17/csv/sdg4_amh.csv"]
    contoh = sub.iloc[0] if len(sub) > 0 else df.iloc[0]
    berkas = contoh["_berkas_raw"]
    sha_silver = contoh["_sha256_raw"]
    m_row = manifest.loc[berkas]
    assert sha_silver == m_row["sha256"], "Hash _sha256_raw tidak cocok dengan MANIFEST.csv"

    teks = f"""# Data dictionary — Kelompok 6 (Kasus 06: Literasi / Angka Melek Aksara)

Satu tabel per keluaran (Silver dan setiap tabel Gold). Isi dari data nyata, bukan dari ingatan: tipe, satuan, rentang, dan jumlah kosong dihitung ulang setiap kali pipeline berjalan (`{len(df):,}` baris, `{len(df.columns)}` kolom).

## `data/silver/silver.parquet`

| Kolom | Tipe | Satuan/format | Boleh kosong | Rentang atau nilai sah | Asal (berkas/aturan) | Keterangan |
|---|---|---|---|---|---|---|
{chr(10).join(baris_tabel)}

### Contoh Penelusuran Satu Baris Silver ke Berkas Mentah (`data/raw/`)

Setiap baris pada `data/silver/silver.parquet` dapat ditelusuri kembali ke berkas sumber aslinya di `data/raw/` melalui pasangan kolom `_berkas_raw` dan `_sha256_raw`:

1. **Contoh baris pada `data/silver/silver.parquet`:**
   - `sumber`: `{contoh['sumber']}`
   - `seri_kode`: `{contoh['seri_kode']}`
   - `wilayah_kode`: `{int(contoh['wilayah_kode'])}` (`{contoh['nama_wilayah']}`)
   - `periode`: `{contoh['periode']}` (`{contoh['jenis_periode']}`)
   - `rincian`: `{contoh['rincian']}`
   - `nilai`: `{contoh['nilai']:.2f}` `{contoh['satuan']}`
   - `kategori_anomali`: `{contoh['kategori_anomali'] if pd.notna(contoh['kategori_anomali']) else 'kosong (normal)'}`
   - `_berkas_raw`: `{berkas}`
   - `_sha256_raw`: `{sha_silver}`

2. **Verifikasi pada `data/raw/MANIFEST.csv`:**
   - Entri `berkas`: `{berkas}`
   - Ukuran `bait`: `{int(m_row['bait']):,}` bait
   - Nilai `sha256`: `{m_row['sha256']}` (**cocok identik** dengan `_sha256_raw`)

3. **Lokasi sel pada berkas mentah:**
   - Buka berkas `data/raw/{berkas}`, cari baris wilayah `{contoh['nama_wilayah']}` (kode BPS `{int(contoh['wilayah_kode']) // 100}`), lalu baca kolom tahun `{contoh['periode']}` sehingga diperoleh nilai mentah `{contoh['nilai']:.2f}` (satuan asli `Persen` sebelum dinormalisasi menjadi `persen` sesuai `K-009`).

## `data/gold/<tabel>.parquet`

*Akan dilengkapi pada Sprint 2–3 setelah pembentukan tabel Gold.*

| Kolom | Tipe | Satuan/format | Boleh kosong | Rentang atau nilai sah | Asal (berkas/aturan) | Keterangan |
|---|---|---|---|---|---|---|
"""
    KELUARAN.parent.mkdir(parents=True, exist_ok=True)
    KELUARAN.write_text(teks, encoding="utf-8")
    print(f"           Kamus data Silver ditulis -> {KELUARAN.relative_to(ROOT)}")


if __name__ == "__main__":
    buat_kamus_data()