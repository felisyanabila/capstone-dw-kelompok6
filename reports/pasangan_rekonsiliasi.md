# Pasangan rekonsiliasi dan catatan keterbandingan (persiapan tahap 6)

Dihasilkan oleh `python -m src.gold.nasional` dari `data/silver/silver.parquet`. Semua angka di bawah dihitung dari Silver; jangan diketik tangan.

Konvensi: selisih = nilai seri A dikurangi nilai seri B, dibulatkan 2 desimal, satuan persen. Selisih tidak dihapus dan tidak dipaksa sama.

## Berkas sumber tiap seri (lineage)

- `tabel:sdg4_amh_rinci`: `bps/2026-10-17/sdg4_amh_rinci.csv`
- `var1458`: `bps/2026-10-17/sdg4_amh.csv`
- `SE.ADT.LITR.ZS`: `wdi/2026-10-20/data/kelompok-03-hal-01.json`

## Pasangan

### p1_rinci_vs_var1458: Total tabel rinci vs seri ringkas var1458 (provinsi dan Indonesia)

- Seri A = `tabel:sdg4_amh_rinci`, seri B = `var1458`, rincian = total, cakupan = semua wilayah
- Pasangan yang cocok: 427; berbeda: 34; selisih mutlak maksimum: 1.91; median selisih mutlak (yang berbeda saja): 0.2
- Tahun beririsan (12): 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025
- Tahun yang ada selisihnya: 2017
- Rincian lengkap: `data/gold/rekonsiliasi_p1_rinci_vs_var1458.parquet`

### p2_var1458_vs_wdi: var1458 baris Indonesia vs WDI SE.ADT.LITR.ZS

- Seri A = `var1458`, seri B = `SE.ADT.LITR.ZS`, rincian = total, cakupan = Indonesia (9999)
- Pasangan yang cocok: 5; berbeda: 0; selisih mutlak maksimum: 0.0; median selisih mutlak (yang berbeda saja): 0.0
- Tahun beririsan (5): 2014, 2015, 2016, 2018, 2020
- Tahun yang ada selisihnya: -
- Rincian lengkap: `data/gold/rekonsiliasi_p2_var1458_vs_wdi.parquet`

### p3_rinci_vs_wdi: (tambahan) total tabel rinci baris Indonesia vs WDI, karena rinci mulai 2009

- Seri A = `tabel:sdg4_amh_rinci`, seri B = `SE.ADT.LITR.ZS`, rincian = total, cakupan = Indonesia (9999)
- Pasangan yang cocok: 8; berbeda: 1; selisih mutlak maksimum: 0.59; median selisih mutlak (yang berbeda saja): 0.59
- Tahun beririsan (8): 2009, 2010, 2011, 2014, 2015, 2016, 2018, 2020
- Tahun yang ada selisihnya: 2010
- Rincian lengkap: `data/gold/rekonsiliasi_p3_rinci_vs_wdi.parquet`

## Catatan keterbandingan (sementara, kategori final ditetapkan di Sprint 2)

| Pasangan | Dugaan kategori | Bukti yang masih harus dicari |
|---|---|---|
| p1 | vintage/metode/definisi (belum diketahui) | `manifest_asal.json` kedua tabel BPS; apakah kedua tabel memakai sumber survei dan bobot yang sama; kenapa selisih mengumpul di tahun tertentu |
| p2 | cakupan sama (nasional, 15+); selisih 0 di semua tahun beririsan menunjukkan WDI mungkin bersumber dari BPS | metadata WDI (`metadata/sumber.json`); tahap 7: apakah WDI pernah merevisi angka Indonesia |
| p3 | vintage (rilis WDI berbeda dari BPS) bila ada selisih | arsip WDI tahap 7 |

Catatan: daftar lampiran panduan kelompok menunjukkan semua berkas BPS bertanggal 2026-10-17 dan WDI 2026-10-20. Selisih p1 karena itu perbedaan antar-tabel dalam satu unduhan, bukan revisi antar-tanggal unduh. Periksa `_berkas_raw` di bagian lineage dan samakan istilah dengan `kategori_anomali = revisi_snapshot` di log (K-006, K-008).
