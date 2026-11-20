CREATE TABLE IF NOT EXISTS silver_data (
    sumber TEXT NOT NULL,
    seri_kode TEXT NOT NULL,
    wilayah_kode INTEGER NOT NULL,
    nama_wilayah TEXT,
    periode TEXT NOT NULL,
    jenis_periode TEXT,
    rincian TEXT NOT NULL,
    nilai REAL,
    satuan TEXT,
    _berkas_raw TEXT,
    _sha256_raw TEXT,
    kode_sdg TEXT,
    daerah TEXT NOT NULL,
    jenis_kelamin TEXT NOT NULL,
    kategori_anomali TEXT,
    PRIMARY KEY (
        sumber,
        seri_kode,
        wilayah_kode,
        periode,
        daerah,
        jenis_kelamin,
        rincian
    )
);