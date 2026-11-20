"""Pemeriksa integrator untuk tugas #24: apakah `main` memenuhi syarat selesai Sprint 1?

Jalankan di folder utama repo, di cabang main yang sudah ditarik:
    git switch main
    git pull origin main
    py cek_main.py

Hanya MEMBACA dan menjalankan pipeline; tidak mengubah berkas kode. Alat sekali pakai, TIDAK perlu di-commit.
Yang TIDAK bisa diperiksa dari sini: apakah tiap PR sudah di-review (lihat di GitHub).
"""
import csv
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path.cwd()
NIM = {"124450001": "Gathfan", "124450014": "Aqila", "124450104": "Felisya",
       "124450110": "Afriza", "124450121": "Jona"}
WAJIB = ["sumber", "seri_kode", "wilayah_kode", "nama_wilayah", "periode", "jenis_periode",
         "rincian", "nilai", "satuan", "_berkas_raw", "_sha256_raw"]
hasil = []


def jalan(*cmd):
    return subprocess.run(list(cmd), cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")


def catat(nama, ok, rinci=""):
    hasil.append(ok)
    print(f"[{'LULUS' if ok else 'GAGAL'}] {nama}")
    for baris in str(rinci).strip().splitlines():
        print(f"        {baris}")


def main():
    if not (ROOT / "pipeline.py").exists():
        sys.exit("BERHENTI: jalankan dari folder utama repo (tempat pipeline.py berada)")

    # 1. cabang dan kesegaran
    cabang = jalan("git", "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    f = jalan("git", "fetch", "origin")
    if f.returncode == 0:
        tertinggal = jalan("git", "rev-list", "--count", "HEAD..origin/main").stdout.strip()
        catat("berada di main dan sudah sama dengan origin/main", cabang == "main" and tertinggal == "0",
              f"cabang: {cabang}; tertinggal dari origin/main: {tertinggal} commit")
    else:
        catat("berada di main (fetch gagal, kesegaran tidak diperiksa)", cabang == "main", f"cabang: {cabang}")
    kotor = jalan("git", "status", "--porcelain", "--untracked-files=no").stdout.strip()
    catat("tidak ada perubahan yang belum di-commit", not kotor, kotor)

    # 2. berkas milik dosen
    log = [x for x in jalan("git", "log", "--format=%h %an %ad %s", "--date=short", "--", "src/common", "unduh_data.py").stdout.splitlines() if x]
    catat("src/common/ dan unduh_data.py tidak diubah setelah template (maks. 1 commit: commit awal)", len(log) <= 1,
          "commit yang menyentuh berkas itu:\n" + "\n".join(log) if log else "tidak ada riwayat")

    # 3. data mentah tidak ikut git
    dilacak = jalan("git", "ls-files", "data/raw").stdout.strip()
    catat("data/raw/ tidak ikut ter-commit", not dilacak, dilacak[:300])

    # 4. pipeline dari data mentah sampai Silver
    silver = ROOT / "data" / "silver" / "silver.parquet"
    mulai = time.time()
    p = jalan(sys.executable, "pipeline.py")
    detik = time.time() - mulai
    keluar = (p.stdout or "") + (p.stderr or "")
    ditulis = silver.exists() and silver.stat().st_mtime >= mulai - 1
    berhenti_gold = "NotImplementedError" in keluar and "Tahap 4" in keluar
    ok = ditulis and "Silver:" in keluar and (p.returncode == 0 or berhenti_gold)
    catat("python pipeline.py berjalan dari data mentah sampai Silver", ok,
          f"kode keluar: {p.returncode}; {detik:.1f} detik; silver.parquet baru ditulis: {ditulis}"
          + ("\nberhenti di Gold (belum dibuat) setelah Silver selesai, ini masih memenuhi syarat sprint 1" if berhenti_gold and ok else "")
          + ("" if ok else "\n--- 12 baris terakhir keluaran ---\n" + "\n".join(keluar.splitlines()[-12:])))

    # 5. pemeriksa skema resmi
    if silver.exists():
        s = jalan(sys.executable, "-m", "src.common.skema", "data/silver/silver.parquet")
        catat("python -m src.common.skema lolos", s.returncode == 0 and "LOLOS" in s.stdout, (s.stdout + s.stderr).strip()[-400:])
        try:
            import pandas as pd
            df = pd.read_parquet(silver)
            kurang = [c for c in WAJIB if c not in df.columns]
            tambahan = [c for c in df.columns if c not in WAJIB]
            kembar = int(df.duplicated(["sumber", "seri_kode", "wilayah_kode", "periode", "rincian", "_berkas_raw"]).sum())
            catat("kolom wajib lengkap dan kunci Silver tidak kembar", not kurang and kembar == 0,
                  f"{len(df)} baris; kolom tambahan: {', '.join(tambahan) or '-'}; kunci kembar: {kembar}"
                  + (f"; KOLOM WAJIB HILANG: {kurang}" if kurang else "")
                  + "\n(bandingkan kolom tambahan dengan docs/data-dictionary.md)")
        except Exception as e:  # pragma: no cover
            catat("membaca silver.parquet", False, repr(e))
    else:
        catat("python -m src.common.skema lolos", False, "data/silver/silver.parquet tidak ada")

    # 6. metrics.json semua anggota
    ada, hilang = [], []
    for nim, nama in NIM.items():
        j = ROOT / "results" / nim / "metrics.json"
        try:
            d = json.loads(j.read_text(encoding="utf-8"))
            (ada if d.get("metrik") and d.get("data_hash") else hilang).append(f"{nim} ({nama})")
        except Exception:
            hilang.append(f"{nim} ({nama})")
    catat("results/<nim>/metrics.json ada untuk semua anggota", not hilang, "belum ada atau rusak: " + ", ".join(hilang) if hilang else "lima berkas lengkap")

    # 7. log keputusan
    try:
        baris = list(csv.reader((ROOT / "log-keputusan.csv").read_text(encoding="utf-8-sig").splitlines()))
        data = [b for b in baris[1:] if b]
        ids = [b[0] for b in data]
        nomor = [int(re.match(r"K-(\d+)$", i).group(1)) for i in ids]
        salah = []
        if any(len(b) != 9 for b in baris if b): salah.append("ada baris dengan kolom tidak 9")
        if len(set(ids)) != len(ids): salah.append("ID kembar: " + ", ".join(sorted({i for i in ids if ids.count(i) > 1})))
        loncat = [n for n in range(1, max(nomor) + 1) if n not in nomor]
        if loncat: salah.append("ID loncat: " + ", ".join(f"K-{n:03d}" for n in loncat))
        catat("log-keputusan.csv: 9 kolom, ID unik dan berurutan", not salah,
              f"{len(data)} baris, K-001 sampai K-{max(nomor):03d}" + ("\n" + "; ".join(salah) if salah else ""))
    except Exception as e:
        catat("membaca log-keputusan.csv", False, repr(e))

    print(f"\nRingkasan: {sum(hasil)} dari {len(hasil)} pemeriksaan lulus.")
    print("Belum diperiksa skrip ini: tiap PR sudah di-review (cek tab Pull requests di GitHub).")
    return 0 if all(hasil) else 1


if __name__ == "__main__":
    sys.exit(main())
