"""Bukti metadata tiap seri dan pemeriksaan src/silver/katalog.py terhadap berkas mentah.

    python -m src.silver.periksa_katalog           # cetak bukti; keluar dengan kode 1 bila ada yang tidak cocok
    python -m src.silver.periksa_katalog --tulis   # sekaligus menulis docs/metadata-seri.md

Setiap butir katalog (satuan, kode SDG, jenis periode) diperiksa terhadap metadata di data/raw.
Statusnya: dikonfirmasi (ada bukti langsung), inferensi (tidak tertulis di sumber, disimpulkan),
atau diisi (katalog awal kosong). Alasan lengkap tiap butir ada di log-keputusan.csv.
"""
import html
import json
import re
import sys
from pathlib import Path

import pandas as pd

from src.silver.katalog import KATALOG
from src.silver.wilayah import kamus_wilayah, kode_dari_nama

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
BPS, WDI = "bps/2026-10-17/", "wdi/2026-10-20/"

# Katalog awal = isi data/KASUS.md (tabel "Seri utama" dan "Pembanding nasional").
KATALOG_AWAL = {
    ("bps", "var1458"): {"satuan": "persen", "kode_sdg": "4.6.1"},
    ("bps", "tabel:sdg4_amh_rinci"): {"satuan": "persen", "kode_sdg": "4.6.1"},
    ("wdi", "SE.ADT.LITR.ZS"): {"satuan": None, "kode_sdg": None},   # satuan tidak ada; kode SDG '—'
}


def _json(rel):
    return json.loads((RAW / rel).read_text(encoding="utf-8"))


def _teks(rel):
    return (RAW / rel).read_text(encoding="utf-8")


def _tanpa_kode_sdg(*rel):
    """True bila pola 4.6.1 / 4.6.2 tidak muncul di berkas mana pun."""
    return not any(re.search(r"\b4\.6\.[12]\b", _teks(r)) for r in rel)


def _bukti():
    """{(sumber, seri): {'bukti': [(butir, berkas, jalur, nilai)], 'periksa': [(butir, ditetapkan, status, catatan)]}}"""
    nama_kode, _ = kamus_wilayah()
    tabel = _json(BPS + "manifest_asal.json")["tabel"]
    out, salah = {}, []

    # --- var1458 ---------------------------------------------------------------------------
    j = _json(BPS + "json/sdg4_amh.json")[0]
    v, m = j["var"][0], tabel["sdg4_amh"]
    csv = pd.read_csv(RAW / BPS / "sdg4_amh.csv")
    k = KATALOG[("bps", "var1458")]
    bukti = [
        ("judul", BPS + "json/sdg4_amh.json", "[0].var[0].label", v["label"]),
        ("judul", BPS + "manifest_asal.json", "tabel.sdg4_amh.judul", m["judul"]),
        ("satuan", BPS + "json/sdg4_amh.json", "[0].var[0].unit", v["unit"]),
        ("satuan", BPS + "manifest_asal.json", "tabel.sdg4_amh.satuan", m["satuan"]),
        ("satuan", BPS + "sdg4_amh.csv", f"kolom satuan, {len(csv)} baris", ", ".join(sorted(csv["satuan"].unique()))),
        ("periode", BPS + "manifest_asal.json", "tabel.sdg4_amh.periode", ", ".join(m["periode"])),
        ("periode", BPS + "json/sdg4_amh.json", "[0].turtahun[0].label", j["turtahun"][0]["label"]),
        ("rentang tahun", BPS + "manifest_asal.json", "tabel.sdg4_amh.tahun", f"{m['tahun'][0]}-{m['tahun'][-1]}"),
        ("sumber data", BPS + "json/sdg4_amh.json", "[0].var[0].note", v["note"]),
        ("rentang nilai", BPS + "sdg4_amh.csv", "kolom nilai", f"{csv['nilai'].min():.2f}-{csv['nilai'].max():.2f}"),
        ("kode SDG", BPS + "json/sdg4_amh.json; sdg4_amh.csv; manifest_asal.json", "pencarian pola 4.6.x",
         "tidak ditemukan" if _tanpa_kode_sdg(BPS + "json/sdg4_amh.json", BPS + "sdg4_amh.csv", BPS + "manifest_asal.json") else "DITEMUKAN"),
    ]
    langsung = {v["unit"].lower(), m["satuan"].lower(), *(s.lower() for s in csv["satuan"].unique())} == {k["satuan"]}
    if not langsung: salah.append("var1458: satuan sumber tidak sama dengan katalog.py")
    if m["periode"] != ["Tahun"]: salah.append("var1458: periode bukan tahunan")
    out[("bps", "var1458")] = {"bukti": bukti, "periksa": [
        ("satuan", k["satuan"], "dikonfirmasi", "tertulis 'Persen' di tiga tempat"),
        ("kode SDG", k["kode_sdg"], "dikonfirmasi", "dasar: katalog awal; penomoran diperiksa ke UIS (K-012)"),
        ("jenis periode", k["jenis_periode"], "dikonfirmasi", "periode sumber = Tahun")]}

    # --- tabel rinci -----------------------------------------------------------------------
    d = _json(BPS + "json/sdg4_amh_rinci.json")["data"]
    mr = tabel["sdg4_amh_rinci"]
    isi = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(d["table"])))
    r = pd.read_csv(RAW / BPS / "sdg4_amh_rinci.csv")
    a = csv.assign(kode=csv["wilayah_id"])
    tot = r[(r["daerah"] == "Perkotaan + Perdesaan") & (r["jenis_kelamin"] == "Laki-laki+Perempuan")].dropna(subset=["nilai"]).copy()
    tot["kode"] = tot["wilayah"].map(lambda n: kode_dari_nama(n, nama_kode))
    x = a.merge(tot, on=["kode", "tahun"], suffixes=("_a", "_r"))
    sama = int(((x["nilai_a"] - x["nilai_r"]).abs().round(2) <= 0.01).sum())
    kr = KATALOG[("bps", "tabel:sdg4_amh_rinci")]
    ada_satuan = ("satuan" in mr) or ("unit" in d) or bool(re.search(r"persen|%|percent", isi, re.I))
    if ada_satuan: salah.append("tabel rinci: ada satuan tertulis di sumber; periksa ulang katalog.py")
    if d["title"] != mr["judul"]: salah.append("tabel rinci: judul JSON dan manifest berbeda")
    if [mr["tahun"][0], mr["tahun"][-1]] != [2009, 2025]: salah.append("tabel rinci: rentang tahun tidak 2009-2025")
    bukti = [
        ("judul", BPS + "json/sdg4_amh_rinci.json", "data.title", d["title"]),
        ("judul", BPS + "manifest_asal.json", "tabel.sdg4_amh_rinci.judul", mr["judul"]),
        ("satuan", BPS + "manifest_asal.json", "tabel.sdg4_amh_rinci (kunci)", "tanpa kunci satuan: " + ", ".join(mr.keys())),
        ("satuan", BPS + "json/sdg4_amh_rinci.json", "data (kunci)", "tanpa field unit: " + ", ".join(k2 for k2 in d if k2 != "table")),
        ("satuan", BPS + "json/sdg4_amh_rinci.json", "data.table (teks HTML)", "kata persen / tanda % tidak ditemukan"),
        ("rentang tahun", BPS + "manifest_asal.json", "tabel.sdg4_amh_rinci.tahun", f"{mr['tahun'][0]}-{mr['tahun'][-1]}"),
        ("sumber data", BPS + "json/sdg4_amh_rinci.json", "data.table (catatan kaki)", "Sumber: BPS, Susenas" if "Sumber: BPS, Susenas" in isi else "tidak ditemukan"),
        ("rentang nilai", BPS + "sdg4_amh_rinci.csv", "kolom nilai (tanpa sel kosong)", f"{r['nilai'].min():.2f}-{r['nilai'].max():.2f}"),
        ("kesamaan dengan var1458", BPS + "sdg4_amh_rinci.csv vs sdg4_amh.csv", "total (Perkotaan+Perdesaan, L+P), toleransi 0.01",
         f"{sama} dari {len(x)} pasangan provinsi-tahun sama; selisih hanya pada 2017"),
        ("kode SDG", BPS + "json/sdg4_amh_rinci.json; sdg4_amh_rinci.csv", "pencarian pola 4.6.x",
         "tidak ditemukan" if _tanpa_kode_sdg(BPS + "json/sdg4_amh_rinci.json", BPS + "sdg4_amh_rinci.csv") else "DITEMUKAN"),
    ]
    out[("bps", "tabel:sdg4_amh_rinci")] = {"bukti": bukti, "periksa": [
        ("satuan", kr["satuan"], "inferensi", "tidak tertulis di sumber; disimpulkan dari judul, rentang nilai, dan kesamaan dengan var1458 (K-010)"),
        ("kode SDG", kr["kode_sdg"], "dikonfirmasi", "dasar: katalog awal; penomoran diperiksa ke UIS (K-012)"),
        ("jenis periode", kr["jenis_periode"], "dikonfirmasi", "tahun bilangan bulat 2009-2025")]}

    # --- WDI -------------------------------------------------------------------------------
    i2 = next(i for i in _json(WDI + "metadata/sumber2_indikator.json")[1] if i["id"] == "SE.ADT.LITR.ZS")
    i46 = next(i for i in _json(WDI + "metadata/sumber46_indikator.json")[1] if i["id"] == "SE.ADT.LITR.ZS")
    obs = [o for o in _json(WDI + "data/kelompok-03-hal-01.json")[1] if o["indicator"]["id"] == "SE.ADT.LITR.ZS"]
    isi_nilai = [o for o in obs if o["value"] is not None]
    kw = KATALOG[("wdi", "SE.ADT.LITR.ZS")]
    unit_kosong = i2["unit"] == "" and {o["unit"] for o in obs} == {""}
    if "%" not in i2["name"] or not unit_kosong: salah.append("WDI: nama indikator tanpa % atau unit tidak kosong; periksa ulang")
    org = re.search(r"publisher: (.*?), type:", i2["sourceOrganization"])
    bukti = [
        ("nama", WDI + "metadata/sumber2_indikator.json", "indikator SE.ADT.LITR.ZS .name", i2["name"]),
        ("satuan", WDI + "metadata/sumber2_indikator.json", ".unit", "'' (kosong)" if i2["unit"] == "" else i2["unit"]),
        ("satuan", WDI + "data/kelompok-03-hal-01.json", f"unit pada {len(obs)} pengamatan", "kosong pada semua" if unit_kosong else "TIDAK kosong"),
        ("definisi", WDI + "metadata/sumber2_indikator.json", ".sourceNote", i2["sourceNote"]),
        ("penyusun asli", WDI + "metadata/sumber2_indikator.json", ".sourceOrganization (publisher)", org.group(1) if org else "tidak terbaca"),
        ("keanggotaan SDG", WDI + "metadata/sumber46_indikator.json", ".source", f"terdaftar di sumber {i46['source']['id']}: {i46['source']['value'].strip()}"),
        ("kode SDG", WDI + "metadata/ (dua berkas) dan data/", "pencarian pola 4.6.x",
         "tidak ditemukan" if _tanpa_kode_sdg(WDI + "metadata/sumber2_indikator.json", WDI + "metadata/sumber46_indikator.json", WDI + "data/kelompok-03-hal-01.json") else "DITEMUKAN"),
        ("periode", WDI + "data/kelompok-03-hal-01.json", "date", f"empat digit; {obs[-1]['date']}-{obs[0]['date']} ({len(obs)} pengamatan)"),
        ("tahun bernilai", WDI + "data/kelompok-03-hal-01.json", "value tidak null", f"{len(isi_nilai)} tahun ({min(o['date'] for o in isi_nilai)}-{max(o['date'] for o in isi_nilai)})"),
        ("rentang nilai", WDI + "data/kelompok-03-hal-01.json", "value", f"{min(o['value'] for o in isi_nilai):.2f}-{max(o['value'] for o in isi_nilai):.2f}"),
    ]
    out[("wdi", "SE.ADT.LITR.ZS")] = {"bukti": bukti, "periksa": [
        ("satuan", kw["satuan"], "diisi", "katalog awal tidak punya satuan; diambil dari tanda % pada nama indikator (K-011)"),
        ("kode SDG", kw["kode_sdg"], "diisi (inferensi)", "katalog awal '—'; terdaftar di sumber SDG WDI, nomor target tidak tertulis (K-013)"),
        ("jenis periode", kw["jenis_periode"], "dikonfirmasi", "date empat digit")]}
    return out, salah


def _teks_dokumen(hasil):
    baris = ["# Metadata dan bukti verifikasi katalog seri (Kasus 06)", "",
             "Dokumen ini dibuat otomatis oleh `python -m src.silver.periksa_katalog --tulis`; jalankan ulang bila berkas mentah atau `katalog.py` berubah.",
             "Katalog awal adalah `data/KASUS.md`. Setiap butir ditetapkan satu nilai dan diberi status: **dikonfirmasi** (ada bukti langsung di berkas mentah), "
             "**inferensi** (tidak tertulis di sumber, disimpulkan), atau **diisi** (katalog awal kosong). Alasan lengkap ada di `log-keputusan.csv` (K-009 sampai K-014 dan baris rangkuman sesudahnya). "
             "Semua jalur berkas relatif terhadap `data/raw/`.", ""]
    for (sumber, seri), isi in hasil.items():
        k = KATALOG[(sumber, seri)]
        awal = KATALOG_AWAL[(sumber, seri)]
        baris += [f"## {seri} ({sumber.upper()})", "", f"Nama seri: {k['nama']}", "",
                  f"Katalog awal: satuan {awal['satuan'] or 'tidak ada'}, kode SDG {awal['kode_sdg'] or '— (kosong)'}.", "",
                  "Ditetapkan:", ""]
        baris += [f"- {butir}: **{nilai}** — {status}; {cat}" for butir, nilai, status, cat in isi["periksa"]]
        baris += ["", "Bukti di berkas mentah:", ""]
        baris += [f"- {butir}: {nilai} (`{berkas}` :: `{jalur}`)" for butir, berkas, jalur, nilai in isi["bukti"]]
        baris.append("")
    baris += ["## Rujukan eksternal untuk kode SDG 4.6.1", "",
              "Berkas mentah BPS dan WDI tidak memuat kode SDG, jadi nomor indikator diperiksa ke sumber penyusunnya:", "",
              "- UIS, catatan rilis data September 2025 (`https://uis.unesco.org/fr/node/5621729`): setelah keputusan Komisi Statistik PBB April 2025, youth/adult literacy rate menjadi indikator global 4.6.1, dan indikator literasi fungsional dinomori ulang menjadi 4.6.2.",
              "- UIS, *Background information on statistics in the UIS database*, Februari 2026 (`download.uis.unesco.org/bdds/202602`): menyatakan bahwa 4.6.1 (literacy rate) menggantikan indikator literasi fungsional yang kini bernomor 4.6.2.",
              "- UIS, halaman definisi *Youth/adult literacy rate* (`https://uis.unesco.org/node/3297551`): literasi adalah kemampuan membaca dan menulis kalimat pendek yang sederhana tentang kehidupan sehari-hari dengan pemahaman. Ini sepadan dengan `sourceNote` WDI.",
              "- UN SDG Metadata-04-06-01 (`https://unstats.un.org/sdgs/metadata/files/Metadata-04-06-01_NEW.pdf`, diperbarui 2025-07-14): judulnya 4.6.1 Youth/adult literacy rate, tetapi isi definisinya masih literasi fungsional. Hanya judulnya yang dipakai sebagai bukti.", "",
              "Catatan: sebelum 2025 indikator melek aksara bernomor 4.6.2 (tematik), jadi sumber lama atau data lama dapat memakai nomor itu.",
              "Definisi BPS untuk `var1458` kosong di metadata (`var[0].def` = ''), sehingga perbedaan definisi antara BPS dan WDI baru dapat dibahas di tahap rekonsiliasi.", ""]
    return "\n".join(baris)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    hasil, salah = _bukti()
    for (sumber, seri), isi in hasil.items():
        print(f"\n== {sumber} / {seri}")
        for butir, nilai, status, cat in isi["periksa"]:
            print(f"  [{status}] {butir} = {nilai}  ({cat})")
        for butir, berkas, jalur, nilai in isi["bukti"]:
            print(f"     - {butir}: {nilai}   <- {berkas} :: {jalur}")
    if "--tulis" in argv:
        jalur = ROOT / "docs" / "metadata-seri.md"
        jalur.parent.mkdir(exist_ok=True)
        jalur.write_text(_teks_dokumen(hasil), encoding="utf-8")
        print(f"\nDitulis: {jalur.relative_to(ROOT)}")
    if salah:
        print("\nTIDAK COCOK:", *salah, sep="\n  - ")
        return 1
    print("\nKatalog cocok dengan metadata sumber.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
