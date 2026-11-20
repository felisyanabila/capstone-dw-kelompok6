"""Perbaiki pembaca JSON tabel rinci (PR #6) di src/ekstraksi/__init__.py dan catat di log.

Jalankan di folder utama repo, di cabang BARU yang dibuat dari main terbaru:
    git switch main
    git pull origin main
    git switch -c 124450121/perbaikan-pembaca-json
    py terapkan_perbaikan_pembaca.py

Skrip ini hanya mengganti fungsi baca_bps_json_rinci (bagian lain berkas tidak disentuh), menguji hasilnya
terhadap sdg4_amh_rinci.csv, dan mengembalikan berkas semula bila ujinya gagal. Menambah satu baris log
(ID otomatis). Aman dijalankan ulang. Alat sekali pakai: JANGAN di-commit.
"""
import csv
import datetime
import io
import re
import subprocess
import sys
from pathlib import Path

NIM = "124450121"
BERKAS = Path("src/ekstraksi/__init__.py")
LOG = Path("log-keputusan.csv")
PENANDA = "Tabelnya terdiri dari TIGA blok"

FUNGSI_BARU = r'''def baca_bps_json_rinci(raw: Path = RAW) -> pd.DataFrame:
    """Membaca json/sdg4_amh_rinci.json: unescape HTML, lalu ratakan tiga blok header bertingkat.

    Tabelnya terdiri dari TIGA blok baris (Perkotaan, Perdesaan, Perkotaan + Perdesaan). Tiap blok punya tiga
    baris header (Klasifikasi Daerah / Jenis Kelamin / Tahun) yang dikenali dari teks kolom pertama, bukan dari
    nomor baris. Pada baris data, kolom 0 = provinsi, kolom 1 kosong, kolom 2 dst = nilai; sedangkan pada baris
    header Jenis Kelamin dan Tahun, label dimulai di kolom 1. Karena itu label kolom data j diambil dari j - 1.
    """
    berkas = "bps/2026-10-17/json/sdg4_amh_rinci.json"
    with open(raw / berkas, encoding="utf-8") as f:
        payload = json.load(f)

    tabel_html = html.unescape(payload["data"]["table"])
    trs = re.findall(r"<tr[^>]*>(.*?)</tr>", tabel_html, flags=re.S | re.I)

    def _sel(tr_html: str) -> list[str]:
        hasil = []
        for tag_open, isi in re.findall(r"<(t[dh][^>]*)>(.*?)</t[dh]>", tr_html, flags=re.S | re.I):
            teks = re.sub(r"<[^>]+>", " ", isi)
            teks = re.sub(r"\s+", " ", html.unescape(teks).replace("\xa0", " ")).strip()
            m = re.search(r"colspan\s*=\s*['\"]?(\d+)", tag_open, flags=re.I)
            hasil.extend([teks] * (int(m.group(1)) if m else 1))
        return hasil

    matriks = [_sel(tr) for tr in trs]
    baris, daerah, jk, tahun = [], None, None, None
    for i, row in enumerate(matriks):
        if not row or not row[0]:
            continue
        if row[0] == "Provinsi":                      # awal blok: tiga baris header berurutan
            daerah = row[2]
            jk, tahun = matriks[i + 1], matriks[i + 2]
            assert jk[0] == "Jenis Kelamin" and tahun[0] == "Tahun", "susunan header tidak seperti dugaan"
            continue
        if row[0] in ("Jenis Kelamin", "Tahun") or row[0].lower().startswith(("sumber", "catatan", "keterangan", "angka melek")):
            continue
        if daerah is None:
            continue
        for j in range(2, min(len(row), len(jk) + 1)):
            if tahun[j - 1].isdigit():
                baris.append({"wilayah": row[0], "daerah": daerah, "jenis_kelamin": jk[j - 1],
                              "tahun": int(tahun[j - 1]), "nilai": row[j]})

    df = pd.DataFrame(baris)
    return _tempel_lineage(df, berkas, raw=raw)
'''

UJI = r'''
import sys
import pandas as pd
sys.path.insert(0, ".")
import src.ekstraksi as ek
def n(df):
    d = df.copy()
    d["k"] = d["wilayah"].str.upper().str.replace("KEPULAUAN", "KEP.", regex=False)
    d["v"] = pd.to_numeric(d["nilai"].astype(str).replace({"-": None, "": None, "nan": None}), errors="coerce")
    return d
j, c = n(ek.baca_bps_json_rinci()), n(ek.baca_bps_csv_rinci())
kunci = ["k", "daerah", "jenis_kelamin", "tahun"]
x = c.merge(j, on=kunci, how="outer", suffixes=("_c", "_j"), indicator=True)
cocok = (x["_merge"] == "both").all() and ((x["v_c"] == x["v_j"]) | (x["v_c"].isna() & x["v_j"].isna())).all()
ok = len(j) == len(c) == 5967 and not j.duplicated(kunci).any() and bool(cocok)
print(("OK" if ok else "GAGAL"), len(j), "baris JSON;", len(c), "baris CSV;", "kunci kembar", int(j.duplicated(kunci).sum()))
sys.exit(0 if ok else 1)
'''

BARIS_LOG = (
    "ekstraksi", "tabel:sdg4_amh_rinci",
    "pembaca JSON tabel rinci diperbaiki: tiga blok header (Perkotaan, Perdesaan, Perkotaan + Perdesaan) dikenali dari teks kolom pertama, bukan nomor baris, dan label jenis kelamin serta tahun diambil dari kolom data dikurangi satu; hasil 5967 baris identik dengan sdg4_amh_rinci.csv pada 5967 dari 5967 sel (sebelumnya 6150 baris, 4050 kunci kembar, daerah selalu Perkotaan, 1872 sel cocok)",
    "membuang pembaca JSON rinci dan memakai CSV saja; mempertahankan pembaca lama dan menyaring baris kembar di Silver",
    "panduan kelompok 4.2 meminta hasil pembacaan HTML dibandingkan dengan CSV pratampil sebagai uji silang, dan pembaca lama gagal uji itu; tabel HTML (json/sdg4_amh_rinci.json, data.table) terdiri dari tiga blok baris dengan header masing-masing",
    183,
)


def main():
    if not BERKAS.exists():
        sys.exit("BERHENTI: jalankan dari folder utama repo (src/ekstraksi/__init__.py tidak ditemukan)")
    asli = BERKAS.read_bytes()
    crlf = b"\r\n" in asli
    teks = asli.decode("utf-8").replace("\r\n", "\n")
    if PENANDA in teks:
        print("Fungsi sudah versi perbaikan; tidak ada yang diganti.")
    else:
        pola = re.compile(r"^def baca_bps_json_rinci\(.*?(?=^def |\Z)", re.S | re.M)
        if len(pola.findall(teks)) != 1:
            sys.exit("BERHENTI: fungsi baca_bps_json_rinci tidak ditemukan tepat satu kali (tidak ada yang diubah)")
        baru = pola.sub(lambda _: FUNGSI_BARU.rstrip("\n") + "\n\n\n", teks, count=1)
        BERKAS.write_bytes((baru.replace("\n", "\r\n") if crlf else baru).encode("utf-8"))
        uji = subprocess.run([sys.executable, "-c", UJI], capture_output=True, text=True, encoding="utf-8", errors="replace")
        print(uji.stdout.strip() or uji.stderr.strip()[-600:])
        if uji.returncode != 0:
            BERKAS.write_bytes(asli)
            sys.exit("BERHENTI: uji gagal; src/ekstraksi/__init__.py dikembalikan seperti semula")
        print("Fungsi baca_bps_json_rinci diganti dan lolos uji.")

    if LOG.exists():
        mentah = LOG.read_bytes()
        akhir = "\r\n" if b"\r\n" in mentah else "\n"
        isi = mentah.decode("utf-8")
        if BARIS_LOG[2] in isi:
            print("Baris log sudah ada.")
        else:
            nomor = max(int(x) for x in re.findall(r"^K-(\d+),", isi, flags=re.M)) + 1
            buf = io.StringIO()
            csv.writer(buf, lineterminator=akhir).writerow([f"K-{nomor:03d}", datetime.date.today().isoformat(), NIM, *BARIS_LOG])
            if not isi.endswith("\n"):
                isi += akhir
            LOG.write_bytes((isi + buf.getvalue()).encode("utf-8"))
            print(f"Baris log ditambahkan: K-{nomor:03d}")
    print("\nLangkah berikut: git add src/ekstraksi/__init__.py log-keputusan.csv, commit, push, buka PR, minta Felisya dan Gathfan sebagai reviewer.")
    print("Setelah PR ini ter-merge, Felisya membuat ulang metrics-nya: py -m src.common.hasil 124450104 berkas_dibaca=8 baris_mentah=12927 format=2")


if __name__ == "__main__":
    main()
