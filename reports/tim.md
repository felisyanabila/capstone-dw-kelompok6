# Laporan tim — <Nama tim>, kasus <NN> <judul kasus>

Satu dokumen bersama, enam bagian. Angka harus dapat ditarik ulang dari `data/silver`, `data/gold`,
dan `log-keputusan.csv` yang sudah di-*commit*.

## Ringkasan
Kasus 06 membahas tingkat melek aksara (SDG 4.6.1) dengan menangani seri data BPS (sdg4_amh_rinci dan var1458) serta seri World Development Indicators (SE.ADT.LITR.ZS). Secara keseluruhan, kualitas data pada lapisan Silver sudah cukup rapi untuk diolah lebih lanjut, namun masih memiliki catatan pada konsistensi wilayah, cakupan periode antar-sumber, dan selisih kecil pada beberapa pasangan perbandingan yang perlu dicermati saat rekonsiliasi.

## Data dan lineage
Sumber dan format mentah, jumlah berkas, cara `_berkas_raw`/`_sha256_raw` dibentuk, dan hasil tarik
ulang API (bila dilakukan): apa yang berubah sejak snapshot 17–20 Oktober 2026.

## Masalah data dan penanganannya
Tabel masalah yang ditemukan (missing, outlier, patahan seri, duplikat, format, wilayah) dengan
jumlah baris terdampak, keputusan, dan alternatif yang ditolak. Rujuk id di `log-keputusan.csv`.

## Integrasi dan rekonsiliasi
Rekonsiliasi Kasus 06 pada lapisan Gold membandingkan seri BPS (tabel:sdg4_amh_rinci dari bps/2026-10-17/sdg4_amh_rinci.csv dan var1458 dari bps/2026-10-17/sdg4_amh.csv) dengan seri WDI (SE.ADT.LITR.ZS dari wdi/2026-10-20/data/kelompok-03-hal-01.json) menggunakan selisih seri A dikurangi seri B dalam persen (dua desimal) tanpa menghapus atau memaksakan kesamaan nilai. Pada pasangan p1_rinci_vs_var1458 (rincian total, seluruh wilayah, 12 tahun beririsan 2014–2025), terdapat 427 pasangan cocok dan 34 pasangan berbeda dengan selisih mutlak maksimum 1,91 serta median 0,2 (tahun berselisih tercatat 2017), yang mencerminkan perbedaan antar-tabel dalam satu tanggal unduhan BPS (2026-10-17) dan selaras dengan istilah revisi_snapshot pada log (K-006 dan K-008) alih-alih revisi antar-tanggal unduh. Pada pasangan p2_var1458_vs_wdi (wilayah Indonesia kode 9999, rincian total, 5 tahun beririsan 2014, 2015, 2016, 2018, dan 2020), seluruh 5 pasangan cocok tanpa selisih (maksimum dan median 0,0), sedangkan pada pasangan tambahan p3_rinci_vs_wdi (wilayah Indonesia kode 9999, rincian total, 8 tahun beririsan 2009–2011, 2014–2016, 2018, dan 2020) tercatat 8 pasangan cocok dan 1 perbedaan sebesar 0,59 pada tahun 2010, sementara bukti lanjutan seperti manifest_asal.json, metadata WDI, dan analisis revisi arsip WDI disiapkan untuk tahap lanjutan.

## Validasi dan reproduksibilitas
Tahap validasi pada alur kerja Kasus 06 mengacu pada pemeriksaan validasi dasar lapisan Silver sebagaimana tercatat pada keputusan K-020 di log-keputusan.csv, serta dilengkapi penghasilan metrik rekonsiliasi pada lapisan Gold (results/124450110/metrics.json) dengan parameter reproduksibilitas seperti seed (0) dan data_hash agar hasil dapat ditelusuri kembali. Untuk rincian aturan lulus/gagal skema validasi, waktu eksekusi python pipeline.py dari nol, serta perbandingan performa pandas terhadap DuckDB atau Dask, bagian ini disiapkan untuk dilengkapi berdasarkan hasil pengujian pipeline dan laporan validasi di repositori. Keterbatasan yang masih tersisa meliputi perlunya verifikasi lanjutan terhadap manifest_asal.json, metadata sumber WDI, dan analisis revisi arsip WDI sebelum penetapan kategori final pada tahap berikutnya.

## Pembagian kerja
| Anggota | NIM | Komponen | Tugas sampingan | Bagian laporan yang ditulis |
|---|---|---|---|---|
