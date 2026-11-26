# Laporan Validasi Silver & Gold

## Ringkasan Aturan

| Aturan | Status | Keterangan |
|---|---|---|
| `skema_dan_rentang_0_100` | **LOLOS** | lolos (5,762 baris, rentang 43.12-99.98) |
| `keunikan_kunci_silver` | **LOLOS** | 0 duplikat kunci |
| `konsistensi_satuan_seri` | **LOLOS** | 3 seri bersatuan tunggal |
| `satu_total_kanonik_prov_tahun` | **LOLOS** | 580 sel kanonik, 0 ganda |
| `laporan_selisih_rinci_ringkas` | **LOLOS** | 34 dari 427 sel berselisih (tahun ['2017']) |
| `gold_kunci_panel_unik` | **LOLOS** | 0 duplikat kunci (wilayah_kode, periode, indikator, rincian) |
| `gold_satuan_satu_per_indikator` | **LOLOS** | 9 indikator bersatuan tunggal |
| `gold_setiap_sel_punya_pasangan_silver` | **LOLOS** | 580 sel terisi diperiksa, 0 tanpa pasangan Silver |
| `rekonsiliasi_kategori_baris_berpasangan` | **LOLOS** | 432 baris berpasangan diperiksa, 0 kategori kosong/tidak sah |

## Selisih Total Rinci vs Ringkas (`var1458`)

| Kode | Wilayah | Tahun | Total Rinci | Total var1458 | Selisih |
|---|---|---|---:|---:|---:|
| 1100 | ACEH | 2017 | 98.15 | 97.94 | +0.21 |
| 1200 | SUMATERA UTARA | 2017 | 98.96 | 98.89 | +0.07 |
| 1300 | SUMATERA BARAT | 2017 | 98.93 | 98.85 | +0.08 |
| 1400 | RIAU | 2017 | 99.21 | 99.17 | +0.04 |
| 1500 | JAMBI | 2017 | 98.28 | 98.09 | +0.19 |
| 1600 | SUMATERA SELATAN | 2017 | 98.65 | 98.54 | +0.11 |
| 1700 | BENGKULU | 2017 | 98.04 | 97.90 | +0.14 |
| 1800 | LAMPUNG | 2017 | 97.21 | 96.89 | +0.32 |
| 1900 | KEP. BANGKA BELITUNG | 2017 | 97.97 | 97.79 | +0.18 |
| 2100 | KEP. RIAU | 2017 | 98.88 | 98.83 | +0.05 |
| 3100 | DKI JAKARTA | 2017 | 99.68 | 99.67 | +0.01 |
| 3200 | JAWA BARAT | 2017 | 98.38 | 98.23 | +0.15 |
| 3300 | JAWA TENGAH | 2017 | 93.99 | 93.39 | +0.60 |
| 3400 | DI YOGYAKARTA | 2017 | 95.09 | 94.64 | +0.45 |
| 3500 | JAWA TIMUR | 2017 | 92.53 | 91.82 | +0.71 |
| 3600 | BANTEN | 2017 | 97.79 | 97.57 | +0.22 |
| 5100 | BALI | 2017 | 93.59 | 92.90 | +0.69 |
| 5200 | NUSA TENGGARA BARAT | 2017 | 88.53 | 87.14 | +1.39 |
| 5300 | NUSA TENGGARA TIMUR | 2017 | 92.75 | 91.68 | +1.07 |
| 6100 | KALIMANTAN BARAT | 2017 | 93.25 | 92.48 | +0.77 |
| 6300 | KALIMANTAN SELATAN | 2017 | 98.52 | 98.40 | +0.12 |
| 6400 | KALIMANTAN TIMUR | 2017 | 99.04 | 98.96 | +0.08 |
| 6500 | KALIMANTAN UTARA | 2017 | 95.63 | 95.14 | +0.49 |
| 7100 | SULAWESI UTARA | 2017 | 99.73 | 99.76 | -0.03 |
| 7200 | SULAWESI TENGAH | 2017 | 97.83 | 97.69 | +0.14 |
| 7300 | SULAWESI SELATAN | 2017 | 92.53 | 91.65 | +0.88 |
| 7400 | SULAWESI TENGGARA | 2017 | 95.05 | 94.32 | +0.73 |
| 7500 | GORONTALO | 2017 | 98.47 | 98.44 | +0.03 |
| 7600 | SULAWESI BARAT | 2017 | 93.71 | 92.79 | +0.92 |
| 8100 | MALUKU | 2017 | 99.19 | 99.13 | +0.06 |
| 8200 | MALUKU UTARA | 2017 | 98.78 | 98.68 | +0.10 |
| 9100 | PAPUA BARAT | 2017 | 97.38 | 97.16 | +0.22 |
| 9400 | PAPUA | 2017 | 75.80 | 73.89 | +1.91 |
| 9999 | INDONESIA | 2017 | 95.92 | 95.50 | +0.42 |
