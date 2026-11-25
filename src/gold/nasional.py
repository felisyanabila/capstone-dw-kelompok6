"""Tugas #18 (Sprint 1): persiapan tahap 6 -- tabel nasional dan daftar pasangan rekonsiliasi.

Skrip mandiri di src/gold/: hanya MEMBACA data/silver/silver.parquet. Belum dipasang ke
gold.jalankan() (itu milik tahap 4 dan Sprint 2); jalankan sendiri:

    python -m src.gold.nasional

Keluaran:
    data/gold/nasional_periode_seri.parquet        tabel nasional periode x seri
    data/gold/rekonsiliasi_p1_rinci_vs_var1458.parquet   pasangan 1, per wilayah x tahun
    data/gold/rekonsiliasi_p2_var1458_vs_wdi.parquet     pasangan 2, nasional
    data/gold/rekonsiliasi_p3_rinci_vs_wdi.parquet       pasangan tambahan, nasional
    reports/pasangan_rekonsiliasi.md               daftar pasangan + catatan keterbandingan
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SILVER = ROOT / "data" / "silver" / "silver.parquet"
GOLD = ROOT / "data" / "gold"
OUT = ROOT / "reports"

RINCI = "tabel:sdg4_amh_rinci"
VAR = "var1458"
WDI = "SE.ADT.LITR.ZS"
SERI = [RINCI, VAR, WDI]
INDONESIA = 9999

# (kode, seri A, seri B, hanya nasional?, judul)
PASANGAN = [
    ("p1_rinci_vs_var1458", RINCI, VAR, False, "Total tabel rinci vs seri ringkas var1458 (provinsi dan Indonesia)"),
    ("p2_var1458_vs_wdi", VAR, WDI, True, "var1458 baris Indonesia vs WDI SE.ADT.LITR.ZS"),
    ("p3_rinci_vs_wdi", RINCI, WDI, True, "(tambahan) total tabel rinci baris Indonesia vs WDI, karena rinci mulai 2009"),
]


def muat_silver(jalur=SILVER):
    s = pd.read_parquet(jalur)
    s["periode"] = s["periode"].astype(str)
    return s


def _total(s, seri):
    """Baris 'total' satu seri. Berhenti dengan pesan jelas bila kosong atau ada kunci kembar."""
    d = s[(s["seri_kode"] == seri) & (s["rincian"] == "total")]
    if d.empty:
        ada = sorted(s.loc[s["seri_kode"] == seri, "rincian"].unique())
        raise SystemExit(f"Tidak ada baris rincian='total' untuk seri {seri}. "
                         f"seri_kode di Silver: {sorted(s['seri_kode'].unique())}; rincian seri ini: {ada}")
    kembar = d.duplicated(["wilayah_kode", "periode"]).sum()
    if kembar:
        raise SystemExit(f"{seri}: {kembar} pasang wilayah x periode kembar (mungkin dua _berkas_raw). "
                         "Tetapkan aturan pemilihan dulu dan catat di log-keputusan.csv.")
    return d


def tabel_nasional(s):
    """Tabel periode x seri untuk Indonesia (9999), rincian total."""
    bagian = []
    for seri in SERI:
        d = _total(s, seri)
        d = d[d["wilayah_kode"] == INDONESIA][["periode", "nilai"]].rename(columns={"nilai": seri})
        bagian.append(d.set_index("periode"))
    return pd.concat(bagian, axis=1).sort_index().round(2)


def pasangkan(s, seri_a, seri_b, hanya_indonesia):
    """Gabung dua seri pada wilayah x periode yang sama. selisih = A - B."""
    a = _total(s, seri_a)[["wilayah_kode", "nama_wilayah", "periode", "nilai"]]
    b = _total(s, seri_b)[["wilayah_kode", "periode", "nilai"]]
    if hanya_indonesia:
        a, b = a[a["wilayah_kode"] == INDONESIA], b[b["wilayah_kode"] == INDONESIA]
    m = a.merge(b, on=["wilayah_kode", "periode"], how="inner", suffixes=("_a", "_b"), validate="one_to_one")
    m = m.rename(columns={"nilai_a": seri_a, "nilai_b": seri_b})
    m[[seri_a, seri_b]] = m[[seri_a, seri_b]].round(2)
    m["selisih"] = (m[seri_a] - m[seri_b]).round(2)
    return m.sort_values(["wilayah_kode", "periode"]).reset_index(drop=True)


def ringkas(m):
    beda = m[m["selisih"].abs() > 0]
    return {
        "n_pasang": len(m),
        "n_beda": len(beda),
        "selisih_maks": float(m["selisih"].abs().max()) if len(m) else float("nan"),
        "selisih_median_beda": float(beda["selisih"].abs().median()) if len(beda) else 0.0,
        "tahun_beririsan": sorted(m["periode"].unique()),
        "tahun_beda": sorted(beda["periode"].unique()),
    }


def _tabel_md(df):
    kol = list(df.columns)
    baris = ["| " + " | ".join(kol) + " |", "|" + "---|" * len(kol)]
    for r in df.itertuples(index=False):
        baris.append("| " + " | ".join(str(x) for x in r) + " |")
    return "\n".join(baris)


def tulis_md(s, hasil, jalur):
    berkas = s.groupby("seri_kode")["_berkas_raw"].unique()
    t = ["# Pasangan rekonsiliasi dan catatan keterbandingan (persiapan tahap 6)", "",
         "Dihasilkan oleh `python -m src.gold.nasional` dari `data/silver/silver.parquet`. "
         "Semua angka di bawah dihitung dari Silver; jangan diketik tangan.", "",
         "Konvensi: selisih = nilai seri A dikurangi nilai seri B, dibulatkan 2 desimal, satuan persen. "
         "Selisih tidak dihapus dan tidak dipaksa sama.", "",
         "## Berkas sumber tiap seri (lineage)", ""]
    for seri in SERI:
        t.append(f"- `{seri}`: " + ", ".join(f"`{b}`" for b in berkas.get(seri, [])))
    t += ["", "## Pasangan", ""]
    for kode, a, b, nas, judul in PASANGAN:
        r = hasil[kode]
        t += [f"### {kode}: {judul}", "",
              f"- Seri A = `{a}`, seri B = `{b}`, rincian = total, cakupan = {'Indonesia (9999)' if nas else 'semua wilayah'}",
              f"- Pasangan yang cocok: {r['n_pasang']}; berbeda: {r['n_beda']}; selisih mutlak maksimum: {r['selisih_maks']}; "
              f"median selisih mutlak (yang berbeda saja): {r['selisih_median_beda']}",
              f"- Tahun beririsan ({len(r['tahun_beririsan'])}): {', '.join(r['tahun_beririsan'])}",
              f"- Tahun yang ada selisihnya: {', '.join(r['tahun_beda']) or '-'}",
              f"- Rincian lengkap: `data/gold/rekonsiliasi_{kode}.parquet`", ""]
    t += ["## Catatan keterbandingan (sementara, kategori final ditetapkan di Sprint 2)", "",
          "| Pasangan | Dugaan kategori | Bukti yang masih harus dicari |", "|---|---|---|",
          "| p1 | vintage/metode/definisi (belum diketahui) | `manifest_asal.json` kedua tabel BPS; apakah kedua tabel memakai sumber survei dan bobot yang sama; kenapa selisih mengumpul di tahun tertentu |",
          "| p2 | cakupan sama (nasional, 15+); selisih 0 di semua tahun beririsan menunjukkan WDI mungkin bersumber dari BPS | metadata WDI (`metadata/sumber.json`); tahap 7: apakah WDI pernah merevisi angka Indonesia |",
          "| p3 | vintage (rilis WDI berbeda dari BPS) bila ada selisih | arsip WDI tahap 7 |", "",
          "Catatan: daftar lampiran panduan kelompok menunjukkan semua berkas BPS bertanggal 2026-10-17 dan WDI 2026-10-20. "
          "Selisih p1 karena itu perbedaan antar-tabel dalam satu unduhan, bukan revisi antar-tanggal unduh. "
          "Periksa `_berkas_raw` di bagian lineage dan samakan istilah dengan `kategori_anomali = revisi_snapshot` di log (K-006, K-008)."]
    jalur.write_text("\n".join(t) + "\n", encoding="utf-8")


def main():
    s = muat_silver()
    GOLD.mkdir(parents=True, exist_ok=True)

    nas = tabel_nasional(s)
    nas.reset_index().to_parquet(GOLD / "nasional_periode_seri.parquet", index=False)
    print(f"nasional_periode_seri.parquet: {nas.shape[0]} periode x {nas.shape[1]} seri")
    print(nas.to_string(), "\n")

    hasil = {}
    for kode, a, b, nasional, _ in PASANGAN:
        m = pasangkan(s, a, b, nasional)
        m.to_parquet(GOLD / f"rekonsiliasi_{kode}.parquet", index=False)
        hasil[kode] = ringkas(m)
        r = hasil[kode]
        print(f"{kode}: {r['n_pasang']} pasang, {r['n_beda']} berbeda, maks {r['selisih_maks']}, "
              f"beririsan {len(r['tahun_beririsan'])} tahun")
    tulis_md(s, hasil, OUT / "pasangan_rekonsiliasi.md")

    p2 = hasil["p2_var1458_vs_wdi"]
    print("\nJalankan untuk metrics.json (cek angkanya cocok dengan yang tercetak di atas):")
    print(f"python -m src.common.hasil 124450110 pasangan_rekonsiliasi={len(PASANGAN)} "
          f"periode_beririsan={len(p2['tahun_beririsan'])}")

def tabel_nasional_gold(s):
    
    wdi_ref = _total(s, WDI)
    wdi_ref = wdi_ref[wdi_ref["wilayah_kode"] == INDONESIA][["periode", "nilai"]].rename(
        columns={"nilai": "nilai_pembanding"}
    )

    daftar = []
    for seri in SERI:
        d = _total(s, seri)
        nas = d[d["wilayah_kode"] == INDONESIA].copy()

        if not nas.empty:
            asal = "pembanding" if seri == WDI else "baris_indonesia"
            df_seri = nas[["periode", "nilai", "_berkas_raw"]].copy()
            df_seri["asal_angka"] = asal
        else:
            
            prov = d[d["wilayah_kode"] != INDONESIA]
            df_seri = prov.groupby("periode", as_index=False).agg(
                nilai=("nilai", "mean"),
                _berkas_raw=("_berkas_raw", lambda x: ";".join(sorted(set(x)))),
            )
            df_seri["asal_angka"] = "agregat"

        df_seri["seri_kode"] = seri
        df_seri["nilai"] = df_seri["nilai"].round(2)
        df_seri["nilai_utama"] = df_seri["nilai"].where(df_seri["seri_kode"] != WDI, other=pd.NA)
        df_seri = df_seri.merge(wdi_ref, on="periode", how="left")
        df_seri["nilai_pembanding"] = df_seri["nilai_pembanding"].round(2)
        daftar.append(df_seri)

    hasil = pd.concat(daftar, ignore_index=True)
    kolom = ["periode", "seri_kode", "nilai", "nilai_utama", "nilai_pembanding", "asal_angka", "_berkas_raw"]
    return hasil[kolom].sort_values(["periode", "seri_kode"]).reset_index(drop=True)


def jalankan(silver: pd.DataFrame) -> dict:
    
    s = silver.copy()
    s["periode"] = s["periode"].astype(str)
    GOLD.mkdir(parents=True, exist_ok=True)

    gold_nas = tabel_nasional_gold(s)
    gold_nas.to_parquet(GOLD / "tabel_nasional.parquet", index=False)

    nas = tabel_nasional(s)
    nas.reset_index().to_parquet(GOLD / "nasional_periode_seri.parquet", index=False)

    tabel = {"tabel_nasional": gold_nas}
    for kode, a, b, nasional, _ in PASANGAN:
        m = pasangkan(s, a, b, nasional)
        m.to_parquet(GOLD / f"rekonsiliasi_{kode}.parquet", index=False)
        tabel[f"rekonsiliasi_{kode}"] = m

    print(f"Gold nasional: tabel_nasional {len(gold_nas)} baris -> {(GOLD / 'tabel_nasional.parquet').relative_to(ROOT)}")
    return tabel