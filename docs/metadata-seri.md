# Metadata dan bukti verifikasi katalog seri (Kasus 06)

Dokumen ini dibuat otomatis oleh `python -m src.silver.periksa_katalog --tulis`; jalankan ulang bila berkas mentah atau `katalog.py` berubah.
Katalog awal adalah `data/KASUS.md`. Setiap butir ditetapkan satu nilai dan diberi status: **dikonfirmasi** (ada bukti langsung di berkas mentah), **inferensi** (tidak tertulis di sumber, disimpulkan), atau **diisi** (katalog awal kosong). Alasan lengkap ada di `log-keputusan.csv` (K-009 sampai K-014 dan baris rangkuman sesudahnya). Semua jalur berkas relatif terhadap `data/raw/`.

## var1458 (BPS)

Nama seri: Angka Melek Aksara Penduduk 15 Tahun ke Atas Menurut Provinsi

Katalog awal: satuan persen, kode SDG 4.6.1.

Ditetapkan:

- satuan: **persen** — dikonfirmasi; tertulis 'Persen' di tiga tempat
- kode SDG: **4.6.1** — dikonfirmasi; dasar: katalog awal; penomoran diperiksa ke UIS (K-012)
- jenis periode: **tahun** — dikonfirmasi; periode sumber = Tahun

Bukti di berkas mentah:

- judul: Angka Melek Aksara Penduduk 15 Tahun ke Atas Menurut Provinsi (`bps/2026-10-17/json/sdg4_amh.json` :: `[0].var[0].label`)
- judul: Angka Melek Aksara Penduduk 15 Tahun ke Atas Menurut Provinsi (`bps/2026-10-17/manifest_asal.json` :: `tabel.sdg4_amh.judul`)
- satuan: Persen (`bps/2026-10-17/json/sdg4_amh.json` :: `[0].var[0].unit`)
- satuan: Persen (`bps/2026-10-17/manifest_asal.json` :: `tabel.sdg4_amh.satuan`)
- satuan: Persen (`bps/2026-10-17/sdg4_amh.csv` :: `kolom satuan, 427 baris`)
- periode: Tahun (`bps/2026-10-17/manifest_asal.json` :: `tabel.sdg4_amh.periode`)
- periode: Tahun (`bps/2026-10-17/json/sdg4_amh.json` :: `[0].turtahun[0].label`)
- rentang tahun: 2014-2025 (`bps/2026-10-17/manifest_asal.json` :: `tabel.sdg4_amh.tahun`)
- sumber data: Sumber: BPS, Susenas (`bps/2026-10-17/json/sdg4_amh.json` :: `[0].var[0].note`)
- rentang nilai: 68.32-99.87 (`bps/2026-10-17/sdg4_amh.csv` :: `kolom nilai`)
- kode SDG: tidak ditemukan (`bps/2026-10-17/json/sdg4_amh.json; sdg4_amh.csv; manifest_asal.json` :: `pencarian pola 4.6.x`)

## tabel:sdg4_amh_rinci (BPS)

Nama seri: Angka Melek Aksara Penduduk Umur 15 Tahun ke Atas Menurut Provinsi, Klasifikasi Desa, dan Jenis Kelamin, 2009-2025

Katalog awal: satuan persen, kode SDG 4.6.1.

Ditetapkan:

- satuan: **persen** — inferensi; tidak tertulis di sumber; disimpulkan dari judul, rentang nilai, dan kesamaan dengan var1458 (K-010)
- kode SDG: **4.6.1** — dikonfirmasi; dasar: katalog awal; penomoran diperiksa ke UIS (K-012)
- jenis periode: **tahun** — dikonfirmasi; tahun bilangan bulat 2009-2025

Bukti di berkas mentah:

- judul: Angka Melek Aksara Penduduk Umur 15 Tahun ke Atas Menurut Provinsi, Klasifikasi Desa, dan Jenis Kelamin, 2009-2025 (`bps/2026-10-17/json/sdg4_amh_rinci.json` :: `data.title`)
- judul: Angka Melek Aksara Penduduk Umur 15 Tahun ke Atas Menurut Provinsi, Klasifikasi Desa, dan Jenis Kelamin, 2009-2025 (`bps/2026-10-17/manifest_asal.json` :: `tabel.sdg4_amh_rinci.judul`)
- satuan: tanpa kunci satuan: jenis, table_id, judul, last_update, tahun, baris_ditandai_cek, baris, sha256_json (`bps/2026-10-17/manifest_asal.json` :: `tabel.sdg4_amh_rinci (kunci)`)
- satuan: tanpa field unit: table_id, sub_id, subcsa_id, subcsa, title, cr_date, updt_date, excel, size, mapping, related (`bps/2026-10-17/json/sdg4_amh_rinci.json` :: `data (kunci)`)
- satuan: kata persen / tanda % tidak ditemukan (`bps/2026-10-17/json/sdg4_amh_rinci.json` :: `data.table (teks HTML)`)
- rentang tahun: 2009-2025 (`bps/2026-10-17/manifest_asal.json` :: `tabel.sdg4_amh_rinci.tahun`)
- sumber data: Sumber: BPS, Susenas (`bps/2026-10-17/json/sdg4_amh_rinci.json` :: `data.table (catatan kaki)`)
- rentang nilai: 43.12-99.98 (`bps/2026-10-17/sdg4_amh_rinci.csv` :: `kolom nilai (tanpa sel kosong)`)
- kesamaan dengan var1458: 394 dari 427 pasangan provinsi-tahun sama; selisih hanya pada 2017 (`bps/2026-10-17/sdg4_amh_rinci.csv vs sdg4_amh.csv` :: `total (Perkotaan+Perdesaan, L+P), toleransi 0.01`)
- kode SDG: tidak ditemukan (`bps/2026-10-17/json/sdg4_amh_rinci.json; sdg4_amh_rinci.csv` :: `pencarian pola 4.6.x`)

## SE.ADT.LITR.ZS (WDI)

Nama seri: Literacy rate, adult total (% of people ages 15 and above)

Katalog awal: satuan tidak ada, kode SDG — (kosong).

Ditetapkan:

- satuan: **persen** — diisi; katalog awal tidak punya satuan; diambil dari tanda % pada nama indikator (K-011)
- kode SDG: **4.6.1** — diisi (inferensi); katalog awal '—'; terdaftar di sumber SDG WDI, nomor target tidak tertulis (K-013)
- jenis periode: **tahun** — dikonfirmasi; date empat digit

Bukti di berkas mentah:

- nama: Literacy rate, adult total (% of people ages 15 and above) (`wdi/2026-10-20/metadata/sumber2_indikator.json` :: `indikator SE.ADT.LITR.ZS .name`)
- satuan: '' (kosong) (`wdi/2026-10-20/metadata/sumber2_indikator.json` :: `.unit`)
- satuan: kosong pada semua (`wdi/2026-10-20/data/kelompok-03-hal-01.json` :: `unit pada 66 pengamatan`)
- definisi: Adult literacy rate is the percentage of people ages 15 and above who can both read and write with understanding a short simple statement about their everyday life. (`wdi/2026-10-20/metadata/sumber2_indikator.json` :: `.sourceNote`)
- penyusun asli: UNESCO Institute for Statistics (UIS) (`wdi/2026-10-20/metadata/sumber2_indikator.json` :: `.sourceOrganization (publisher)`)
- keanggotaan SDG: terdaftar di sumber 46: Sustainable Development Goals (`wdi/2026-10-20/metadata/sumber46_indikator.json` :: `.source`)
- kode SDG: tidak ditemukan (`wdi/2026-10-20/metadata/ (dua berkas) dan data/` :: `pencarian pola 4.6.x`)
- periode: empat digit; 1960-2025 (66 pengamatan) (`wdi/2026-10-20/data/kelompok-03-hal-01.json` :: `date`)
- tahun bernilai: 13 tahun (1980-2020) (`wdi/2026-10-20/data/kelompok-03-hal-01.json` :: `value tidak null`)
- rentang nilai: 67.31-96.00 (`wdi/2026-10-20/data/kelompok-03-hal-01.json` :: `value`)

## Rujukan eksternal untuk kode SDG 4.6.1

Berkas mentah BPS dan WDI tidak memuat kode SDG, jadi nomor indikator diperiksa ke sumber penyusunnya:

- UIS, catatan rilis data September 2025 (`https://uis.unesco.org/fr/node/5621729`): setelah keputusan Komisi Statistik PBB April 2025, youth/adult literacy rate menjadi indikator global 4.6.1, dan indikator literasi fungsional dinomori ulang menjadi 4.6.2.
- UIS, *Background information on statistics in the UIS database*, Februari 2026 (`download.uis.unesco.org/bdds/202602`): menyatakan bahwa 4.6.1 (literacy rate) menggantikan indikator literasi fungsional yang kini bernomor 4.6.2.
- UIS, halaman definisi *Youth/adult literacy rate* (`https://uis.unesco.org/node/3297551`): literasi adalah kemampuan membaca dan menulis kalimat pendek yang sederhana tentang kehidupan sehari-hari dengan pemahaman. Ini sepadan dengan `sourceNote` WDI.
- UN SDG Metadata-04-06-01 (`https://unstats.un.org/sdgs/metadata/files/Metadata-04-06-01_NEW.pdf`, diperbarui 2025-07-14): judulnya 4.6.1 Youth/adult literacy rate, tetapi isi definisinya masih literasi fungsional. Hanya judulnya yang dipakai sebagai bukti.

Catatan: sebelum 2025 indikator melek aksara bernomor 4.6.2 (tematik), jadi sumber lama atau data lama dapat memakai nomor itu.
Definisi BPS untuk `var1458` kosong di metadata (`var[0].def` = ''), sehingga perbedaan definisi antara BPS dan WDI baru dapat dibahas di tahap rekonsiliasi.
