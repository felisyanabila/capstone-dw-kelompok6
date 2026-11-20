CREATE TABLE IF NOT EXISTS gold_ringkasan_bersih (
    sumber TEXT NOT NULL,
    seri_kode TEXT NOT NULL,
    wilayah_kode INTEGER NOT NULL,
    nama_wilayah TEXT,
    periode TEXT NOT NULL,
    daerah TEXT NOT NULL,
    jenis_kelamin TEXT NOT NULL,
    jumlah_observasi INTEGER NOT NULL,
    rata_rata_nilai REAL,
    nilai_min REAL,
    nilai_max REAL,
    PRIMARY KEY (
        sumber,
        seri_kode,
        wilayah_kode,
        periode,
        daerah,
        jenis_kelamin
    )
);
