"""Revisi tugas #16: lengkapi alasan K-009..K-014 dengan bukti yang dapat ditelusuri dan tambah baris rangkuman.

Jalankan dari folder utama repo, SETELAH `git merge origin/main`:
    python revisi_log_katalog.py

- Hanya mengubah kolom alasan baris K-009..K-014 milik 124450121; kolom lain dan baris lain tidak disentuh.
- Menambah satu baris rangkuman dengan ID berikutnya (tidak bentrok dengan rekan).
- Aman dijalankan ulang. Alat sekali pakai; TIDAK perlu di-commit.
"""
import csv
import datetime
import io
import re
import sys
from pathlib import Path

NIM = "124450121"
LOG = Path("log-keputusan.csv")

ALASAN = {
    "K-009": "Katalog awal (data/KASUS.md): persen. Bukti di data/raw: bps/2026-10-17/json/sdg4_amh.json var[0].unit = 'Persen'; bps/2026-10-17/manifest_asal.json tabel.sdg4_amh.satuan = 'Persen'; kolom satuan sdg4_amh.csv = 'Persen' pada 427 dari 427 baris; rentang nilai 68.32-99.87. Status: katalog dikonfirmasi, hanya penulisan dinormalkan ke huruf kecil. Bukti lengkap: docs/metadata-seri.md.",
    "K-010": "Katalog awal: persen. Sumber tidak menyebut satuan: manifest_asal.json tabel.sdg4_amh_rinci hanya berisi jenis, table_id, judul, last_update, tahun, baris_ditandai_cek, baris, sha256_json; json/sdg4_amh_rinci.json data tidak punya field unit; teks tabel HTML tidak memuat kata persen atau tanda %. Nilai katalog dipertahankan lewat bukti tidak langsung: judul (data.title) 'Angka Melek Aksara Penduduk Umur 15 Tahun ke Atas ...'; nilai 43.12-99.98; total rinci identik dengan var1458 (satuan Persen) pada 394 dari 427 pasangan (toleransi 0.01 seperti K-008; selisih hanya pada 2017). Status: dikonfirmasi secara inferensi. Bukti lengkap: docs/metadata-seri.md.",
    "K-011": "Katalog awal (data/KASUS.md) tidak punya kolom satuan untuk WDI. Bukti: wdi/2026-10-20/metadata/sumber2_indikator.json indikator SE.ADT.LITR.ZS: unit = '' (kosong), name = 'Literacy rate, adult total (% of people ages 15 and above)'; unit juga kosong pada 66 pengamatan di data/kelompok-03-hal-01.json; nilai 67.31-96.00. Satuan diambil dari tanda % pada nama indikator. Status: satuan diisi. Bukti lengkap: docs/metadata-seri.md.",
    "K-012": "Katalog awal: 4.6.1. Berkas mentah BPS tidak memuat kode SDG (pola 4.6.x tidak ditemukan di berkas BPS), jadi dasar kode adalah data/KASUS.md. Penomoran diperiksa ke penyusunnya: UIS, catatan rilis data September 2025 (uis.unesco.org/fr/node/5621729): setelah keputusan Komisi Statistik PBB April 2025, youth/adult literacy rate menjadi indikator global 4.6.1 dan literasi fungsional dinomori ulang 4.6.2; UIS Data Release Background Doc Februari 2026 (download.uis.unesco.org/bdds/202602) menyatakan hal yang sama. UN SDG Metadata-04-06-01 (diperbarui 2025-07-14) berjudul 4.6.1 Youth/adult literacy rate tetapi isi definisinya masih literasi fungsional, sehingga hanya judulnya yang dipakai. Status: kode dikonfirmasi; sebelum 2025 indikator yang sama bernomor 4.6.2.",
    "K-013": "Katalog awal: kode SDG kosong ('—'). Bukti: wdi/2026-10-20/metadata/sumber46_indikator.json (sumber 46, Sustainable Development Goals) mendaftarkan SE.ADT.LITR.ZS; sourceNote di sumber2_indikator.json mendefinisikan angka melek aksara penduduk 15 tahun ke atas (penyusun UNESCO UIS), sepadan dengan definisi UIS untuk youth/adult literacy rate (uis.unesco.org/node/3297551) yang kini bernomor 4.6.1 (K-012). Berkas WDI tidak mencantumkan nomor target, jadi 4.6.1 adalah inferensi tim. Status: kode diisi (inferensi).",
    "K-014": "Bukti: bps/2026-10-17/manifest_asal.json tabel.sdg4_amh.periode = ['Tahun'] dan json/sdg4_amh.json turtahun[0].label = 'Tahun'; tabel rinci: tahun bilangan bulat 2009-2025 (manifest_asal.json tabel.sdg4_amh_rinci.tahun); WDI: date empat digit pada 66 pengamatan (1960-2025). Tidak ada seri semesteran atau bulanan sehingga tidak ada periode yang diagregasi. Status: dikonfirmasi.",
}
RANGKUMAN = (
    "silver", "semua",
    "hasil pemeriksaan katalog awal terhadap metadata sumber (revisi #16): 2 butir diisi (satuan WDI, kode SDG WDI), 4 butir dikonfirmasi (satuan dan kode SDG var1458, kode SDG tabel rinci, satuan tabel rinci secara inferensi); judul dan jenis periode ketiga seri cocok; bukti per seri ada di docs/metadata-seri.md dan dapat dijalankan ulang dengan python -m src.silver.periksa_katalog",
    "mencatat hanya butir yang dikoreksi tanpa butir yang dikonfirmasi",
    "catatan dosen pada #16: sumber metadata tiap seri harus ditunjukkan dan seluruh koreksi katalog harus tercatat dengan alasan yang dapat ditelusuri; butir yang dikonfirmasi ikut dicatat agar terlihat bahwa seluruh katalog sudah diperiksa",
    0,
)


def main():
    if not LOG.exists():
        sys.exit("BERHENTI: log-keputusan.csv tidak ditemukan; jalankan dari folder utama repo")
    mentah = LOG.read_bytes()
    akhir = "\r\n" if b"\r\n" in mentah else "\n"
    teks = mentah.decode("utf-8")
    baris = list(csv.reader(io.StringIO(teks)))
    if not baris or baris[0][:1] != ["id"] or any(len(b) != 9 for b in baris if b):
        sys.exit("BERHENTI: format log tidak dikenali (tidak ada yang diubah)")
    ada = {b[0]: b for b in baris[1:] if b}
    kurang = [k for k in ALASAN if k not in ada]
    if kurang:
        sys.exit(f"BERHENTI: {', '.join(kurang)} tidak ada di log; jalankan git merge origin/main dulu")
    salah_nim = [k for k in ALASAN if ada[k][2] != NIM]
    if salah_nim:
        sys.exit(f"BERHENTI: {', '.join(salah_nim)} bukan milik {NIM}; baris orang lain tidak diubah")
    diubah = 0
    for b in baris[1:]:
        if b and b[0] in ALASAN and b[7] != ALASAN[b[0]]:
            b[7] = ALASAN[b[0]]
            diubah += 1
    ada_rangkuman = any(b[5] == RANGKUMAN[2] for b in baris[1:] if b)
    if not ada_rangkuman:
        nomor = max(int(re.match(r"K-(\d+)", b[0]).group(1)) for b in baris[1:] if b) + 1
        baris.append([f"K-{nomor:03d}", datetime.date.today().isoformat(), NIM, RANGKUMAN[0], RANGKUMAN[1],
                      RANGKUMAN[2], RANGKUMAN[3], RANGKUMAN[4], RANGKUMAN[5]])
    buf = io.StringIO()
    csv.writer(buf, lineterminator=akhir).writerows(baris)
    LOG.write_bytes(buf.getvalue().encode("utf-8"))
    print(f"Alasan diperbarui: {diubah} baris (K-009..K-014)")
    print("Baris rangkuman:", "sudah ada" if ada_rangkuman else f"ditambahkan sebagai {baris[-1][0]}")


if __name__ == "__main__":
    main()
