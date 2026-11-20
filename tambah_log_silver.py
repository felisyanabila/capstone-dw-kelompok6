"""Tambahkan keputusan Silver ke log-keputusan.csv dan rapikan satu angka di K-010.

Jalankan dari folder utama repo, SETELAH `git merge origin/main`:
    python tambah_log_silver.py

- ID baru otomatis menyambung dari ID terakhir di log (tidak bentrok dengan rekan).
- Aman dijalankan ulang: keputusan yang sudah ada (teksnya sama) dilewati.
- Alat sekali pakai; TIDAK perlu di-commit.
"""
import csv
import datetime
import io
import re
import sys
from pathlib import Path

NIM = "124450121"
LOG = Path("log-keputusan.csv")

# K-010: angka identik disamakan dengan K-008 (toleransi 0.01 karena data dibulatkan dua desimal).
K010_LAMA = "pada 393 dari 427 pasangan provinsi-tahun, selisih hanya pada 2017"
K010_BARU = "pada 394 dari 427 pasangan provinsi-tahun (toleransi 0.01 seperti K-008; selisih hanya pada 2017)"

BARIS = [
    ("silver", "tabel:sdg4_amh_rinci",
     "kolom rincian Silver tabel rinci dienkode dari daerah x jenis kelamin menjadi sembilan nilai (total, perkotaan, perdesaan, laki-laki, perempuan, perkotaan_laki-laki, perkotaan_perempuan, perdesaan_laki-laki, perdesaan_perempuan); var1458 dan WDI selalu total; kolom tambahan daerah dan jenis_kelamin menyimpan pecahan yang sama (semua, perkotaan, perdesaan; semua, laki-laki, perempuan)",
     "menyimpan label asli BPS (Perkotaan + Perdesaan, Laki-laki+Perempuan) sebagai rincian; menyimpan total saja dan membuang rincian",
     "panduan umum 5.1: total untuk angka keseluruhan dan nama rincian yang konsisten; rincian bagian dari kunci Silver; memilih rincian yang sebanding ditunda ke Gold (Sprint 2)",
     5322),
    ("silver", "semua",
     "baris tanpa nilai tidak masuk Silver: 645 sel tabel rinci bertanda - di HTML (Papua baru sebelum 2024, Kalimantan Utara 2009-2014, DKI Jakarta perdesaan) dan 53 tahun WDI tanpa pengamatan; sel-sel itu tetap terlihat sebagai status di grid (K-004)",
     "menyimpan baris bernilai kosong; mengisi nilai (imputasi)",
     "aturan baku Silver tidak menyimpan baris tanpa nilai dan pemeriksa skema menolak nilai kosong; imputasi sudah ditolak di K-004",
     698),
    ("silver", "var1458;tabel:sdg4_amh_rinci",
     "berkas sumber Silver untuk dua seri BPS adalah CSV pratampil; JSON BPS tidak dimasukkan dan hanya uji silang: JSON var1458 identik dengan CSV pada 427 dari 427 sel; pembaca JSON rinci belum lolos uji silang (6150 baris vs 5967, kolom daerah selalu Perkotaan, baris header ikut terbaca) sehingga belum dipakai",
     "memasukkan CSV dan JSON dengan _berkas_raw masing-masing; menjadikan JSON sumber kanonik",
     "panduan umum 2.1: pilih satu berkas kanonik dan pakai yang lain untuk uji silang; CSV sudah rata dan memuat daerah serta jenis kelamin lengkap; pembaca JSON rinci perlu diperbaiki pemilik ekstraksi sebelum dipakai",
     6577),
    ("silver", "semua",
     "baris Indonesia (9999) tetap ada di Silver: 165 baris BPS (12 var1458 dan 153 tabel rinci) serta 13 baris WDI; pemisahan dari grid provinsi dilakukan di Gold (K-005)",
     "membuang baris Indonesia dari Silver",
     "aturan baku 5.1 memberi kode 9999 untuk Indonesia; rekonsiliasi tahap 6 memerlukan angka nasional BPS dan WDI di tabel yang sama",
     178),
    ("silver", "semua",
     "kategori calon anomali (K-006) ditempel sebagai kolom kategori_anomali pada 463 baris Silver (outlier_asli 441, patahan_metode 13, patahan_wilayah 7, revisi_snapshot 2); kosong untuk baris lain dan untuk WDI; nilai tidak diubah (K-007)",
     "tabel anotasi terpisah di reports/; menghapus atau mengganti nilai yang bertanda",
     "panduan 5.4: outlier asli dan patahan ditandai dengan kolom tambahan, tidak diubah; kolom tambahan diizinkan pemeriksa skema; Gold memerlukan kategori untuk memilih seri yang sebanding",
     463),
]


def main():
    if not LOG.exists():
        sys.exit("BERHENTI: log-keputusan.csv tidak ditemukan; jalankan dari folder utama repo")
    mentah = LOG.read_bytes()
    akhir = "\r\n" if b"\r\n" in mentah else "\n"
    teks = mentah.decode("utf-8")
    diperbaiki = K010_LAMA in teks
    if diperbaiki:
        teks = teks.replace(K010_LAMA, K010_BARU)
    baris = list(csv.DictReader(io.StringIO(teks)))
    sudah = {r["keputusan"] for r in baris}
    nomor = max((int(x) for x in re.findall(r"^K-(\d+),", teks, flags=re.M)), default=0)
    baru = [b for b in BARIS if b[2] not in sudah]
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator=akhir)
    ids = []
    for tahap, seri, keputusan, alt, alasan, dampak in baru:
        nomor += 1
        ids.append(f"K-{nomor:03d}")
        w.writerow([ids[-1], datetime.date.today().isoformat(), NIM, tahap, seri, keputusan, alt, alasan, dampak])
    if teks and not teks.endswith("\n"):
        teks += akhir
    hasil = teks + buf.getvalue()
    cek = list(csv.reader(io.StringIO(hasil)))
    if any(len(r) != 9 for r in cek if r):
        sys.exit("BERHENTI: jumlah kolom tidak 9 setelah penambahan (tidak ada yang diubah)")
    LOG.write_bytes(hasil.encode("utf-8"))
    print(f"K-010 dirapikan: {'ya' if diperbaiki else 'tidak perlu / sudah'}")
    print(f"Baris baru: {len(baru)}" + (f" ({ids[0]} s.d. {ids[-1]})" if baru else " (semua sudah ada)"))
    print(f"Total baris data di log: {len(cek) - 1}; baris milik {NIM}: {sum(1 for r in cek[1:] if r[2] == NIM)}")


if __name__ == "__main__":
    main()
