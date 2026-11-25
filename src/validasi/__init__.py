from pathlib import Path
import pandas as pd
from src.common.manifest import baca
from src.common.skema import periksa_silver

ROOT = Path(__file__).resolve().parents[2]


def jalankan(silver: pd.DataFrame, gold: dict, out_report: Path = ROOT / "reports" / "validasi.md") -> dict:
    """Validasi struktur Silver dan Gold lalu tulis ringkasan ke reports/validasi.md."""
    manifest = baca()
    pelanggaran_silver = periksa_silver(silver, manifest)

    rek = gold.get("rekonsiliasi", pd.DataFrame())
    panel = gold.get("panel_melek_aksara", pd.DataFrame())

    jumlah_rek = len(rek)
    jumlah_selisih = int((rek["selisih"].notna() & (rek["selisih"].abs() > 0)).sum()) if not rek.empty and "selisih" in rek.columns else 0
    jumlah_panel = len(panel)

    out_file = Path(out_report)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Laporan Validasi Pipeline",
        "",
        f"- Pelanggaran skema Silver: {len(pelanggaran_silver)}",
        f"- Jumlah baris tabel panel Gold (`panel_melek_aksara`): {jumlah_panel}",
        f"- Jumlah baris tabel rekonsiliasi Gold (`rekonsiliasi`): {jumlah_rek}",
        f"- Jumlah baris rekonsiliasi dengan selisih tidak nol: {jumlah_selisih}",
    ]
    if pelanggaran_silver:
        lines.append("")
        lines.append("## Detail Pelanggaran Silver")
        for item in pelanggaran_silver:
            lines.append(f"- {item}")

    out_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {
        "pelanggaran_silver": pelanggaran_silver,
        "jumlah_panel": jumlah_panel,
        "jumlah_rekonsiliasi": jumlah_rek,
        "jumlah_selisih": jumlah_selisih,
    }
