from pathlib import Path
import sqlite3
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
PARQUET_PATH = BASE_DIR / "data" / "silver" / "silver.parquet"
SQL_PATH = BASE_DIR / "sql" / "silver_schema.sql"
DB_PATH = BASE_DIR / "data" / "silver" / "silver.db"
TABLE_NAME = "silver_data"


def main() -> None:
    df = pd.read_parquet(PARQUET_PATH)

    columns = [
        "sumber",
        "seri_kode",
        "wilayah_kode",
        "nama_wilayah",
        "periode",
        "jenis_periode",
        "rincian",
        "nilai",
        "satuan",
        "_berkas_raw",
        "_sha256_raw",
        "kode_sdg",
        "daerah",
        "jenis_kelamin",
        "kategori_anomali",
    ]
    df = df[columns].copy()
    df["wilayah_kode"] = df["wilayah_kode"].astype(int)
    df = df.astype(object).where(pd.notna(df), None)

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    ddl_sql = SQL_PATH.read_text(encoding="utf-8")

    placeholders = ", ".join(["?"] * len(columns))
    col_list = ", ".join(columns)
    insert_sql = f"INSERT OR REPLACE INTO {TABLE_NAME} ({col_list}) VALUES ({placeholders})"

    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(ddl_sql)
        rows = [tuple(row) for row in df.itertuples(index=False, name=None)]
        conn.executemany(insert_sql, rows)
        conn.commit()
        total_db = conn.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}").fetchone()[0]

    print(f"Berhasil memuat {len(rows)} baris ke {DB_PATH} (total di tabel: {total_db}).")


if __name__ == "__main__":
    main()