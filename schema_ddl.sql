-- ============================================================================
-- DATABASE SCHEMA: Koperasi Management System
-- Generated from metadata_database_hackathon_final.xlsx
-- Total: 27 tables, 32 foreign key relationships
-- Date: 2026-07-10
-- ============================================================================

-- ============================================================================
-- PHASE 1: REFERENCE / MASTER TABLES (no foreign key dependencies)
-- ============================================================================

-- 1. referensi_wilayah - Region/administrative area reference
CREATE TABLE referensi_wilayah (
    kode_wilayah    TEXT        NOT NULL,
    provinsi        TEXT        NULL,
    kab_kota        TEXT        NULL,
    kecamatan       TEXT        NULL,
    desa_kelurahan  TEXT        NULL,
    dibuat_pada     TIMESTAMP   NULL,
    diperbarui_pada TIMESTAMP   NULL,
    CONSTRAINT pk_referensi_wilayah PRIMARY KEY (kode_wilayah)
);
COMMENT ON TABLE referensi_wilayah IS 'Hierarchical administrative region reference (province, regency, district, village).';

-- 2. referensi_dokumen_koperasi - Document type reference
CREATE TABLE referensi_dokumen_koperasi (
    jenis_dokumen_ref   TEXT        NOT NULL,
    nama_dokumen        TEXT        NULL,
    dibuat_pada         TIMESTAMP   NULL,
    diperbarui_pada     TIMESTAMP   NULL,
    CONSTRAINT pk_referensi_dokumen_koperasi PRIMARY KEY (jenis_dokumen_ref)
);
COMMENT ON TABLE referensi_dokumen_koperasi IS 'Reference list of cooperative document types.';

-- 3. referensi_gerai_koperasi - Outlet type reference
CREATE TABLE referensi_gerai_koperasi (
    jenis_gerai_ref     TEXT        NOT NULL,
    nama_jenis_gerai    TEXT        NULL,
    dibuat_pada         TIMESTAMP   NULL,
    diperbarui_pada     TIMESTAMP   NULL,
    CONSTRAINT pk_referensi_gerai_koperasi PRIMARY KEY (jenis_gerai_ref)
);
COMMENT ON TABLE referensi_gerai_koperasi IS 'Reference list of cooperative outlet/store types.';

-- 4. referensi_komoditas_desa - Village commodity reference
CREATE TABLE referensi_komoditas_desa (
    komoditas_ref           TEXT        NOT NULL,
    kode_wilayah            TEXT        NOT NULL,
    nama_komoditas          TEXT        NULL,
    luas_area               TEXT        NULL,
    volume                  TEXT        NULL,
    jumlah_sdm_terlibat     REAL        NULL,
    nilai_potensi_desa      BIGINT      NULL,
    dibuat_pada             TIMESTAMP   NULL,
    diperbarui_pada         TIMESTAMP   NULL,
    CONSTRAINT pk_referensi_komoditas_desa PRIMARY KEY (komoditas_ref),
    CONSTRAINT fk_komoditas_desa_wilayah FOREIGN KEY (kode_wilayah)
        REFERENCES referensi_wilayah (kode_wilayah)
);
COMMENT ON TABLE referensi_komoditas_desa IS 'Village commodity potential data linked to administrative region.';

-- 5. referensi_profil_desa - Village profile reference
CREATE TABLE referensi_profil_desa (
    kode_wilayah            TEXT        NOT NULL,
    tahun_populasi          INTEGER     NULL,
    total_penduduk          INTEGER     NULL,
    penduduk_laki_laki      INTEGER     NULL,
    penduduk_perempuan      INTEGER     NULL,
    tahun_pendanaan         INTEGER     NULL,
    anggaran_dana_desa      NUMERIC     NULL,
    dibuat_pada             TIMESTAMP   NULL,
    diperbarui_pada         TIMESTAMP   NULL,
    CONSTRAINT pk_referensi_profil_desa PRIMARY KEY (kode_wilayah),
    CONSTRAINT fk_profil_desa_wilayah FOREIGN KEY (kode_wilayah)
        REFERENCES referensi_wilayah (kode_wilayah)
);
COMMENT ON TABLE referensi_profil_desa IS 'Village demographic profile and budget data. Parent 1 : Child 0..1 to referensi_wilayah.';

-- ============================================================================
-- PHASE 2: COOPERATIVE HUB TABLES
-- ============================================================================

-- 6. referensi_koperasi_wilayah - Cooperative-Region mapping (CENTRAL HUB)
CREATE TABLE referensi_koperasi_wilayah (
    koperasi_ref    TEXT        NOT NULL,
    kode_wilayah    TEXT        NULL,
    dibuat_pada     TIMESTAMP   NULL,
    diperbarui_pada TIMESTAMP   NULL,
    CONSTRAINT pk_referensi_koperasi_wilayah PRIMARY KEY (koperasi_ref),
    CONSTRAINT fk_koperasi_wilayah_wilayah FOREIGN KEY (kode_wilayah)
        REFERENCES referensi_wilayah (kode_wilayah)
);
COMMENT ON TABLE referensi_koperasi_wilayah IS 'CENTRAL HUB: Maps every cooperative to its administrative region. Referenced by nearly all transaction/master tables.';

-- 7. profil_koperasi - Cooperative profile (1:0..1 extension of referensi_koperasi_wilayah)
CREATE TABLE profil_koperasi (
    koperasi_ref            TEXT        NOT NULL,
    nama_koperasi           TEXT        NULL,
    status_registrasi       TEXT        NULL,
    bentuk_koperasi         TEXT        NULL,
    kategori_usaha          TEXT        NULL,
    nik_koperasi            TEXT        NULL,
    alamat_lengkap          TEXT        NULL,
    kode_pos                TEXT        NULL,
    koordinat_dibulatkan    TEXT        NULL,
    modal_awal              TEXT        NULL,
    sumber_persetujuan      TEXT        NULL,
    tentang_koperasi        TEXT        NULL,
    pola_pengelolaan        TEXT        NULL,
    metode_pengisian        TEXT        NULL,
    dibuat_pada             TIMESTAMP   NULL,
    diperbarui_pada         TIMESTAMP   NULL,
    CONSTRAINT pk_profil_koperasi PRIMARY KEY (koperasi_ref),
    CONSTRAINT fk_profil_koperasi FOREIGN KEY (koperasi_ref)
        REFERENCES referensi_koperasi_wilayah (koperasi_ref)
);
COMMENT ON TABLE profil_koperasi IS 'Detailed cooperative profile. Parent 1 : Child 0..1 to referensi_koperasi_wilayah.';

-- ============================================================================
-- PHASE 3: COOPERATIVE ENTITY TABLES (depend on koperasi_wilayah)
-- ============================================================================

-- 8. akun_bank_koperasi - Cooperative bank accounts
CREATE TABLE akun_bank_koperasi (
    akun_bank_ref   TEXT        NOT NULL,
    koperasi_ref    TEXT        NOT NULL,
    nama_rekening   TEXT        NULL,
    nama_bank       TEXT        NULL,
    dibuat_pada     TIMESTAMP   NULL,
    diperbarui_pada TIMESTAMP   NULL,
    CONSTRAINT pk_akun_bank_koperasi PRIMARY KEY (akun_bank_ref),
    CONSTRAINT fk_akun_bank_koperasi FOREIGN KEY (koperasi_ref)
        REFERENCES referensi_koperasi_wilayah (koperasi_ref)
);
COMMENT ON TABLE akun_bank_koperasi IS 'Cooperative bank account information. Standardize nama_bank values before aggregation.';

-- 9. anggota_koperasi - Cooperative members
CREATE TABLE anggota_koperasi (
    anggota_ref         TEXT        NOT NULL,
    koperasi_ref        TEXT        NOT NULL,
    nama                TEXT        NULL,
    nik                 TEXT        NULL,
    kode_wilayah        TEXT        NULL,
    jenis_kelamin       TEXT        NULL,
    status_keanggotaan  TEXT        NULL,
    tanggal_terdaftar   DATE        NULL,
    dibuat_pada         TIMESTAMP   NULL,
    diperbarui_pada     TIMESTAMP   NULL,
    file_ktp            TEXT        NULL,
    status_akun         TEXT        NULL,
    pekerjaan           TEXT        NULL,
    CONSTRAINT pk_anggota_koperasi PRIMARY KEY (anggota_ref),
    CONSTRAINT fk_anggota_koperasi FOREIGN KEY (koperasi_ref)
        REFERENCES referensi_koperasi_wilayah (koperasi_ref),
    CONSTRAINT fk_anggota_wilayah FOREIGN KEY (kode_wilayah)
        REFERENCES referensi_wilayah (kode_wilayah)
);
COMMENT ON TABLE anggota_koperasi IS 'Cooperative members. NIK values are masked for privacy.';

-- 10. aset_koperasi - Cooperative assets
CREATE TABLE aset_koperasi (
    aset_ref            TEXT        NOT NULL,
    koperasi_ref        TEXT        NOT NULL,
    nama_aset           TEXT        NULL,
    tipe_aset           TEXT        NULL,
    status              TEXT        NULL,
    progres_pembangunan NUMERIC     NULL,
    foto_utama          TEXT        NULL,
    foto_sekunder       TEXT        NULL,
    dokumen_utama       TEXT        NULL,
    dokumen_sekunder    TEXT        NULL,
    dokumen_lainnya     TEXT        NULL,
    luas_lahan          NUMERIC     NULL,
    panjang_lahan       NUMERIC     NULL,
    lebar_lahan         NUMERIC     NULL,
    akses_jalan         TEXT        NULL,
    koordinat_dibulatkan TEXT       NULL,
    dibuat_pada         TIMESTAMP   NULL,
    diperbarui_pada     TIMESTAMP   NULL,
    CONSTRAINT pk_aset_koperasi PRIMARY KEY (aset_ref),
    CONSTRAINT fk_aset_koperasi FOREIGN KEY (koperasi_ref)
        REFERENCES referensi_koperasi_wilayah (koperasi_ref)
);
COMMENT ON TABLE aset_koperasi IS 'Cooperative asset records. tipe_aset categories: BMDes, BMD, Hibah. progres_pembangunan range: 0-100.';

-- 11. dokumen_koperasi - Cooperative documents
CREATE TABLE dokumen_koperasi (
    dokumen_ref             TEXT        NOT NULL,
    koperasi_ref            TEXT        NOT NULL,
    jenis_dokumen_ref       TEXT        NOT NULL,
    nomor                   TEXT        NULL,
    tanggal_berlaku         DATE        NULL,
    tanggal_kadaluarsa      DATE        NULL,
    alamat_pada_dokumen     TEXT        NULL,
    unggahan_dokumen        TEXT        NULL,
    dibuat_pada             TIMESTAMP   NULL,
    diperbarui_pada         TIMESTAMP   NULL,
    CONSTRAINT pk_dokumen_koperasi PRIMARY KEY (dokumen_ref),
    CONSTRAINT fk_dokumen_koperasi FOREIGN KEY (koperasi_ref)
        REFERENCES referensi_koperasi_wilayah (koperasi_ref),
    CONSTRAINT fk_dokumen_jenis FOREIGN KEY (jenis_dokumen_ref)
        REFERENCES referensi_dokumen_koperasi (jenis_dokumen_ref)
);
COMMENT ON TABLE dokumen_koperasi IS 'Cooperative legal/administrative documents.';

-- 12. gerai_koperasi - Cooperative outlets/stores
CREATE TABLE gerai_koperasi (
    gerai_ref                       TEXT        NOT NULL,
    koperasi_ref                    TEXT        NOT NULL,
    jenis_gerai_ref                 TEXT        NOT NULL,
    status_gerai                    TEXT        NULL,
    foto_gerai                      TEXT        NULL,
    pengisi                         TEXT        NULL,
    akses_internet                  TEXT        NULL,
    akses_listrik                   TEXT        NULL,
    status_kepemilikan_aset_gerai   TEXT        NULL,
    status_pemanfaatan_aset_gerai   TEXT        NULL,
    sumber_air_bersih               TEXT        NULL,
    jenis_bangunan                  TEXT        NULL,
    koordinat_dibulatkan            TEXT        NULL,
    dibuat_pada                     TIMESTAMP   NULL,
    diperbarui_pada                 TIMESTAMP   NULL,
    CONSTRAINT pk_gerai_koperasi PRIMARY KEY (gerai_ref),
    CONSTRAINT fk_gerai_koperasi FOREIGN KEY (koperasi_ref)
        REFERENCES referensi_koperasi_wilayah (koperasi_ref),
    CONSTRAINT fk_gerai_jenis FOREIGN KEY (jenis_gerai_ref)
        REFERENCES referensi_gerai_koperasi (jenis_gerai_ref)
);
COMMENT ON TABLE gerai_koperasi IS 'Cooperative retail outlets with infrastructure details.';

-- 13. karyawan_koperasi - Cooperative employees
CREATE TABLE karyawan_koperasi (
    karyawan_ref        TEXT        NOT NULL,
    koperasi_ref        TEXT        NOT NULL,
    nama                TEXT        NULL,
    jabatan             TEXT        NULL,
    nomor_hp_karyawan   TEXT        NULL,
    jenis_kelamin       TEXT        NULL,
    nik                 TEXT        NULL,
    email               TEXT        NULL,
    status_karyawan     TEXT        NULL,
    dibuat_pada         TIMESTAMP   NULL,
    diperbarui_pada     TIMESTAMP   NULL,
    CONSTRAINT pk_karyawan_koperasi PRIMARY KEY (karyawan_ref),
    CONSTRAINT fk_karyawan_koperasi FOREIGN KEY (koperasi_ref)
        REFERENCES referensi_koperasi_wilayah (koperasi_ref)
);
COMMENT ON TABLE karyawan_koperasi IS 'Cooperative employee records.';

-- 14. kbli_koperasi - KBLI business classification
CREATE TABLE kbli_koperasi (
    __row_id            INTEGER     NOT NULL,
    koperasi_ref        TEXT        NOT NULL,
    kode_kbli           TEXT        NULL,
    nama_kbli           TEXT        NULL,
    tipe_izin_usaha     TEXT        NULL,
    tahun_kbli          SMALLINT    NULL,
    dibuat_pada         TIMESTAMP   NULL,
    diperbarui_pada     TIMESTAMP   NULL,
    CONSTRAINT pk_kbli_koperasi PRIMARY KEY (__row_id),
    CONSTRAINT fk_kbli_koperasi FOREIGN KEY (koperasi_ref)
        REFERENCES referensi_koperasi_wilayah (koperasi_ref)
);
COMMENT ON TABLE kbli_koperasi IS 'KBLI (Indonesia Standard Industrial Classification) codes assigned to cooperatives.';

-- 15. modal_koperasi - Cooperative capital/funding
CREATE TABLE modal_koperasi (
    modal_ref           TEXT        NOT NULL,
    koperasi_ref        TEXT        NOT NULL,
    nomor_perjanjian    TEXT        NULL,
    tipe_sumber         TEXT        NULL,
    nama_sumber         TEXT        NULL,
    tipe_modal          TEXT        NULL,
    jumlah              NUMERIC     NULL,
    tanggal_diterima    DATE        NULL,
    file_perjanjian     TEXT        NULL,
    dibuat_pada         TIMESTAMP   NULL,
    diperbarui_pada     TIMESTAMP   NULL,
    CONSTRAINT pk_modal_koperasi PRIMARY KEY (modal_ref),
    CONSTRAINT fk_modal_koperasi FOREIGN KEY (koperasi_ref)
        REFERENCES referensi_koperasi_wilayah (koperasi_ref)
);
COMMENT ON TABLE modal_koperasi IS 'Cooperative capital sources and funding agreements.';

-- 16. pengajuan_domain - Domain registration requests
CREATE TABLE pengajuan_domain (
    domain_ref          TEXT        NOT NULL,
    koperasi_ref        TEXT        NOT NULL,
    domain_koperasi     TEXT        NULL,
    status_verifikasi   TEXT        NULL,
    status_domain       TEXT        NULL,
    dibuat_pada         TIMESTAMP   NULL,
    diperbarui_pada     TIMESTAMP   NULL,
    CONSTRAINT pk_pengajuan_domain PRIMARY KEY (domain_ref),
    CONSTRAINT fk_pengajuan_domain FOREIGN KEY (koperasi_ref)
        REFERENCES referensi_koperasi_wilayah (koperasi_ref)
);
COMMENT ON TABLE pengajuan_domain IS 'Cooperative website domain registration submissions.';

-- 17. pengajuan_kemitraan - Partnership applications
CREATE TABLE pengajuan_kemitraan (
    pengajuan_kemitraan_ref TEXT        NOT NULL,
    koperasi_ref            TEXT        NOT NULL,
    nik                     TEXT        NULL,
    penanggung_jawab        TEXT        NULL,
    nomor_penanggung_jawab  TEXT        NULL,
    status_permohonan       TEXT        NULL,
    bisnis_kemitraan        TEXT        NULL,
    paket_kemitraan         TEXT        NULL,
    formulir_permohonan     TEXT        NULL,
    ktp_penanggung_jawab    TEXT        NULL,
    tipe_kemitraan          TEXT        NULL,
    catatan                 TEXT        NULL,
    dibuat_pada             TIMESTAMP   NULL,
    diperbarui_pada         TIMESTAMP   NULL,
    CONSTRAINT pk_pengajuan_kemitraan PRIMARY KEY (pengajuan_kemitraan_ref),
    CONSTRAINT fk_pengajuan_kemitraan FOREIGN KEY (koperasi_ref)
        REFERENCES referensi_koperasi_wilayah (koperasi_ref)
);
COMMENT ON TABLE pengajuan_kemitraan IS 'Partnership application submissions.';

-- 18. pengajuan_pembiayaan - Financing applications
CREATE TABLE pengajuan_pembiayaan (
    pengajuan_pembiayaan_ref        TEXT        NOT NULL,
    koperasi_ref                    TEXT        NOT NULL,
    nik                             TEXT        NULL,
    penanggung_jawab                TEXT        NULL,
    nomor_penanggung_jawab          TEXT        NULL,
    status_permohonan               TEXT        NULL,
    formulir_permohonan_pembiayaan  TEXT        NULL,
    nominal_permohonan              REAL        NULL,
    tenor                           INTEGER     NULL,
    tujuan_permohonan               TEXT        NULL,
    dibuat_pada                     TIMESTAMP   NULL,
    diperbarui_pada                 TIMESTAMP   NULL,
    CONSTRAINT pk_pengajuan_pembiayaan PRIMARY KEY (pengajuan_pembiayaan_ref),
    CONSTRAINT fk_pengajuan_pembiayaan FOREIGN KEY (koperasi_ref)
        REFERENCES referensi_koperasi_wilayah (koperasi_ref)
);
COMMENT ON TABLE pengajuan_pembiayaan IS 'Financing/loan application submissions.';

-- 19. pengajuan_rekening_bank - Bank account opening requests
CREATE TABLE pengajuan_rekening_bank (
    pengajuan_rekening_ref  TEXT        NOT NULL,
    koperasi_ref            TEXT        NOT NULL,
    nik                     TEXT        NULL,
    penanggung_jawab        TEXT        NULL,
    nomor_penanggung_jawab  TEXT        NULL,
    status                  TEXT        NULL,
    kode_bank               TEXT        NULL,
    nama_bank               TEXT        NULL,
    dibuat_pada             TIMESTAMP   NULL,
    diperbarui_pada         TIMESTAMP   NULL,
    CONSTRAINT pk_pengajuan_rekening_bank PRIMARY KEY (pengajuan_rekening_ref),
    CONSTRAINT fk_pengajuan_rekening_bank FOREIGN KEY (koperasi_ref)
        REFERENCES referensi_koperasi_wilayah (koperasi_ref)
);
COMMENT ON TABLE pengajuan_rekening_bank IS 'Bank account opening request submissions.';

-- 20. pengurus_koperasi - Cooperative board/management
CREATE TABLE pengurus_koperasi (
    pengurus_ref        TEXT        NOT NULL,
    koperasi_ref        TEXT        NOT NULL,
    nama                TEXT        NULL,
    jabatan             TEXT        NULL,
    status              TEXT        NULL,
    no_hp               TEXT        NULL,
    nik                 TEXT        NULL,
    jenis_kelamin       TEXT        NULL,
    foto_profil         TEXT        NULL,
    email               TEXT        NULL,
    alamat              TEXT        NULL,
    kode_pos            TEXT        NULL,
    tanggal_lahir       TEXT        NULL,
    status_pendidikan   TEXT        NULL,
    periode_mulai       TEXT        NULL,
    periode_selesai     DATE        NULL,
    file_ktp            TEXT        NULL,
    sumber_data         TEXT        NULL,
    dibuat_pada         TIMESTAMP   NULL,
    diperbarui_pada     TIMESTAMP   NULL,
    CONSTRAINT pk_pengurus_koperasi PRIMARY KEY (pengurus_ref),
    CONSTRAINT fk_pengurus_koperasi FOREIGN KEY (koperasi_ref)
        REFERENCES referensi_koperasi_wilayah (koperasi_ref)
);
COMMENT ON TABLE pengurus_koperasi IS 'Cooperative board members, management, and authorized personnel.';

-- 21. rat_koperasi - Annual Member Meeting records
CREATE TABLE rat_koperasi (
    rat_sample_id               TEXT        NOT NULL,
    koperasi_ref                TEXT        NOT NULL,
    jenis_sektor_koperasi       TEXT        NULL,
    urutan_rat                  TEXT        NULL,
    tahun_buku                  SMALLINT    NULL,
    tahun_rencana_kerja         SMALLINT    NULL,
    tahun_rencana_anggaran      SMALLINT    NULL,
    tanggal_rat                 DATE        NULL,
    jumlah_peserta_rat          INTEGER     NULL,
    status_rat                  TEXT        NULL,
    tahap_rat                   TEXT        NULL,
    laporan_posisi_keuangan     TEXT        NULL,
    laporan_hasil_usaha         TEXT        NULL,
    rapb_posisi_keuangan        TEXT        NULL,
    rapb_hasil_usaha            TEXT        NULL,
    dibuat_pada                 TIMESTAMP   NULL,
    diperbarui_pada             TIMESTAMP   NULL,
    CONSTRAINT pk_rat_koperasi PRIMARY KEY (rat_sample_id),
    CONSTRAINT fk_rat_koperasi FOREIGN KEY (koperasi_ref)
        REFERENCES referensi_koperasi_wilayah (koperasi_ref)
);
COMMENT ON TABLE rat_koperasi IS 'Rapat Anggota Tahunan (Annual Member Meeting) records with financial report references.';

-- ============================================================================
-- PHASE 4: PRODUCT & INVENTORY TABLES
-- ============================================================================

-- 22. produk_koperasi - Cooperative products catalog
CREATE TABLE produk_koperasi (
    produk_sample_id    TEXT        NOT NULL,
    koperasi_ref        TEXT        NOT NULL,
    kode_barcode        TEXT        NULL,
    nama_produk         TEXT        NULL,
    unit                TEXT        NULL,
    dibuat_pada         TIMESTAMP   NULL,
    diperbarui_pada     TIMESTAMP   NULL,
    CONSTRAINT pk_produk_koperasi PRIMARY KEY (produk_sample_id),
    CONSTRAINT fk_produk_koperasi FOREIGN KEY (koperasi_ref)
        REFERENCES referensi_koperasi_wilayah (koperasi_ref)
);
COMMENT ON TABLE produk_koperasi IS 'Cooperative product catalog master.';

-- 23. inventaris_produk - Product inventory
CREATE TABLE inventaris_produk (
    inventaris_ref      TEXT        NOT NULL,
    produk_sample_id    TEXT        NOT NULL,
    koperasi_ref        TEXT        NOT NULL,
    nama_produk         TEXT        NULL,
    stok                NUMERIC     NULL,
    dibuat_pada         TIMESTAMP   NULL,
    diperbarui_pada     TIMESTAMP   NULL,
    kode_barcode        TEXT        NULL,
    CONSTRAINT pk_inventaris_produk PRIMARY KEY (inventaris_ref),
    CONSTRAINT fk_inventaris_koperasi FOREIGN KEY (koperasi_ref)
        REFERENCES referensi_koperasi_wilayah (koperasi_ref),
    CONSTRAINT fk_inventaris_produk FOREIGN KEY (produk_sample_id)
        REFERENCES produk_koperasi (produk_sample_id)
);
COMMENT ON TABLE inventaris_produk IS 'Product inventory tracking per cooperative.';

-- 24. barang_masuk_produk - Inbound goods
CREATE TABLE barang_masuk_produk (
    barang_masuk_ref    TEXT        NOT NULL,
    produk_sample_id    TEXT        NOT NULL,
    koperasi_ref        TEXT        NOT NULL,
    kode_barcode        TEXT        NULL,
    nama_produk         TEXT        NULL,
    nama_tampilan       TEXT        NULL,
    jumlah_masuk        NUMERIC     NULL,
    jumlah_tersedia     NUMERIC     NULL,
    harga_beli          NUMERIC     NULL,
    harga_jual          NUMERIC     NULL,
    total_biaya         NUMERIC     NULL,
    keterangan          TEXT        NULL,
    status              TEXT        NULL,
    tanggal_masuk       TIMESTAMP   NULL,
    dibuat_pada         TIMESTAMP   NULL,
    diperbarui_pada     TIMESTAMP   NULL,
    CONSTRAINT pk_barang_masuk_produk PRIMARY KEY (barang_masuk_ref),
    CONSTRAINT fk_barang_masuk_koperasi FOREIGN KEY (koperasi_ref)
        REFERENCES referensi_koperasi_wilayah (koperasi_ref),
    CONSTRAINT fk_barang_masuk_produk FOREIGN KEY (produk_sample_id)
        REFERENCES produk_koperasi (produk_sample_id)
);
COMMENT ON TABLE barang_masuk_produk IS 'Inbound goods/stock receipts.';

-- ============================================================================
-- PHASE 5: TRANSACTION TABLES
-- ============================================================================

-- 25. transaksi_penjualan - Sales transactions
CREATE TABLE transaksi_penjualan (
    transaksi_sample_id TEXT        NOT NULL,
    koperasi_ref        TEXT        NOT NULL,
    nama_pelanggan      TEXT        NULL,
    tanggal_dibuat      TIMESTAMP   NULL,
    total_pembayaran    NUMERIC     NULL,
    status_transaksi    TEXT        NULL,
    metode_pembayaran   TEXT        NULL,
    dibuat_pada         TIMESTAMP   NULL,
    diperbarui_pada     TIMESTAMP   NULL,
    CONSTRAINT pk_transaksi_penjualan PRIMARY KEY (transaksi_sample_id),
    CONSTRAINT fk_transaksi_penjualan FOREIGN KEY (koperasi_ref)
        REFERENCES referensi_koperasi_wilayah (koperasi_ref)
);
COMMENT ON TABLE transaksi_penjualan IS 'Sales transaction headers.';

-- 26. barang_keluar_produk - Outbound goods (sales line items)
CREATE TABLE barang_keluar_produk (
    __row_id                INTEGER     NOT NULL,
    transaksi_sample_id     TEXT        NOT NULL,
    produk_sample_id        TEXT        NOT NULL,
    koperasi_ref            TEXT        NOT NULL,
    kode_barcode            TEXT        NULL,
    tanggal_keluar          TIMESTAMP   NULL,
    status                  TEXT        NULL,
    nama_produk             TEXT        NULL,
    nama_tampilan           TEXT        NULL,
    jumlah_keluar           NUMERIC     NULL,
    harga                   NUMERIC     NULL,
    total_nilai             NUMERIC     NULL,
    status_transaksi        TEXT        NULL,
    dibuat_pada             TIMESTAMP   NULL,
    diperbarui_pada         TIMESTAMP   NULL,
    CONSTRAINT pk_barang_keluar_produk PRIMARY KEY (__row_id),
    CONSTRAINT fk_barang_keluar_koperasi FOREIGN KEY (koperasi_ref)
        REFERENCES referensi_koperasi_wilayah (koperasi_ref),
    CONSTRAINT fk_barang_keluar_produk FOREIGN KEY (produk_sample_id)
        REFERENCES produk_koperasi (produk_sample_id),
    CONSTRAINT fk_barang_keluar_transaksi FOREIGN KEY (transaksi_sample_id)
        REFERENCES transaksi_penjualan (transaksi_sample_id)
);
COMMENT ON TABLE barang_keluar_produk IS 'Outbound goods / sales line items. Links sales transaction to products.';

-- ============================================================================
-- PHASE 6: MEMBER SAVINGS
-- ============================================================================

-- 27. simpanan_anggota - Member savings/deposits
CREATE TABLE simpanan_anggota (
    simpanan_ref        TEXT        NOT NULL,
    koperasi_ref        TEXT        NOT NULL,
    anggota_ref         TEXT        NOT NULL,
    periode_pembayaran  TEXT        NULL,
    jumlah_simpanan     NUMERIC     NULL,
    status              TEXT        NULL,
    dibuat_pada         TIMESTAMP   NULL,
    dibayar_pada        TIMESTAMP   NULL,
    CONSTRAINT pk_simpanan_anggota PRIMARY KEY (simpanan_ref),
    CONSTRAINT fk_simpanan_koperasi FOREIGN KEY (koperasi_ref)
        REFERENCES referensi_koperasi_wilayah (koperasi_ref),
    CONSTRAINT fk_simpanan_anggota FOREIGN KEY (anggota_ref)
        REFERENCES anggota_koperasi (anggota_ref)
);
COMMENT ON TABLE simpanan_anggota IS 'Member savings/deposit records.';

-- ============================================================================
-- INDEXES for common join patterns
-- ============================================================================
CREATE INDEX idx_akun_bank_koperasi_ref     ON akun_bank_koperasi (koperasi_ref);
CREATE INDEX idx_anggota_koperasi_ref       ON anggota_koperasi (koperasi_ref);
CREATE INDEX idx_anggota_wilayah            ON anggota_koperasi (kode_wilayah);
CREATE INDEX idx_aset_koperasi_ref          ON aset_koperasi (koperasi_ref);
CREATE INDEX idx_dokumen_koperasi_ref       ON dokumen_koperasi (koperasi_ref);
CREATE INDEX idx_gerai_koperasi_ref         ON gerai_koperasi (koperasi_ref);
CREATE INDEX idx_karyawan_koperasi_ref      ON karyawan_koperasi (koperasi_ref);
CREATE INDEX idx_kbli_koperasi_ref          ON kbli_koperasi (koperasi_ref);
CREATE INDEX idx_modal_koperasi_ref         ON modal_koperasi (koperasi_ref);
CREATE INDEX idx_produk_koperasi_ref        ON produk_koperasi (koperasi_ref);
CREATE INDEX idx_inventaris_koperasi_ref    ON inventaris_produk (koperasi_ref);
CREATE INDEX idx_inventaris_produk_ref      ON inventaris_produk (produk_sample_id);
CREATE INDEX idx_barang_masuk_koperasi_ref  ON barang_masuk_produk (koperasi_ref);
CREATE INDEX idx_barang_masuk_produk_ref    ON barang_masuk_produk (produk_sample_id);
CREATE INDEX idx_barang_keluar_koperasi_ref ON barang_keluar_produk (koperasi_ref);
CREATE INDEX idx_barang_keluar_produk_ref   ON barang_keluar_produk (produk_sample_id);
CREATE INDEX idx_barang_keluar_transaksi    ON barang_keluar_produk (transaksi_sample_id);
CREATE INDEX idx_transaksi_koperasi_ref     ON transaksi_penjualan (koperasi_ref);
CREATE INDEX idx_simpanan_koperasi_ref      ON simpanan_anggota (koperasi_ref);
CREATE INDEX idx_simpanan_anggota_ref       ON simpanan_anggota (anggota_ref);
CREATE INDEX idx_rat_koperasi_ref           ON rat_koperasi (koperasi_ref);
CREATE INDEX idx_pengurus_koperasi_ref      ON pengurus_koperasi (koperasi_ref);
CREATE INDEX idx_koperasi_wilayah_wil       ON referensi_koperasi_wilayah (kode_wilayah);
CREATE INDEX idx_komoditas_desa_wilayah     ON referensi_komoditas_desa (kode_wilayah);
