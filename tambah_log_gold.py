"""Tambahkan keputusan panel Gold (Tahap 4) ke log-keputusan.csv.

Jalankan di folder utama repo, SETELAH git pull origin main di cabang barumu:
    py tambah_log_gold.py

ID baru otomatis menyambung dari ID terakhir; aman dijalankan ulang (keputusan yang sudah ada dilewati).
Alat sekali pakai: JANGAN di-commit.
"""
import csv
import datetime
import io
import re
import sys
from pathlib import Path

NIM = "124450121"
LOG = Path("log-keputusan.csv")

BARIS = [
    ("var1458;tabel:sdg4_amh_rinci",
     "panel Gold dibentuk sebagai grid lengkap 38 provinsi x 17 tahun (2009-2025) x 9 indikator = 5814 baris (data/gold/panel_provinsi.parquet); indikator = angka melek aksara menurut rincian (amh_total, amh_perkotaan, ..., amh_perdesaan_perempuan) sehingga kunci (wilayah_kode, periode, indikator) unik; sel kosong tetap menjadi baris bernilai kosong dengan status_sel dari aturan K-004 (495 belum_ada_wilayah, 99 belum_terbit, 51 tidak_berlaku, 0 missing); panel lebar 646 baris (provinsi x tahun, satu kolom per indikator) diturunkan tanpa nilai baru",
     "panel hanya berisi sel terisi (5169 baris); var1458 dan tabel rinci sebagai dua indikator terpisah dengan rincian sebagai kunci tambahan; mengisi sel kosong",
     "panduan umum 5.4 dan 5.5: grid lengkap dibentuk sebelum membahas missing dan rincian dienkode konsisten; satu indikator pada satu kunci menghindari dua angka untuk sel yang sama; status sel memakai fungsi status_sel tahap 3 (grid_amh.py) sehingga sama dengan grid Gathfan pada 5168 sel rincian non-total",
     645),
    ("var1458;tabel:sdg4_amh_rinci",
     "nilai total panel: var1458 untuk 2014-2025 dan tabel rinci untuk 2009-2013 (K-003); semua rincian lain dari tabel rinci; total tabel rinci 2014-2025 pada sel yang sama disimpan di kolom nilai_alternatif (415 sel provinsi-tahun), tidak dibuang atau dirata-ratakan (K-008)",
     "tabel rinci sebagai sumber total; dua baris untuk satu sel; merata-ratakan keduanya",
     "K-003 dan K-008 sudah menetapkan var1458 sebagai angka total analisis dan menyimpan kedua nilai; panel butuh satu angka per kunci, jejak revisi 2017 tetap terlihat lewat nilai_alternatif dan tabel pemeriksaan",
     415),
    ("semua",
     "baris Indonesia (9999) tidak masuk panel provinsi: 178 baris Silver (165 BPS dan 13 WDI) tetap di Silver dan dipakai di tabel nasional dan rekonsiliasi",
     "memasukkan 9999 sebagai wilayah ke-39 di panel provinsi",
     "K-005: nilai nasional bukan provinsi dan akan menggeser rata-rata dan sebaran provinsi",
     178),
    ("var1458;tabel:sdg4_amh_rinci",
     "satu kolom nilai bersatuan persen; panel tidak mengubah angka (tanpa konversi satuan, normalisasi, atau transformasi) dan pipeline berhenti bila Silver memuat lebih dari satu satuan untuk seri utama",
     "menambah versi ternormalisasi atau terstandar di panel",
     "satuan seri utama sudah tunggal (persen, K-009 dan K-010) dan nilai 0-100 sudah sebanding antarprovinsi; hanya versi asli yang disimpan",
     0),
    ("semua",
     "kategori_anomali Silver ikut ke panel apa adanya (440 sel panel bertanda); nilai bertanda tetap berada di panel dan tidak disaring",
     "menyaring baris bertanda dari panel; mengganti nilai bertanda",
     "K-006 dan K-007: outlier asli dan patahan ditandai dan dijelaskan, bukan dibuang; Gold menyimpan tandanya supaya analisis dapat memilih",
     440),
    ("var1458;tabel:sdg4_amh_rinci",
     "tabel pemeriksaan total rinci vs ringkas (provinsi, 2014-2025, 415 pasangan) melaporkan selisih tanpa menyamakan paksa: 382 sama dan 33 berbeda (semuanya 2017); kolom dalam_toleransi_0_01 menandai satu sel (DKI Jakarta, selisih 0.01) sehingga ada 32 beda di atas toleransi pembulatan",
     "satu angka ringkas tanpa tabel pemeriksaan; hanya memakai toleransi tanpa selisih persis",
     "menyelaraskan hitungan yang berbeda di PR dan log: 34 sel persis (33 provinsi dan Indonesia) dan 33 sel di atas toleransi 0.01 (32 provinsi dan Indonesia, K-008); bedanya hanya toleransi dan cakupan Indonesia",
     33),
]


def main():
    if not LOG.exists():
        sys.exit("BERHENTI: log-keputusan.csv tidak ditemukan; jalankan dari folder utama repo")
    mentah = LOG.read_bytes()
    akhir = "\r\n" if b"\r\n" in mentah else "\n"
    teks = mentah.decode("utf-8")
    baris = list(csv.reader(io.StringIO(teks)))
    if not baris or baris[0][:1] != ["id"] or any(len(b) != 9 for b in baris if b):
        sys.exit("BERHENTI: format log tidak dikenali (tidak ada yang diubah)")
    sudah = {b[5] for b in baris[1:] if b}
    nomor = max(int(re.match(r"K-(\d+)", b[0]).group(1)) for b in baris[1:] if b)
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator=akhir)
    ids = []
    for seri, keputusan, alt, alasan, dampak in BARIS:
        if keputusan in sudah:
            continue
        nomor += 1
        ids.append(f"K-{nomor:03d}")
        w.writerow([ids[-1], datetime.date.today().isoformat(), NIM, "gold", seri, keputusan, alt, alasan, dampak])
    if teks and not teks.endswith("\n"):
        teks += akhir
    hasil = teks + buf.getvalue()
    cek = list(csv.reader(io.StringIO(hasil)))
    if any(len(r) != 9 for r in cek if r):
        sys.exit("BERHENTI: jumlah kolom tidak 9 setelah penambahan (tidak ada yang diubah)")
    LOG.write_bytes(hasil.encode("utf-8"))
    print(f"Baris baru: {len(ids)}" + (f" ({ids[0]} s.d. {ids[-1]})" if ids else " (semua sudah ada)"))
    print(f"Baris milik {NIM} di log: {sum(1 for r in cek[1:] if r and r[2] == NIM)}  <- pakai angka ini untuk keputusan_dicatat")


if __name__ == "__main__":
    main()
