CREATE TABLE IF NOT EXISTS gold_panel_provinsi (
    wilayah_kode INTEGER NOT NULL,
    nama_wilayah TEXT,
    periode TEXT NOT NULL,
    tahun INTEGER,
    indikator TEXT NOT NULL,
    rincian TEXT NOT NULL,
    daerah TEXT,
    jenis_kelamin TEXT,
    nilai REAL,
    satuan TEXT,
    status_sel TEXT,
    kode_sdg TEXT,
    kategori_anomali TEXT,
    nilai_alternatif REAL,
    seri_alternatif TEXT,
    sumber TEXT,
    seri_kanonik TEXT,
    _berkas_raw TEXT,
    _sha256_raw TEXT,
    PRIMARY KEY (wilayah_kode, periode, indikator, rincian)
);

CREATE TABLE IF NOT EXISTS gold_panel_lebar (
    wilayah_kode INTEGER NOT NULL,
    nama_wilayah TEXT,
    periode TEXT NOT NULL,
    tahun INTEGER,
    amh_total REAL,
    amh_perkotaan REAL,
    amh_perdesaan REAL,
    "amh_laki-laki" REAL,
    amh_perempuan REAL,
    "amh_perkotaan_laki-laki" REAL,
    "amh_perkotaan_perempuan" REAL,
    "amh_perdesaan_laki-laki" REAL,
    amh_perdesaan_perempuan REAL,
    PRIMARY KEY (wilayah_kode, periode)
);

CREATE TABLE IF NOT EXISTS gold_tabel_nasional (
    periode TEXT NOT NULL,
    seri_kode TEXT NOT NULL,
    nilai REAL,
    nilai_utama REAL,
    nilai_pembanding REAL,
    asal_angka TEXT,
    _berkas_raw TEXT,
    PRIMARY KEY (periode, seri_kode)
);

CREATE TABLE IF NOT EXISTS gold_nasional_periode_seri (
    periode TEXT NOT NULL,
    "tabel:sdg4_amh_rinci" REAL,
    var1458 REAL,
    "SE.ADT.LITR.ZS" REAL,
    PRIMARY KEY (periode)
);

CREATE TABLE IF NOT EXISTS gold_pemeriksaan_total (
    wilayah_kode INTEGER NOT NULL,
    nama_wilayah TEXT,
    periode TEXT NOT NULL,
    nilai_var1458 REAL,
    _berkas_raw_var1458 TEXT,
    _sha256_raw_var1458 TEXT,
    nilai_rinci_total REAL,
    _berkas_raw_rinci TEXT,
    _sha256_raw_rinci TEXT,
    selisih REAL,
    status_pemeriksaan TEXT,
    dalam_toleransi_0_01 INTEGER,
    PRIMARY KEY (wilayah_kode, periode)
);

CREATE TABLE IF NOT EXISTS gold_rekonsiliasi_p1 (
    wilayah_kode INTEGER NOT NULL,
    nama_wilayah TEXT,
    periode TEXT NOT NULL,
    "tabel:sdg4_amh_rinci" REAL,
    var1458 REAL,
    selisih REAL,
    PRIMARY KEY (wilayah_kode, periode)
);

CREATE TABLE IF NOT EXISTS gold_rekonsiliasi_p2 (
    wilayah_kode INTEGER NOT NULL,
    nama_wilayah TEXT,
    periode TEXT NOT NULL,
    var1458 REAL,
    "SE.ADT.LITR.ZS" REAL,
    selisih REAL,
    PRIMARY KEY (wilayah_kode, periode)
);

CREATE TABLE IF NOT EXISTS gold_rekonsiliasi_p3 (
    wilayah_kode INTEGER NOT NULL,
    nama_wilayah TEXT,
    periode TEXT NOT NULL,
    "tabel:sdg4_amh_rinci" REAL,
    "SE.ADT.LITR.ZS" REAL,
    selisih REAL,
    PRIMARY KEY (wilayah_kode, periode)
);