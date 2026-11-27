"""Pemeriksa integrator Sprint 2: apakah main memenuhi 'python pipeline.py lolos sampai validasi'?

Jalankan di folder utama repo, di cabang main yang sudah ditarik:
    git switch main
    git pull origin main
    py cek_main_sprint2.py

Hanya MEMBACA dan menjalankan pipeline. Alat sekali pakai: JANGAN di-commit.
Tidak dapat memeriksa apakah tiap PR sudah di-review (lihat tab Pull requests di GitHub).
"""
import csv
import datetime
import json
import re
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path.cwd()
NIM = {"124450001": "Gathfan", "124450014": "Aqila", "124450104": "Felisya", "124450110": "Afriza", "124450121": "Jona"}
GOLD_WAJIB = ["panel_provinsi", "panel_lebar", "pemeriksaan_total_rinci_vs_ringkas"]   # tabel panel (tahap 4)
hasil, catatan, gagal_nama, blok = [], [], [], {}


def jalan(*cmd):
    return subprocess.run(list(cmd), cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")


def catat(nama, ok, rinci=""):
    hasil.append(ok)
    if not ok:
        gagal_nama.append(nama)
    print(f"[{'LULUS' if ok else 'GAGAL'}] {nama}")
    for b in str(rinci).strip().splitlines():
        print(f"        {b}")


def info(nama, rinci=""):
    catatan.append(nama)
    print(f"[CATATAN] {nama}")
    for b in str(rinci).strip().splitlines():
        print(f"        {b}")


def main():
    if not (ROOT / "pipeline.py").exists():
        sys.exit("BERHENTI: jalankan dari folder utama repo (tempat pipeline.py berada)")

    print("== keadaan repo")
    cabang = jalan("git", "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    if jalan("git", "fetch", "origin").returncode == 0:
        ts = jalan("git", "rev-list", "--count", "HEAD..origin/main").stdout.strip()
        catat("berada di main dan sama dengan origin/main", cabang == "main" and ts == "0", f"cabang: {cabang}; tertinggal: {ts} commit")
    else:
        catat("berada di main (fetch gagal, kesegaran tidak diperiksa)", cabang == "main", f"cabang: {cabang}")
    blok["commit"] = jalan("git", "log", "-1", "--oneline").stdout.strip() or "tidak diketahui"
    blok["cabang"] = cabang
    kotor = jalan("git", "status", "--porcelain", "--untracked-files=no").stdout.strip()
    catat("tidak ada perubahan yang belum di-commit", not kotor, kotor)
    log = [x for x in jalan("git", "log", "--format=%h %an %ad %s", "--date=short", "--", "src/common", "unduh_data.py").stdout.splitlines() if x]
    catat("src/common/ dan unduh_data.py tidak diubah setelah template (maks. 1 commit)", len(log) <= 1, "\n".join(log) if len(log) > 1 else "")
    catat("data/raw/ tidak ikut ter-commit", not jalan("git", "ls-files", "data/raw").stdout.strip())
    terlacak = [f for f in jalan("git", "ls-files", "data").stdout.splitlines() if f.endswith((".db", ".sqlite", ".sqlite3"))]
    if terlacak:
        info("basis data SQL ikut ter-commit (dibangun ulang pipeline; berkas biner rawan konflik antar PR)", "\n".join(terlacak))

    print("\n== python pipeline.py")
    mulai = time.time()
    p = jalan(sys.executable, "pipeline.py")
    detik = time.time() - mulai
    keluar = (p.stdout or "") + (p.stderr or "")
    m = re.search(r"Validasi: (\d+)/(\d+) aturan lolos", keluar)
    ok = p.returncode == 0 and bool(m) and m.group(1) == m.group(2)
    catat("pipeline selesai sampai validasi tanpa galat (kode keluar 0, semua aturan validasi lolos)", ok,
          f"kode keluar {p.returncode}; {detik:.1f} detik" + (f"; validasi {m.group(1)}/{m.group(2)}" if m else "; baris 'Validasi' tidak ditemukan")
          + ("" if ok else "\n--- baris GAGAL dari keluaran pipeline ---\n" + "\n".join(b.strip() for b in keluar.splitlines() if "GAGAL" in b)
             + "\n--- 25 baris terakhir ---\n" + "\n".join(keluar.splitlines()[-25:])))
    dilewati = [b.strip() for b in keluar.splitlines() if "dilewati" in b.lower()]
    blok.update(validasi=(f"{m.group(1)}/{m.group(2)} aturan lolos" if m else "tidak ada"), selesai=ok, dilewati=dilewati, detik=detik,
                penting=[b.strip() for b in keluar.splitlines() if re.match(r"\s*(Silver|Gold|Rekonsiliasi|SQL|Validasi|Pipeline selesai)\b", b)])
    catat("tidak ada tahap yang dilewati", not dilewati, "\n".join(dilewati))
    catat("berjalan kurang dari 15 menit", detik < 900, f"{detik:.1f} detik")

    print("\n== keluaran Gold dan rekonsiliasi")
    semua = sorted((f for f in (ROOT / "data" / "gold").glob("*.parquet") if f.stat().st_mtime >= mulai - 1), key=lambda f: f.name)
    info("tabel Gold yang ditulis pipeline pada jalan ini", "\n".join(f.name for f in semua) or "(tidak ada)")
    blok["gold"] = [f.name for f in semua]
    panel_file = [f for f in semua if "panel" in f.name]
    nas = [f for f in semua if "nasional" in f.name]
    rek = [f for f in semua if "rekonsiliasi" in f.name]
    blok["rekonsiliasi"], blok["nasional"] = [f.name for f in rek], [f.name for f in nas]
    catat("tabel panel Gold ditulis oleh pipeline", bool(panel_file), ", ".join(f.name for f in panel_file) or "tidak ada berkas *panel*.parquet yang ditulis pipeline")
    catat("tabel rekonsiliasi (pasangan seri utama vs pembanding) ditulis oleh pipeline", bool(rek),
          ", ".join(f.name for f in rek) if rek else "tidak ada berkas *rekonsiliasi*.parquet yang ditulis pipeline; syarat sprint meminta tabel rekonsiliasi")
    if not nas:
        info("tidak ada tabel nasional yang ditulis pipeline (tidak disebut di syarat sprint; periksa apakah memang disengaja)")
    lap = ROOT / "reports" / "pasangan_rekonsiliasi.md"
    if not (lap.exists() and lap.stat().st_mtime >= mulai - 1):
        info("reports/pasangan_rekonsiliasi.md tidak ditulis oleh pipeline")
    pg = ROOT / "reports" / "panel_gold.md"
    if pg.exists() and pg.stat().st_mtime >= mulai - 1:
        teks = pg.read_text(encoding="utf-8")
        sec = teks.split("## 4. Metrik")[-1]
        catat("reports/panel_gold.md ditulis oleh pipeline (kunci kembar 0, jejak ke berkas mentah)",
              "kunci kembar: 0" in teks and "sel terlacak lebih jauh ke satu baris berkas mentah" in teks)
        catat("metrik di results/124450121/metrics.json cocok dengan hitungan pipeline", "BEDA" not in sec and "tidak ada" not in sec,
              "\n".join(b.strip("- ") for b in sec.splitlines() if "BEDA" in b or "tidak ada" in b))
    else:
        info("reports/panel_gold.md tidak ditulis oleh pipeline; metrik 124450121 tidak dibandingkan dengan hitungan pipeline")
    panel_baris = {}
    try:
        import pandas as pd
        for f in rek:
            if not any("kategori" in c for c in pd.read_parquet(f).columns):
                info(f"{f.name}: belum ada kolom kategori penjelasan selisih (definisi/metode/vintage/cakupan/belum terjelaskan)")
                break
        for f in panel_file:
            df = pd.read_parquet(f)
            panel_baris[f.name] = len(df)
            kunci = [c for c in ("wilayah_kode", "periode", "indikator") if c in df.columns]
            if len(kunci) >= 2:
                catat(f"{f.name}: kunci ({', '.join(kunci)}) tidak kembar", int(df.duplicated(kunci).sum()) == 0, f"{len(df)} baris")
    except Exception as e:
        catat("membaca tabel Gold", False, repr(e))

    print("\n== basis data SQL")
    dbs = [d for d in (ROOT / "data").rglob("*") if d.suffix in (".db", ".sqlite", ".sqlite3") and d.stat().st_mtime >= mulai - 1]
    catat("basis data SQL dibangun oleh pipeline", bool(dbs), ", ".join(str(d.relative_to(ROOT)) for d in dbs))
    blok["sql"] = [str(d.relative_to(ROOT)) for d in dbs]
    for d in dbs:
        c = sqlite3.connect(d)
        try:
            tabel = [t for (t,) in c.execute("select name from sqlite_master where type='table'")]
            blok.setdefault("sql_tabel", {})[d.name] = len(tabel)
            tanpa_pk = [t for t in tabel if not any(r[5] > 0 for r in c.execute(f"pragma table_info({t})"))]
            jumlah = {t: c.execute(f"select count(*) from {t}").fetchone()[0] for t in tabel}
            catat(f"{d.name}: {len(tabel)} tabel, semuanya punya kunci primer", bool(tabel) and not tanpa_pk,
                  ", ".join(f"{t} {n}" for t, n in jumlah.items()) + (f"\ntanpa kunci primer: {tanpa_pk}" if tanpa_pk else ""))
            silver_n = len(pd.read_parquet(ROOT / "data" / "silver" / "silver.parquet"))
            sd = [t for t in tabel if "silver" in t.lower()]
            catat(f"{d.name}: tabel Silver berisi {silver_n} baris sama dengan silver.parquet", bool(sd) and jumlah[sd[0]] == silver_n,
                  f"tabel Silver: {sd or 'tidak ditemukan'}; semua tabel: {tabel}")
            gd = [t for t in tabel if "panel" in t.lower()]
            if gd:
                catat(f"{d.name}: tabel panel Gold berisi baris yang sama dengan berkas panel Parquet", jumlah[gd[0]] in panel_baris.values(),
                      f"tabel SQL {gd[0]}: {jumlah[gd[0]]} baris; berkas Parquet: {panel_baris}")
            else:
                info(f"{d.name}: tidak ada tabel bernama *panel*; panel Gold belum ada di SQL?", f"semua tabel: {tabel}")
        finally:
            c.close()

    print("\n== Silver, metrics, dan log")
    silver = ROOT / "data" / "silver" / "silver.parquet"
    s = jalan(sys.executable, "-m", "src.common.skema", "data/silver/silver.parquet")
    catat("python -m src.common.skema lolos", s.returncode == 0 and "LOLOS" in s.stdout, (s.stdout + s.stderr).strip()[-300:])
    kurang = []
    for nim, nama in NIM.items():
        try:
            d = json.loads((ROOT / "results" / nim / "metrics.json").read_text(encoding="utf-8"))
            assert d.get("metrik") and d.get("data_hash")
        except Exception:
            kurang.append(f"{nim} ({nama})")
    catat("results/<nim>/metrics.json ada untuk semua anggota", not kurang, "belum ada atau rusak: " + ", ".join(kurang) if kurang else "")
    try:
        mj = json.loads((ROOT / "results/124450121/metrics.json").read_text(encoding="utf-8"))["metrik"]
        if "seri_panel" not in mj or "baris_gold" not in mj:
            info("metrics 124450121 belum memuat seri_panel dan baris_gold")
        ma = json.loads((ROOT / "results/124450110/metrics.json").read_text(encoding="utf-8"))["metrik"]
        if not any(k in ma for k in ("pasangan_rekonsiliasi", "selisih_median", "rilis_dibaca")):
            info("metrics 124450110 belum memuat metrik Sprint 2 (pasangan_rekonsiliasi, selisih_median)")
    except Exception:
        pass
    try:
        baris = list(csv.reader((ROOT / "log-keputusan.csv").read_text(encoding="utf-8-sig").splitlines()))
        data = [b for b in baris[1:] if b]
        nomor = [int(re.match(r"K-(\d+)$", b[0]).group(1)) for b in data]
        masalah = []
        if any(len(b) != 9 for b in baris if b): masalah.append("ada baris dengan kolom tidak 9")
        if len(set(nomor)) != len(nomor): masalah.append("ID kembar")
        loncat = [n for n in range(1, max(nomor) + 1) if n not in nomor]
        if loncat: masalah.append("ID loncat: " + ", ".join(f"K-{n:03d}" for n in loncat))
        catat("log-keputusan.csv: 9 kolom, ID unik dan berurutan", not masalah, f"{len(data)} baris, sampai K-{max(nomor):03d}" + ("\n" + "; ".join(masalah) if masalah else ""))
    except Exception as e:
        catat("membaca log-keputusan.csv", False, repr(e))

    diubah = [b[3:] for b in jalan("git", "status", "--porcelain", "--untracked-files=no").stdout.splitlines() if b.strip()]
    if diubah:
        info("pipeline mengubah berkas yang dilacak git; JANGAN di-commit di main, periksa dulu dengan git status", "\n".join(diubah))

    print(f"\nRingkasan: {sum(hasil)} dari {len(hasil)} pemeriksaan lulus; {len(catatan)} catatan.")
    print("\n" + "=" * 70 + "\nBLOK UNTUK KOMENTAR TUGAS #34 (salin; periksa tiap baris sebelum dikirim)\n" + "=" * 70)
    ok_semua = all(hasil)
    print(f"Dijalankan pada {datetime.datetime.now():%d %B %Y %H:%M} di cabang {blok.get('cabang')} (commit {blok.get('commit')}).")
    status = "TIDAK" if not blok.get("selesai") else ("ya, TETAPI ada tahap yang dilewati sehingga belum memenuhi syarat" if blok.get("dilewati") else "ya")
    print(f"- Selesai sampai validasi: {status} (validasi: {blok.get('validasi')})")
    print(f"- Tahap yang dilewati: {'; '.join(blok.get('dilewati', [])) or 'tidak ada'}")
    print(f"- Gold: {', '.join(blok.get('gold', [])) or 'tidak ada yang ditulis pipeline'}")
    print(f"- Tabel nasional: {', '.join(blok.get('nasional', [])) or 'tidak ada'}")
    print(f"- Rekonsiliasi: {', '.join(blok.get('rekonsiliasi', [])) or 'tidak ada'}")
    print(f"- SQL: {', '.join(f'{n} ({blok.get('sql_tabel', {}).get(n.split(chr(92))[-1].split('/')[-1], '?')} tabel)' for n in blok.get('sql', [])) or 'tidak ada'}")
    print(f"- Waktu jalan: {blok.get('detik', 0):.1f} detik")
    print(f"- Hasil pemeriksaan: {sum(hasil)} dari {len(hasil)} lulus" + ("" if ok_semua else "; GAGAL: " + "; ".join(gagal_nama)))
    if blok.get("penting"):
        print("- Baris penting dari keluaran pipeline:\n  " + "\n  ".join(blok["penting"]))
    print("=" * 70)
    print("Belum diperiksa skrip ini: tiap PR Sprint 2 sudah di-review (cek tab Pull requests di GitHub).")
    return 0 if all(hasil) else 1


if __name__ == "__main__":
    sys.exit(main())
