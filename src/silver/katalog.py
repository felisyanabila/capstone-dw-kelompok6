"""Katalog seri hasil pemeriksaan terhadap berkas mentah (Tahap 4, persiapan).

Satu satuan dan satu kode SDG per seri, beserta sumber penetapannya. Rujuk log-keputusan.csv
(K-009 s.d. K-014). Dipakai Silver untuk mengisi kolom `satuan` dan menamai seri.
"""

KATALOG = {
    ("bps", "var1458"): {
        "nama": "Angka Melek Aksara Penduduk 15 Tahun ke Atas Menurut Provinsi",
        "satuan": "persen", "kode_sdg": "4.6.1", "jenis_periode": "tahun",
        "sumber_satuan": "bps/2026-10-17/json/sdg4_amh.json var.unit; manifest_asal.json satuan (K-009)",
        "sumber_sdg": "data/KASUS.md; diperiksa terhadap UIS Feb 2026 (K-012)",
    },
    ("bps", "tabel:sdg4_amh_rinci"): {
        "nama": "Angka Melek Aksara Penduduk Umur 15 Tahun ke Atas Menurut Provinsi, "
                "Klasifikasi Desa, dan Jenis Kelamin, 2009-2025",
        "satuan": "persen", "kode_sdg": "4.6.1", "jenis_periode": "tahun",
        "sumber_satuan": "inferensi: total identik dengan var1458 (toleransi 0.01) pada 394 dari 427 pasangan (K-010)",
        "sumber_sdg": "data/KASUS.md; diperiksa terhadap UIS Feb 2026 (K-012)",
    },
    ("wdi", "SE.ADT.LITR.ZS"): {
        "nama": "Literacy rate, adult total (% of people ages 15 and above)",
        "satuan": "persen", "kode_sdg": "4.6.1", "jenis_periode": "tahun",
        "sumber_satuan": "wdi/2026-10-20/metadata/sumber2_indikator.json name (K-011)",
        "sumber_sdg": "inferensi dari sourceNote WDI/UIS; tidak ada di berkas mentah (K-013)",
    },
}
