# Data dictionary — Kelompok 6 (Kasus 06: Literasi / Angka Melek Aksara)

Satu tabel per keluaran (Silver dan setiap tabel Gold). Isi dari data nyata, bukan dari ingatan: tipe, satuan, rentang, dan jumlah kosong dihitung ulang setiap kali pipeline berjalan (`5,762` baris, `15` kolom).

## `data/silver/silver.parquet`

| Kolom | Tipe | Satuan/format | Boleh kosong | Rentang atau nilai sah | Asal (berkas/aturan) | Keterangan |
|---|---|---|---|---|---|---|
| `sumber` | `str` | – | tidak (0 kosong) | `bps`, `wdi` | nama folder tingkat pertama di `data/raw/` (`K-005`, `K-017`) | Identitas penyedia data sumber (`bps` untuk BPS dan `wdi` untuk World Development Indicators Bank Dunia). |
| `seri_kode` | `str` | – | tidak (0 kosong) | `tabel:sdg4_amh_rinci`, `var1458`, `SE.ADT.LITR.ZS` | nama berkas/katalog BPS & kode indikator WDI (`K-003`, `K-012`, `K-013`, `K-018`) | Kode seri indikator baku: `var1458` & `tabel:sdg4_amh_rinci` (SDG 4.6.1 AMH 15+), serta `SE.ADT.LITR.ZS` (pembanding WDI). |
| `wilayah_kode` | `int64` | kode BPS × 100 (atau `9999`) | tidak (0 kosong) | `1100` – `9999` (39 nilai unik) | peta kode BPS 2 digit × 100 tata 38 provinsi 2025 (`K-001`, `K-002`, `K-005`, `K-018`) | Kode wilayah baku lintas sumber: `9999` untuk nasional Indonesia dan `1100`–`9700` untuk 38 provinsi. |
| `nama_wilayah` | `str` | – | tidak (0 kosong) | 39 nilai unik (mis. `ACEH`, `SUMATERA UTARA`, `INDONESIA`) | master nama wilayah `var1458` & label `Indonesia` WDI (`K-002`, `K-005`) | Nama provinsi atau negara yang telah dinormalisasi ejaan dan kapitalisasinya. |
| `periode` | `str` | `YYYY` (4 digit tahun) | tidak (0 kosong) | 22 nilai unik (mis. `2009`, `2010`, `2008`) | kolom tahun `var1458`, header tahun tabel rinci, & field `date` WDI (`K-014`, `K-015`) | Tahun pengamatan indikator (cakupan WDI 1980–2024 dan BPS 2009–2025). |
| `jenis_periode` | `str` | – | tidak (0 kosong) | `tahun` | konstanta penyeragaman frekuensi (`K-014`) | Granularitas waktu pengamatan; seluruh baris Silver berfrekuensi tahunan (`tahun`). |
| `rincian` | `str` | – | tidak (0 kosong) | `laki-laki`, `perdesaan`, `perdesaan_laki-laki`, `perdesaan_perempuan`, `perempuan`, `perkotaan`, `perkotaan_laki-laki`, `perkotaan_perempuan`, `total` | hasil enkode daerah × jenis kelamin tabel rinci; `total` untuk `var1458` & WDI (`K-015`) | Disagregasi demografis/spasial (`total`, `perkotaan`, `perdesaan`, `laki-laki`, `perempuan`, dan kombinasinya). |
| `nilai` | `float64` | `persen` (`0–100`) | tidak (0 kosong) | `43.12` – `99.98` | angka pengamatan mentah tanpa imputasi maupun winsorizing (`K-007`, `K-008`, `K-016`, `K-019`) | Persentase angka melek aksara penduduk usia 15 tahun ke atas. |
| `satuan` | `str` | – | tidak (0 kosong) | `persen` | penyeragaman label `Persen` / satuan implisit tabel rinci / unit WDI (`K-009`, `K-010`, `K-011`) | Satuan pengukuran baku (`persen`) untuk seluruh seri pada tabel Silver. |
| `_berkas_raw` | `str` | path relatif `data/raw/` | tidak (0 kosong) | `bps/2026-10-17/sdg4_amh_rinci.csv`, `bps/2026-10-17/sdg4_amh.csv`, `wdi/2026-10-20/data/kelompok-03-hal-01.json` | jejak berkas sumber pada `data/raw/MANIFEST.csv` (`K-008`, `K-017`) | Jalur relatif berkas mentah asal baris data; menjadi bagian kunci unik Silver. |
| `_sha256_raw` | `str` | hex 64 karakter | tidak (0 kosong) | `b967137b51bafa93c7c557fcb6150514e3ecefb6f6c34100a077eb00b0da286b`, `b35f0b3f6cc4233d2ff22e21e5a076b90ea670d42f4d1af85fdca47487a112b9`, `7b649c5de4bbceb93fa223984c3cdf47bd48a58155c17f7f7125115cdc6500c3` | hash SHA-256 berkas sumber pada `data/raw/MANIFEST.csv` (`src/common/manifest.py`) | Sidik jari kriptografis berkas mentah untuk verifikasi integritas dan keterlacakan data. |
| `kode_sdg` | `str` | – | tidak (0 kosong) | `4.6.1` | olahan Silver | Kolom tabel Silver. |
| `daerah` | `str` | – | tidak (0 kosong) | `semua`, `perdesaan`, `perkotaan` | olahan Silver | Kolom tabel Silver. |
| `jenis_kelamin` | `str` | – | tidak (0 kosong) | `laki-laki`, `semua`, `perempuan` | olahan Silver | Kolom tabel Silver. |
| `kategori_anomali` | `str` | – | ya (5,299 kosong) | `outlier_asli`, `patahan_metode`, `revisi_snapshot`, `patahan_wilayah` | deteksi calon anomali di `src/silver/anomali_amh.py` (`K-006`, `K-007`, `K-019`) | Label diagnostik calon anomali (`outlier_asli`, `patahan_metode`, `patahan_wilayah`, `revisi_snapshot`) tanpa mengubah `nilai`. |

### Contoh Penelusuran Satu Baris Silver ke Berkas Mentah (`data/raw/`)

Setiap baris pada `data/silver/silver.parquet` dapat ditelusuri kembali ke berkas sumber aslinya di `data/raw/` melalui pasangan kolom `_berkas_raw` dan `_sha256_raw`:

1. **Contoh baris pada `data/silver/silver.parquet`:**
   - `sumber`: `bps`
   - `seri_kode`: `tabel:sdg4_amh_rinci`
   - `wilayah_kode`: `1100` (`ACEH`)
   - `periode`: `2009` (`tahun`)
   - `rincian`: `laki-laki`
   - `nilai`: `97.95` `persen`
   - `kategori_anomali`: `kosong (normal)`
   - `_berkas_raw`: `bps/2026-10-17/sdg4_amh_rinci.csv`
   - `_sha256_raw`: `b967137b51bafa93c7c557fcb6150514e3ecefb6f6c34100a077eb00b0da286b`

2. **Verifikasi pada `data/raw/MANIFEST.csv`:**
   - Entri `berkas`: `bps/2026-10-17/sdg4_amh_rinci.csv`
   - Ukuran `bait`: `310,753` bait
   - Nilai `sha256`: `b967137b51bafa93c7c557fcb6150514e3ecefb6f6c34100a077eb00b0da286b` (**cocok identik** dengan `_sha256_raw`)

3. **Lokasi sel pada berkas mentah:**
   - Buka berkas `data/raw/bps/2026-10-17/sdg4_amh_rinci.csv`, cari baris wilayah `ACEH` (kode BPS `11`), lalu baca kolom tahun `2009` sehingga diperoleh nilai mentah `97.95` (satuan asli `Persen` sebelum dinormalisasi menjadi `persen` sesuai `K-009`).

## `data/gold/<tabel>.parquet`

*Akan dilengkapi pada Sprint 2–3 setelah pembentukan tabel Gold.*

| Kolom | Tipe | Satuan/format | Boleh kosong | Rentang atau nilai sah | Asal (berkas/aturan) | Keterangan |
|---|---|---|---|---|---|---|
