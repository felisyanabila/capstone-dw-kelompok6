"""Tahap 1 — Ekstraksi. Milik tim.

Baca setiap berkas di data/raw/ menjadi DataFrame mentah yang setia pada sumbernya:
jangan membersihkan di sini, cukup ratakan struktur dan catat asal tiap baris
(`_berkas_raw` relatif data/raw/, `_sha256_raw` dari src.common.manifest).
"""
import html
import json
import re
from pathlib import Path

import pandas as pd

from src.common.manifest import RAW, sha256_raw


def _tempel_lineage(df: pd.DataFrame, berkas_relatif: str, raw: Path = RAW) -> pd.DataFrame:
    df = df.copy()
    df["_berkas_raw"] = berkas_relatif
    df["_sha256_raw"] = sha256_raw(berkas_relatif, raw=raw)
    return df


def baca_bps_csv_ringkas(raw: Path = RAW) -> pd.DataFrame:
    """Membaca sdg4_amh.csv (var1458)."""
    berkas = "bps/2026-10-17/sdg4_amh.csv"
    df = pd.read_csv(raw / berkas, encoding="utf-8")
    return _tempel_lineage(df, berkas, raw=raw)


def baca_bps_csv_rinci(raw: Path = RAW) -> pd.DataFrame:
    """Membaca sdg4_amh_rinci.csv (pratampil tabel:sdg4_amh_rinci).
    Catatan: kolom 'cek' dipertahankan di lapis mentah (seluruh isinya NaN, kolom bantu ekspor BPS).
    """
    berkas = "bps/2026-10-17/sdg4_amh_rinci.csv"
    df = pd.read_csv(raw / berkas, encoding="utf-8")
    return _tempel_lineage(df, berkas, raw=raw)


def baca_bps_json_ringkas(raw: Path = RAW) -> pd.DataFrame:
    """Membaca json/sdg4_amh.json (struktur WebAPI BPS: vervar, var, turvar, tahun, turtahun, datacontent)."""
    berkas = "bps/2026-10-17/json/sdg4_amh.json"
    with open(raw / berkas, encoding="utf-8") as f:
        paket_list = json.load(f)

    baris = []
    for item in paket_list:
        var_info = item["var"][0]
        var_id = str(var_info["val"])
        satuan = var_info.get("unit", "")

        map_wilayah = {str(w["val"]): w["label"] for w in item["vervar"]}
        map_turvar = {str(t["val"]): t["label"] for t in item["turvar"]}
        map_tahun = {str(th["val"]): th["label"] for th in item["tahun"]}
        map_turtahun = {str(tt["val"]): tt["label"] for tt in item["turtahun"]}

        for w_id, w_label in map_wilayah.items():
            for tv_id, tv_label in map_turvar.items():
                for th_id, th_label in map_tahun.items():
                    for tt_id, tt_label in map_turtahun.items():
                        kunci = f"{w_id}{var_id}{tv_id}{th_id}{tt_id}"
                        if kunci in item["datacontent"]:
                            baris.append(
                                {
                                    "var_id": int(var_id),
                                    "wilayah_id": int(w_id),
                                    "wilayah": w_label,
                                    "turvar_id": int(tv_id),
                                    "turvar": tv_label,
                                    "tahun_id": int(th_id),
                                    "tahun": int(th_label),
                                    "periode_id": int(tt_id),
                                    "periode": tt_label,
                                    "nilai": item["datacontent"][kunci],
                                    "satuan": satuan,
                                }
                            )

    df = pd.DataFrame(baris)
    return _tempel_lineage(df, berkas, raw=raw)


def baca_bps_json_rinci(raw: Path = RAW) -> pd.DataFrame:
    """Membaca json/sdg4_amh_rinci.json dengan unescape HTML dan meratakan header bertingkat."""
    berkas = "bps/2026-10-17/json/sdg4_amh_rinci.json"
    with open(raw / berkas, encoding="utf-8") as f:
        payload = json.load(f)

    tabel_html = html.unescape(payload["data"]["table"])
    trs = re.findall(r"<tr[^>]*>(.*?)</tr>", tabel_html, flags=re.S | re.I)

    def _ekstrak_sel_dengan_colspan(tr_html: str) -> list[str]:
        hasil = []
        for tag_open, isi in re.findall(r"<(t[dh][^>]*)>(.*?)</t[dh]>", tr_html, flags=re.S | re.I):
            teks = re.sub(r"<[^>]+>", " ", isi)
            teks = html.unescape(teks).replace("\xa0", " ")
            teks = re.sub(r"\s+", " ", teks).strip()
            m = re.search(r"colspan\s*=\s*['\"]?(\d+)", tag_open, flags=re.I)
            span = int(m.group(1)) if m else 1
            hasil.extend([teks] * span)
        return hasil

    matriks = [_ekstrak_sel_dengan_colspan(tr) for tr in trs]

    
    baris_daerah = matriks[2]
    baris_jk = matriks[3]
    baris_tahun = [""] + matriks[4]

    baris = []
    
    for row in matriks[5:]:
        if not row or not row[0]:
            continue
        wilayah = row[0]
        if wilayah.lower().startswith(("catatan", "sumber", "keterangan", "*")):
            break

        
        batas_kolom = min(len(row), len(baris_daerah), len(baris_jk), len(baris_tahun))
        for col_idx in range(2, batas_kolom):
            tahun_str = baris_tahun[col_idx]
            if not tahun_str.isdigit():
                continue
            nilai_mentah = row[col_idx]
            baris.append(
                {
                    "wilayah": wilayah,
                    "daerah": baris_daerah[col_idx],
                    "jenis_kelamin": baris_jk[col_idx],
                    "tahun": int(tahun_str),
                    "nilai": nilai_mentah,
                }
            )

    df = pd.DataFrame(baris)
    return _tempel_lineage(df, berkas, raw=raw)


def jalankan(raw: Path = RAW) -> dict[str, pd.DataFrame]:
    """Kembalikan {nama_sumber: DataFrame mentah} untuk semua berkas BPS."""
    return {
        "bps_sdg4_amh_csv": baca_bps_csv_ringkas(raw=raw),
        "bps_sdg4_amh_rinci_csv": baca_bps_csv_rinci(raw=raw),
        "bps_sdg4_amh_json": baca_bps_json_ringkas(raw=raw),
        "bps_sdg4_amh_rinci_json": baca_bps_json_rinci(raw=raw),
    }