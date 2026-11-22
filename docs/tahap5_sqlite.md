# Tahap 5: penyimpanan Silver dan Gold ke SQLite

## Yang disimpan
Berkas `data/silver/silver.db` berisi dua tabel:

- `silver_data`: seluruh isi `data/silver/silver.parquet` (15 kolom, termasuk `_berkas_raw`, `_sha256_raw`, dan `kategori_anomali`). Dimuat oleh `scripts/muat_silver_sqlite.py`.
- `gold_ringkasan_bersih`: ringkasan per sumber, seri, wilayah, periode, daerah, dan jenis kelamin (jumlah observasi, rata-rata, nilai minimum, nilai maksimum). Dimuat oleh `scripts/load_gold.py`.

Skema ada di `sql/silver_schema.sql` dan `sql/gold_schema.sql`.

## Kunci primer
- `silver_data`: (`sumber`, `seri_kode`, `wilayah_kode`, `periode`, `daerah`, `jenis_kelamin`, `rincian`).
- `gold_ringkasan_bersih`: (`sumber`, `seri_kode`, `wilayah_kode`, `periode`, `daerah`, `jenis_kelamin`).

Kolom kunci dibuat `NOT NULL` sehingga baris dengan kunci kembar atau kunci kosong ditolak oleh basis data, bukan hanya oleh skrip pemeriksa. Ini mendukung aturan validasi "kunci unik Silver tidak kembar".

## Alasan memilih SQLite
1. **Mudah direproduksi.** Basis data berupa satu berkas, tanpa server, kredensial, atau instalasi tambahan. Siapa pun yang mengklon repo dapat menjalankan ulang pemuatan, sesuai syarat `python pipeline.py` dari klon bersih.
2. **Tanpa dependensi baru.** Modul `sqlite3` sudah bawaan Python, sehingga `requirements.txt` tidak bertambah.
3. **Ukuran data kecil.** Silver hanya berisi ribuan baris, jauh di bawah ukuran yang memerlukan mesin basis data server atau penyimpanan kolumnar.
4. **Mendukung kunci primer komposit dan batasan `NOT NULL`,** yang dibutuhkan untuk menegakkan keunikan kunci Silver.
5. **Dapat diperiksa langsung.** Pembimbing dan rekan dapat membuka `silver.db` dengan alat SQL biasa untuk menelusuri baris sampai `_berkas_raw` dan `_sha256_raw`.
6. **Pemuatan bersifat idempoten.** Silver dimuat dengan `INSERT OR REPLACE` dan Gold dengan `DELETE` lalu `INSERT`, sehingga menjalankan ulang skrip tidak menggandakan baris.

## Alternatif yang tidak dipilih
- **PostgreSQL:** membutuhkan server dan konfigurasi akses, sehingga sulit direproduksi dari klon bersih dalam waktu 15 menit, dan berlebihan untuk data sekecil ini.
- **DuckDB:** cocok untuk analitik kolumnar dan tetap dipakai pada perbandingan skala tahap 7 (pandas vs DuckDB atau Dask). Untuk penyimpanan Silver dan Gold yang kecil dan memerlukan kunci primer, SQLite sudah mencukupi.

## Keterbatasan
- SQLite hanya mengizinkan satu penulis pada satu waktu dan tidak dirancang untuk data besar atau akses bersamaan.
- Tipe data SQLite longgar; `periode` disimpan sebagai `TEXT`, jadi pengurutan harus memperhatikan format teks.
- `INSERT OR REPLACE` menimpa baris dengan kunci yang sama. Karena itu keunikan kunci diperiksa terpisah oleh validasi Silver sebelum pemuatan.

## Cara memuat ulang
```
python scripts/muat_silver_sqlite.py
python scripts/load_gold.py
```
