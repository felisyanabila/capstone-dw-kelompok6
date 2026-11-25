# Laporan panel Gold provinsi x periode x indikator (Tahap 4)

Dibuat otomatis oleh `python pipeline.py` (`src/gold/panel.py`); tidak ada langkah tangan. Isinya sengaja tanpa waktu dan nomor commit supaya sama setiap kali pipeline dijalankan.

## 1. Hasil pipeline

- `data/gold/panel_provinsi.parquet`: 5814 baris = 38 provinsi x 17 tahun (2009-2025) x 9 indikator (`amh_<rincian>`).
- `data/gold/panel_lebar.parquet`: 646 baris (provinsi x tahun, satu kolom nilai per indikator).
- `data/gold/pemeriksaan_total_rinci_vs_ringkas.parquet`: 415 pasangan provinsi-tahun; 382 sama, 33 berbeda (periode: 2017), 1 di antaranya dalam toleransi 0,01.
- Status sel: 5169 terisi, 495 belum_ada_wilayah, 99 belum_terbit, 51 tidak_berlaku, 0 missing (aturan K-004).
- Satuan: persen untuk seluruh kolom `nilai`; nilai tidak diubah; rentang 43.12 sampai 99.98.
- Nilai total: var1458 untuk 2014-2025, tabel rinci untuk 2009-2013 (K-003); 415 nilai tabel rinci pada sel yang sama disimpan di `nilai_alternatif`.
- 440 sel membawa `kategori_anomali` dari Silver (K-006); tidak ada sel yang disaring.

## 2. Keunikan kunci

- Kunci panel: `wilayah_kode, periode, indikator`.
- Baris: 5814; kombinasi kunci unik: 5814; kunci kembar: 0.
- Pemeriksaan ini dijalankan di dalam pipeline (`periksa()`); bila ada kunci kembar, pipeline berhenti.

## 3. Keterlacakan baris

- 5169 sel terisi -> tepat satu baris Silver (kunci: sumber, seri_kode, wilayah_kode, periode, rincian, _berkas_raw): nilai, sidik sumber, dan tanda anomali sama.
- 5169 dari 5169 sel terlacak lebih jauh ke satu baris berkas mentah dengan nilai sama (selisih nilai: 0):
  - `bps/2026-10-17/sdg4_amh.csv`: 415 sel
  - `bps/2026-10-17/sdg4_amh_rinci.csv`: 4754 sel
- sha256 setiap berkas mentah dihitung ulang dan sama dengan `data/raw/MANIFEST.csv` dan kolom `_sha256_raw`: ya.
- 645 sel kosong tidak punya baris Silver (memang tidak ada nilai di sumber); statusnya menjelaskan alasannya.

Contoh penelusuran (sel dipilih tetap):

```
Gold    : wilayah 1100 (ACEH), periode 2009, indikator amh_total: nilai 96.39 persen, status terisi
Silver  : bps / tabel:sdg4_amh_rinci / wilayah 1100 / 2009 / total / bps/2026-10-17/sdg4_amh_rinci.csv: nilai 96.39
Mentah  : bps/2026-10-17/sdg4_amh_rinci.csv, baris 121: nilai 96.39
sha256  : b967137b51bafa93c7c557fcb6150514e3ecefb6f6c34100a077eb00b0da286b (dihitung ulang), sama dengan MANIFEST.csv: True
Hasil   : nilai Gold = nilai Silver = nilai berkas mentah
```

```
Gold    : wilayah 1100 (ACEH), periode 2017, indikator amh_total: nilai 97.94 persen, status terisi, nilai_alternatif 98.15 (tabel:sdg4_amh_rinci)
Silver  : bps / var1458 / wilayah 1100 / 2017 / total / bps/2026-10-17/sdg4_amh.csv: nilai 97.94
Mentah  : bps/2026-10-17/sdg4_amh.csv, baris 5: nilai 97.94
sha256  : b35f0b3f6cc4233d2ff22e21e5a076b90ea670d42f4d1af85fdca47487a112b9 (dihitung ulang), sama dengan MANIFEST.csv: True
Hasil   : nilai Gold = nilai Silver = nilai berkas mentah
```

```
Gold    : wilayah 9400 (PAPUA), periode 2024, indikator amh_total: nilai 98.37 persen, status terisi, kategori_anomali patahan_wilayah, nilai_alternatif 98.37 (tabel:sdg4_amh_rinci)
Silver  : bps / var1458 / wilayah 9400 / 2024 / total / bps/2026-10-17/sdg4_amh.csv: nilai 98.37
Mentah  : bps/2026-10-17/sdg4_amh.csv, baris 409: nilai 98.37
sha256  : b35f0b3f6cc4233d2ff22e21e5a076b90ea670d42f4d1af85fdca47487a112b9 (dihitung ulang), sama dengan MANIFEST.csv: True
Hasil   : nilai Gold = nilai Silver = nilai berkas mentah
```

```
Gold    : wilayah 3100 (DKI JAKARTA), periode 2025, indikator amh_perkotaan_perempuan: nilai 99.61 persen, status terisi
Silver  : bps / tabel:sdg4_amh_rinci / wilayah 3100 / 2025 / perkotaan_perempuan / bps/2026-10-17/sdg4_amh_rinci.csv: nilai 99.61
Mentah  : bps/2026-10-17/sdg4_amh_rinci.csv, baris 868: nilai 99.61
sha256  : b967137b51bafa93c7c557fcb6150514e3ecefb6f6c34100a077eb00b0da286b (dihitung ulang), sama dengan MANIFEST.csv: True
Hasil   : nilai Gold = nilai Silver = nilai berkas mentah
```

```
Gold    : wilayah 9200 (PAPUA BARAT DAYA), periode 2023, indikator amh_total: nilai None persen, status belum_terbit
Hasil   : sel kosong (belum_terbit): tidak ada baris Silver maupun baris berkas mentah untuk sel ini
```

```
Gold    : wilayah 3100 (DKI JAKARTA), periode 2020, indikator amh_perdesaan: nilai None persen, status tidak_berlaku
Hasil   : sel kosong (tidak_berlaku): tidak ada baris Silver maupun baris berkas mentah untuk sel ini
```

Menelusuri sel mana pun: `py -m src.gold.panel --telusuri <wilayah_kode> <periode> <indikator>`, misalnya `py -m src.gold.panel --telusuri 9400 2024 amh_total`.

## 4. Metrik

Dihitung pipeline dibandingkan dengan `results/124450121/metrics.json`:

- `seri_silver`: dihitung 3; di metrics.json 3 (cocok)
- `rincian_dienkode`: dihitung 9; di metrics.json 9 (cocok)
- `baris_silver`: dihitung 5762; di metrics.json 5762 (cocok)
- `seri_panel`: dihitung 2; di metrics.json 2 (cocok)
- `baris_gold`: dihitung 5814; di metrics.json 5814 (cocok)
- `keputusan_dicatat`: dihitung 19; di metrics.json 19 (cocok)

Perintah menulis ulang metrics (satu baris, memuat metrik Sprint 1 dan Sprint 2):

```
py -m src.common.hasil 124450121 seri_silver=3 rincian_dienkode=9 baris_silver=5762 seri_panel=2 baris_gold=5814 keputusan_dicatat=19
```
