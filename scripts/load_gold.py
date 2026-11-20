from pathlib import Path
import sqlite3

ROOT_DIR = Path(__file__).resolve().parents[1]
DB_PATH = ROOT_DIR / "data" / "silver" / "silver.db"
SCHEMA_PATH = ROOT_DIR / "sql" / "gold_schema.sql"


def load_gold() -> int:
    conn = sqlite3.connect(DB_PATH)
    try:
        schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
        with conn:
            conn.executescript(schema_sql)
            conn.execute("DELETE FROM gold_ringkasan_bersih")
            conn.execute(
                """
                INSERT INTO gold_ringkasan_bersih (
                    sumber,
                    seri_kode,
                    wilayah_kode,
                    nama_wilayah,
                    periode,
                    daerah,
                    jenis_kelamin,
                    jumlah_observasi,
                    rata_rata_nilai,
                    nilai_min,
                    nilai_max
                )
                SELECT
                    sumber,
                    seri_kode,
                    wilayah_kode,
                    nama_wilayah,
                    periode,
                    daerah,
                    jenis_kelamin,
                    COUNT(*) AS jumlah_observasi,
                    ROUND(AVG(nilai), 4) AS rata_rata_nilai,
                    MIN(nilai) AS nilai_min,
                    MAX(nilai) AS nilai_max
                FROM silver_data
                WHERE kategori_anomali IS NULL
                GROUP BY
                    sumber,
                    seri_kode,
                    wilayah_kode,
                    nama_wilayah,
                    periode,
                    daerah,
                    jenis_kelamin
                """
            )
        total = conn.execute("SELECT COUNT(*) FROM gold_ringkasan_bersih").fetchone()[0]
    finally:
        conn.close()

    print(f"Berhasil memuat {total} baris ke gold_ringkasan_bersih di {DB_PATH}.")
    return total


if __name__ == "__main__":
    load_gold()
