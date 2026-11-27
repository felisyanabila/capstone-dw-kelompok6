"""Sambungkan lagi panel Gold (src/gold/panel.py) ke gold.jalankan() di src/gold/__init__.py.

PR #34 menggantikan isi gold.jalankan() sehingga panel_provinsi, panel_lebar, dan pemeriksaan total tidak lagi
ditulis oleh pipeline. Skrip ini hanya MENYISIPKAN dua hal dan tidak mengubah kode lain:
  1. import  : from src.gold import panel as panel_gold
  2. di akhir jalankan(): memanggil panel_gold.jalankan(silver) dan menyertakan tabelnya pada kamus hasil.

Jalankan di folder utama repo, di cabang BARU dari main terbaru:
    py sambung_panel_ke_gold.py

Aman dijalankan ulang; berkas dikembalikan bila uji impor gagal. Alat sekali pakai: JANGAN di-commit.
"""
import re
import subprocess
import sys
from pathlib import Path

BERKAS = Path("src/gold/__init__.py")
IMPOR = "from src.gold import panel as panel_gold"
POLA_RETURN = re.compile(r'(?P<ind>[ ]{4})return \{\s*"panel_melek_aksara": panel,\s*"rekonsiliasi": rekonsiliasi,\s*\}')
RETURN_BARU = '''    # Tahap 4: panel provinsi x periode x indikator (src/gold/panel.py): panel_provinsi, panel_lebar,
    # pemeriksaan total rinci vs ringkas, dan laporan bukti reports/panel_gold.md
    tabel_panel = panel_gold.jalankan(silver)

    return {
        "panel_melek_aksara": panel,
        "rekonsiliasi": rekonsiliasi,
        **tabel_panel,
    }'''


def main():
    if not BERKAS.exists():
        sys.exit("BERHENTI: jalankan dari folder utama repo (src/gold/__init__.py tidak ditemukan)")
    asli = BERKAS.read_bytes()
    crlf = b"\r\n" in asli
    teks = asli.decode("utf-8-sig").replace("\r\n", "\n")
    if IMPOR in teks:
        print("Sudah tersambung; tidak ada yang diubah.")
        return
    if len(POLA_RETURN.findall(teks)) != 1 or "from src.gold.rekonsiliasi import" not in teks:
        sys.exit("BERHENTI: bentuk gold.jalankan() tidak seperti dugaan (berkas sudah diubah orang lain?). Tidak ada yang diubah; kirim isi src/gold/__init__.py ke Claude.")
    baru = re.sub(r"(from src\.gold\.rekonsiliasi import[^\n]*\n)", lambda m: m.group(1) + IMPOR + "\n", teks, count=1)
    baru = POLA_RETURN.sub(lambda m: RETURN_BARU, baru, count=1)
    bom = asli.startswith(b"\xef\xbb\xbf")
    BERKAS.write_bytes((b"\xef\xbb\xbf" if bom else b"") + (baru.replace("\n", "\r\n") if crlf else baru).encode("utf-8"))
    uji = subprocess.run([sys.executable, "-c", "import src.gold as g; assert callable(g.jalankan)"], capture_output=True, text=True)
    if uji.returncode != 0:
        BERKAS.write_bytes(asli)
        sys.exit("BERHENTI: uji impor gagal; src/gold/__init__.py dikembalikan seperti semula.\n" + uji.stderr[-500:])
    print("Tersambung: panel_gold.jalankan(silver) dipanggil di akhir gold.jalankan(), tabelnya ikut dikembalikan.")
    print("Langkah berikut: py pipeline.py, lalu git add src/gold/__init__.py src/gold/panel.py ...")


if __name__ == "__main__":
    main()
