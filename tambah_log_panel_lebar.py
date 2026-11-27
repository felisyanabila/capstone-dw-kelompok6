"""Tambahkan keputusan perbaikan panel lebar Gold ke log-keputusan.csv.

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
     "panel_lebar hanya memuat provinsi-tahun yang punya minimal satu nilai (580 baris) dan hanya kolom kunci serta sembilan indikator (tanpa kolom tahun); grid lengkap 646 provinsi-tahun dengan status sel tetap ada di panel_provinsi (5814 baris); menggantikan angka 646 baris di K-023",
     "mempertahankan 646 baris dengan 66 baris tanpa nilai dan kolom tahun; hanya mengubah aturan validasi",
     "validasi.md di main (commit 4f5760e): aturan gold_satuan_satu_per_indikator menghitung kolom tahun sebagai indikator (10 indikator = 9 amh_ + tahun) dan gold_setiap_sel_punya_pasangan_silver memeriksa 646 baris dengan 66 tanpa pasangan Silver (Kalimantan Utara dan empat provinsi Papua baru, K-004); panel lebar adalah bentuk analisis, sedangkan sel kosong beserta statusnya tetap lengkap di panel panjang",
     66),
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
