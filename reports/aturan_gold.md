# Aturan satu nilai per sel Gold (Tahap 4, persiapan)

Dibuat oleh `src/gold/aturan.py` (fungsi `pilih_satu_nilai`), dipanggil `src/gold/__init__.py` dan karena itu `pipeline.py`.
Silver boleh punya beberapa baris per sel, Gold tidak boleh. Kunci sel Gold: `wilayah_kode` x `periode` x `rincian`.

## Aturan
| no | aturan | akibat |
|---|---|---|
| 1 | Baris Indonesia (9999) bukan provinsi | tidak masuk panel; dipakai tabel nasional (K-005) |
| 2 | Total provinsi: 2014 sampai 2025 pakai var1458, sebelum 2014 pakai tabel rinci (K-003) | total tabel rinci pada sel yang var1458-nya ada tidak terpilih; selisih dilaporkan |
| 3 | Rincian laki-laki, perempuan, perkotaan, perdesaan, dan gabungannya hanya ada di tabel rinci | seluruhnya masuk panel pada kolom rincian |
| 4 | Periode harus tahunan | periode semesteran atau bulanan menghentikan proses dengan galat |
| 5 | Penanda anomali dibawa ke Gold | penanda dari baris tidak terpilih dipindah ke baris terpilih (prioritas galat_input, revisi_snapshot, patahan_wilayah, patahan_metode, outlier_asli) |

## Hasil pada Silver sekarang
| keterangan | baris |
|---|---|
| baris Silver | 5762 |
| masuk panel provinsi (satu nilai per sel) | 5169 |
| tidak terpilih: nasional_bukan_provinsi | 178 |
| tidak terpilih: total_rinci_digantikan_var1458 | 415 |

Panel memuat 38 kode provinsi dan 9 rincian. Daftar baris Silver yang tidak terpilih:
`reports/gold/baris_silver_tidak_terpilih.csv`.

## Pemeriksaan total rinci vs ringkas
Dari 427 pasangan sel (termasuk Indonesia), 393 sama dan 34 berbeda (tahun 2017).
Selisih dilaporkan, tidak disamakan paksa; nilai yang dipakai Gold adalah var1458. Daftar: `reports/gold/pemeriksaan_total_rinci_vs_ringkas.csv`.

## Penanda anomali di panel
441 sel panel bertanda; 1 di antaranya mewarisi penanda dari baris tabel rinci yang tidak terpilih.

| kategori_anomali | sel_di_panel |
|---|---|
| galat_input | 0 |
| revisi_snapshot | 1 |
| patahan_wilayah | 6 |
| patahan_metode | 13 |
| outlier_asli | 421 |

## Catatan temuan

1. Kenapa var1458 dipilih untuk 2014 sampai 2025. Ia sumber kanonik angka total (K-003). Untuk 415 sel provinsi pada rentang itu, var1458 dan tabel rinci sama-sama ada, jadi 415 baris total tabel rinci tidak terpilih dan tetap disimpan di Silver. Sebelum 2014 hanya tabel rinci yang punya total, sehingga dipakai apa adanya.

2. Isi 593 baris yang tidak terpilih: 415 total tabel rinci yang digantikan var1458, dan 178 baris nasional (Indonesia dari tabel rinci, var1458, dan seri WDI). Nilai nasional tidak dibuang, hanya tidak masuk panel provinsi karena Indonesia bukan provinsi.

3. Koreksi angka selisih. Pemeriksaan total memakai selisih tanpa pembulatan ambang, hasilnya 34 dari 427 sel berbeda, semuanya 2017, bukan 33 seperti di K-003 dan K-008. Perbedaan ini muncul karena DKI Jakarta 2017 berselisih 0,01 (99,67 vs 99,68) dan sebelumnya terbuang oleh ambang. Selisih terbesar Papua 2017 (73,89 vs 75,80). Koreksi dicatat di K-029, baris lama tidak diubah.

4. Penanda anomali. 441 sel panel bertanda: 421 outlier asli, 13 patahan metode, 6 patahan wilayah, 1 revisi snapshot. Satu sel (Nusa Tenggara Barat 2014, total) ditandai patahan metode pada baris tabel rinci tetapi tidak pada var1458; penanda itu dipindahkan ke baris var1458 yang terpilih supaya tidak hilang. Ia ditandai di kolom penanda_dari_baris_lain.

5. Periode. Seluruh 5.762 baris Silver bertahun. Fungsi berhenti dengan galat bila nanti ada periode semesteran atau bulanan, karena agregasinya keputusan yang harus dicatat dulu.

6. Keterbatasan. Aturan ini hanya memilih nilai dan belum menulis panel ke data/gold (tugas panel). Penanda anomali dibawa dari Sprint 1 dan tidak dihitung ulang pada nilai var1458.
