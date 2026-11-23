# AI_LOG — Aksara Data (Kelompok 6)

Satu baris per pemakaian AI yang bermakna (ChatGPT, Claude, Copilot, Bravais, dan sejenisnya).
Ringkas dan jujur; transkrip penuh tidak diminta. Yang dinilai bukan "pakai AI atau tidak",
melainkan "mengerti atau tidak" — isi kolom terakhir dengan apa yang Anda ubah dari keluarannya.

| Tanggal | Siapa (NIM) | Alat | Untuk apa | Apa yang diubah dari keluarannya |
|---|---|---|---|---|
| 2026-11-03 | 12345678 | Copilot | kerangka DataLoader | ganti normalisasi, tambah seed worker |
| 2026-11-15 | 124450001 | Claude | membantu memahami tugas "Profil dan calon anomali seri utama tabel:sdg4_amh_rinci, var1458" | penjelasan profil_amh.md |
| 2026-11-15 | 124450001 | Claude | membantu memahami dan membuat skrip profil WDI dan draf catatan temuan | mencocokkan angka kunci dengan CSV dan menulis ulang kalimat catatan temuan |
| 2026-11-16 | 124450001 | Claude | grid, kelengkapan panel, kamus wilayah, draf log keputusan | mencocokkan angka kunci dengan CSV, memahami alasan K-002 sampai K-005, mengubah kalimat catatan yang tidak sesuai |
| 2026-11-16 | 124450001 | Claude | kategori anomali dan deduplikasi | mencocokkan angka kunci dengan CSV, memahami alasan K-006 sampai K-008 |
| 2026-11-18 | 124450014 | Gemini | menyusun skema validasi Pandera Silver di src/validasi/__init__.py dan laporan validasi | menyesuaikan pengecekan total kanonik dengan aturan K-003 dan melewati sementara NotImplementedError gold di pipeline.py |
| 2026-11-19 | 124450014 | Gemini | membuat generator kamus data Silver di src/validasi/kamus_data.py dan mengisi docs/data-dictionary.md | mengintegrasikan pembaruan otomatis kamus data ke tahap validasi dan menambahkan contoh penelusuran ke MANIFEST.csv |
| 2026-11-20 | 124450110 | Claude | kerangka skrip tabel nasional dan pasangan rekonsiliasi (src/gold/nasional.py), langkah git dan PowerShell | menjalankan skrip dan mencocokkan angka (p1 427/34, p2 5/0, p3 8/1) dengan profil Gathfan, menambah pembulatan 2 desimal pada nilai WDI, memahami mengapa selisih memakai A minus B, menulis log K-020 sampai K-022 dengan kalimat sendiri |
| 2026-11-20 | 124450110 | Gemini | draf bagian Ringkasan, Integrasi dan rekonsiliasi, serta Validasi dan reproduksibilitas di reports/tim.md | mengecek isi tim.md, menyesuaikan angka rekonsiliasi dengan pasangan_rekonsiliasi.md dan rujukan log-keputusan.csv, serta menandai bagian yang perlu dilengkapi lanjutan |
| 2026-11-23 | 124450001 | Claude | skrip aturan satu nilai per sel Gold (#27), draf baris log tahap gold, draf catatan temuan | Saya menjalankan skrip, memeriksa angkanya terhadap Silver dan laporan validasi, dan menulis ulang catatan temuan dengan bahasa sendiri. Saya mengoreksi angka 33 menjadi 34 setelah menemukan selisih 0,01 DKI Jakarta 2017. |
