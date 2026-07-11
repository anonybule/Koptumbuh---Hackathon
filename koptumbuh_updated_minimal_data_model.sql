-- ============================================================================
-- KopTumbuh - Updated Minimal Data Model
-- PostgreSQL 15+
--
-- Purpose:
--   1. Reproduce the SIMKOPDES-compatible core entities described in
--      metadata_database_hackathon_final.
--   2. Add the minimum operational extensions required for the KopTumbuh
--      WhatsApp -> validation -> transaction -> insight workflow.
--   3. Keep direct production SIMKOPDES integration out of scope; this schema
--      supports export/mapping first, then authorized API integration later.
--
-- Notes:
--   - All timestamps use TIMESTAMPTZ and should be written in the cooperative's
--     local timezone, normally Asia/Jakarta, then stored by PostgreSQL in UTC.
--   - Status columns remain TEXT where source metadata contains mixed values.
--   - Sensitive data should be minimized, masked in non-production environments,
--     and protected with role-based access.
-- ============================================================================

BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE SCHEMA IF NOT EXISTS koptumbuh;
SET search_path = koptumbuh, public;

-- ----------------------------------------------------------------------------
-- Helper function
-- ----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION set_diperbarui_pada()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.diperbarui_pada = NOW();
    RETURN NEW;
END;
$$;

-- ============================================================================
-- A. MASTER & REFERENCE
-- ============================================================================

CREATE TABLE IF NOT EXISTS referensi_wilayah (
    kode_wilayah            TEXT PRIMARY KEY,
    provinsi                TEXT,
    kab_kota                TEXT,
    kecamatan               TEXT,
    desa_kelurahan          TEXT,
    dibuat_pada             TIMESTAMPTZ DEFAULT NOW(),
    diperbarui_pada         TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS referensi_koperasi_wilayah (
    koperasi_ref            TEXT PRIMARY KEY,
    kode_wilayah            TEXT REFERENCES referensi_wilayah(kode_wilayah),
    dibuat_pada             TIMESTAMPTZ DEFAULT NOW(),
    diperbarui_pada         TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS referensi_dokumen_koperasi (
    jenis_dokumen_ref       TEXT PRIMARY KEY,
    nama_dokumen            TEXT,
    dibuat_pada             TIMESTAMPTZ DEFAULT NOW(),
    diperbarui_pada         TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS referensi_gerai_koperasi (
    jenis_gerai_ref         TEXT PRIMARY KEY,
    nama_jenis_gerai        TEXT,
    dibuat_pada             TIMESTAMPTZ DEFAULT NOW(),
    diperbarui_pada         TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- B. IDENTITY & COOPERATIVE ORGANIZATION
-- ============================================================================

CREATE TABLE IF NOT EXISTS profil_koperasi (
    koperasi_ref            TEXT PRIMARY KEY
                             REFERENCES referensi_koperasi_wilayah(koperasi_ref),
    nama_koperasi           TEXT,
    status_registrasi       TEXT,
    bentuk_koperasi         TEXT,
    kategori_usaha          TEXT,
    nik_koperasi            TEXT,
    alamat_lengkap          TEXT,
    kode_pos                TEXT,
    koordinat_dibulatkan    TEXT,
    modal_awal              TEXT,
    sumber_persetujuan      TEXT,
    tentang_koperasi        TEXT,
    pola_pengelolaan        TEXT,
    metode_pengisian        TEXT,
    dibuat_pada             TIMESTAMPTZ DEFAULT NOW(),
    diperbarui_pada         TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS pengurus_koperasi (
    pengurus_ref            TEXT PRIMARY KEY,
    koperasi_ref            TEXT NOT NULL
                             REFERENCES referensi_koperasi_wilayah(koperasi_ref),
    nama                    TEXT,
    jabatan                 TEXT,
    status                  TEXT,
    no_hp                   TEXT,
    nik                     TEXT,
    jenis_kelamin           TEXT,
    foto_profil             TEXT,
    email                   TEXT,
    alamat                  TEXT,
    kode_pos                TEXT,
    tanggal_lahir           TEXT,
    status_pendidikan       TEXT,
    periode_mulai           TEXT,
    periode_selesai         DATE,
    file_ktp                TEXT,
    sumber_data             TEXT,
    dibuat_pada             TIMESTAMPTZ DEFAULT NOW(),
    diperbarui_pada         TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS karyawan_koperasi (
    karyawan_ref            TEXT PRIMARY KEY,
    koperasi_ref            TEXT NOT NULL
                             REFERENCES referensi_koperasi_wilayah(koperasi_ref),
    nama                    TEXT,
    jabatan                 TEXT,
    nomor_hp_karyawan       TEXT,
    jenis_kelamin           TEXT,
    nik                     TEXT,
    email                   TEXT,
    status_karyawan         TEXT,
    dibuat_pada             TIMESTAMPTZ DEFAULT NOW(),
    diperbarui_pada         TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS dokumen_koperasi (
    dokumen_ref             TEXT PRIMARY KEY,
    koperasi_ref            TEXT NOT NULL
                             REFERENCES referensi_koperasi_wilayah(koperasi_ref),
    jenis_dokumen_ref       TEXT NOT NULL
                             REFERENCES referensi_dokumen_koperasi(jenis_dokumen_ref),
    nomor                   TEXT,
    tanggal_berlaku         DATE,
    tanggal_kadaluarsa      DATE,
    alamat_pada_dokumen     TEXT,
    unggahan_dokumen        TEXT,
    dibuat_pada             TIMESTAMPTZ DEFAULT NOW(),
    diperbarui_pada         TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT ck_dokumen_tanggal
        CHECK (
            tanggal_kadaluarsa IS NULL
            OR tanggal_berlaku IS NULL
            OR tanggal_kadaluarsa >= tanggal_berlaku
        )
);

CREATE TABLE IF NOT EXISTS kbli_koperasi (
    __row_id                BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    koperasi_ref            TEXT NOT NULL
                             REFERENCES referensi_koperasi_wilayah(koperasi_ref),
    kode_kbli               TEXT,
    nama_kbli               TEXT,
    tipe_izin_usaha         TEXT,
    tahun_kbli              SMALLINT,
    dibuat_pada             TIMESTAMPTZ DEFAULT NOW(),
    diperbarui_pada         TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS aset_koperasi (
    aset_ref                TEXT PRIMARY KEY,
    koperasi_ref            TEXT NOT NULL
                             REFERENCES referensi_koperasi_wilayah(koperasi_ref),
    nama_aset               TEXT,
    tipe_aset               TEXT,
    status                  TEXT,
    progres_pembangunan     NUMERIC(5,2),
    foto_utama              TEXT,
    foto_sekunder           TEXT,
    dokumen_utama           TEXT,
    dokumen_sekunder        TEXT,
    dokumen_lainnya         TEXT,
    luas_lahan              NUMERIC(18,2),
    panjang_lahan           NUMERIC(18,2),
    lebar_lahan             NUMERIC(18,2),
    akses_jalan             TEXT,
    koordinat_dibulatkan    TEXT,
    dibuat_pada             TIMESTAMPTZ DEFAULT NOW(),
    diperbarui_pada         TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT ck_aset_progres
        CHECK (
            progres_pembangunan IS NULL
            OR progres_pembangunan BETWEEN 0 AND 100
        )
);

CREATE TABLE IF NOT EXISTS gerai_koperasi (
    gerai_ref                       TEXT PRIMARY KEY,
    koperasi_ref                    TEXT NOT NULL
                                     REFERENCES referensi_koperasi_wilayah(koperasi_ref),
    jenis_gerai_ref                 TEXT NOT NULL
                                     REFERENCES referensi_gerai_koperasi(jenis_gerai_ref),
    status_gerai                    TEXT,
    foto_gerai                      TEXT,
    pengisi                         TEXT,
    akses_internet                  TEXT,
    akses_listrik                   TEXT,
    status_kepemilikan_aset_gerai   TEXT,
    status_pemanfaatan_aset_gerai   TEXT,
    sumber_air_bersih               TEXT,
    jenis_bangunan                  TEXT,
    koordinat_dibulatkan            TEXT,
    dibuat_pada                     TIMESTAMPTZ DEFAULT NOW(),
    diperbarui_pada                 TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- C. MEMBERS & PARTICIPATION
-- ============================================================================

CREATE TABLE IF NOT EXISTS anggota_koperasi (
    anggota_ref             TEXT PRIMARY KEY,
    koperasi_ref            TEXT NOT NULL
                             REFERENCES referensi_koperasi_wilayah(koperasi_ref),
    nama                    TEXT,
    nik                     TEXT,
    kode_wilayah            TEXT REFERENCES referensi_wilayah(kode_wilayah),
    jenis_kelamin           TEXT,
    status_keanggotaan      TEXT,
    tanggal_terdaftar       DATE,
    file_ktp                TEXT,
    status_akun             TEXT,
    pekerjaan               TEXT,
    dibuat_pada             TIMESTAMPTZ DEFAULT NOW(),
    diperbarui_pada         TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS simpanan_anggota (
    simpanan_ref            TEXT PRIMARY KEY,
    koperasi_ref            TEXT NOT NULL
                             REFERENCES referensi_koperasi_wilayah(koperasi_ref),
    anggota_ref             TEXT NOT NULL
                             REFERENCES anggota_koperasi(anggota_ref),
    periode_pembayaran      TEXT,
    jumlah_simpanan         NUMERIC(18,2),
    status                  TEXT,
    dibuat_pada             TIMESTAMPTZ DEFAULT NOW(),
    dibayar_pada            TIMESTAMPTZ,
    CONSTRAINT ck_simpanan_nonnegative
        CHECK (jumlah_simpanan IS NULL OR jumlah_simpanan >= 0)
);

-- ============================================================================
-- D. BUSINESS OPERATIONS
-- ============================================================================

CREATE TABLE IF NOT EXISTS produk_koperasi (
    produk_sample_id        TEXT PRIMARY KEY,
    koperasi_ref            TEXT NOT NULL
                             REFERENCES referensi_koperasi_wilayah(koperasi_ref),
    kode_barcode            TEXT,
    nama_produk             TEXT,
    unit                    TEXT,
    dibuat_pada             TIMESTAMPTZ DEFAULT NOW(),
    diperbarui_pada         TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS transaksi_penjualan (
    transaksi_sample_id     TEXT PRIMARY KEY,
    koperasi_ref            TEXT NOT NULL
                             REFERENCES referensi_koperasi_wilayah(koperasi_ref),
    nama_pelanggan          TEXT,
    tanggal_dibuat          TIMESTAMPTZ,
    total_pembayaran        NUMERIC(18,2),
    status_transaksi        TEXT,
    metode_pembayaran       TEXT,
    dibuat_pada             TIMESTAMPTZ DEFAULT NOW(),
    diperbarui_pada         TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT ck_transaksi_total_nonnegative
        CHECK (total_pembayaran IS NULL OR total_pembayaran >= 0)
);

CREATE TABLE IF NOT EXISTS barang_keluar_produk (
    __row_id                BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    transaksi_sample_id     TEXT NOT NULL
                             REFERENCES transaksi_penjualan(transaksi_sample_id),
    produk_sample_id        TEXT NOT NULL
                             REFERENCES produk_koperasi(produk_sample_id),
    koperasi_ref            TEXT NOT NULL
                             REFERENCES referensi_koperasi_wilayah(koperasi_ref),
    kode_barcode            TEXT,
    tanggal_keluar          TIMESTAMPTZ,
    status                  TEXT,
    nama_produk             TEXT,
    nama_tampilan           TEXT,
    jumlah_keluar           NUMERIC(18,3),
    harga                   NUMERIC(18,2),
    total_nilai             NUMERIC(18,2),
    status_transaksi        TEXT,
    dibuat_pada             TIMESTAMPTZ DEFAULT NOW(),
    diperbarui_pada         TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT ck_barang_keluar_qty_nonnegative
        CHECK (jumlah_keluar IS NULL OR jumlah_keluar >= 0),
    CONSTRAINT ck_barang_keluar_total_nonnegative
        CHECK (total_nilai IS NULL OR total_nilai >= 0)
);

CREATE TABLE IF NOT EXISTS barang_masuk_produk (
    barang_masuk_ref        TEXT PRIMARY KEY,
    produk_sample_id        TEXT NOT NULL
                             REFERENCES produk_koperasi(produk_sample_id),
    koperasi_ref            TEXT NOT NULL
                             REFERENCES referensi_koperasi_wilayah(koperasi_ref),
    kode_barcode            TEXT,
    nama_produk             TEXT,
    nama_tampilan           TEXT,
    jumlah_masuk            NUMERIC(18,3),
    jumlah_tersedia         NUMERIC(18,3),
    harga_beli              NUMERIC(18,2),
    harga_jual              NUMERIC(18,2),
    total_biaya             NUMERIC(18,2),
    keterangan              TEXT,
    status                  TEXT,
    tanggal_masuk           TIMESTAMPTZ,
    dibuat_pada             TIMESTAMPTZ DEFAULT NOW(),
    diperbarui_pada         TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT ck_barang_masuk_qty_nonnegative
        CHECK (
            (jumlah_masuk IS NULL OR jumlah_masuk >= 0)
            AND (jumlah_tersedia IS NULL OR jumlah_tersedia >= 0)
        )
);

CREATE TABLE IF NOT EXISTS inventaris_produk (
    inventaris_ref          TEXT PRIMARY KEY,
    produk_sample_id        TEXT NOT NULL
                             REFERENCES produk_koperasi(produk_sample_id),
    koperasi_ref            TEXT NOT NULL
                             REFERENCES referensi_koperasi_wilayah(koperasi_ref),
    nama_produk             TEXT,
    stok                    NUMERIC(18,3),
    kode_barcode            TEXT,
    dibuat_pada             TIMESTAMPTZ DEFAULT NOW(),
    diperbarui_pada         TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_inventaris_koperasi_produk
        UNIQUE (koperasi_ref, produk_sample_id)
);

-- ============================================================================
-- E. FINANCE, CAPITAL & APPLICATIONS
-- ============================================================================

CREATE TABLE IF NOT EXISTS akun_bank_koperasi (
    akun_bank_ref           TEXT PRIMARY KEY,
    koperasi_ref            TEXT NOT NULL
                             REFERENCES referensi_koperasi_wilayah(koperasi_ref),
    nama_rekening           TEXT,
    nama_bank               TEXT,
    dibuat_pada             TIMESTAMPTZ DEFAULT NOW(),
    diperbarui_pada         TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS pengajuan_rekening_bank (
    pengajuan_rekening_ref  TEXT PRIMARY KEY,
    koperasi_ref            TEXT NOT NULL
                             REFERENCES referensi_koperasi_wilayah(koperasi_ref),
    nik                     TEXT,
    penanggung_jawab        TEXT,
    nomor_penanggung_jawab  TEXT,
    status                  TEXT,
    kode_bank               TEXT,
    nama_bank               TEXT,
    dibuat_pada             TIMESTAMPTZ DEFAULT NOW(),
    diperbarui_pada         TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS modal_koperasi (
    modal_ref               TEXT PRIMARY KEY,
    koperasi_ref            TEXT NOT NULL
                             REFERENCES referensi_koperasi_wilayah(koperasi_ref),
    nomor_perjanjian        TEXT,
    tipe_sumber             TEXT,
    nama_sumber             TEXT,
    tipe_modal              TEXT,
    jumlah                  NUMERIC(18,2),
    tanggal_diterima        DATE,
    file_perjanjian         TEXT,
    dibuat_pada             TIMESTAMPTZ DEFAULT NOW(),
    diperbarui_pada         TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT ck_modal_nonnegative
        CHECK (jumlah IS NULL OR jumlah >= 0)
);

CREATE TABLE IF NOT EXISTS pengajuan_pembiayaan (
    pengajuan_pembiayaan_ref            TEXT PRIMARY KEY,
    koperasi_ref                        TEXT NOT NULL
                                         REFERENCES referensi_koperasi_wilayah(koperasi_ref),
    nik                                 TEXT,
    penanggung_jawab                    TEXT,
    nomor_penanggung_jawab              TEXT,
    status_permohonan                   TEXT,
    formulir_permohonan_pembiayaan      TEXT,
    nominal_permohonan                  NUMERIC(18,2),
    tenor                               INTEGER,
    tujuan_permohonan                   TEXT,
    dibuat_pada                         TIMESTAMPTZ DEFAULT NOW(),
    diperbarui_pada                     TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT ck_pembiayaan_nonnegative
        CHECK (
            (nominal_permohonan IS NULL OR nominal_permohonan >= 0)
            AND (tenor IS NULL OR tenor >= 0)
        )
);

CREATE TABLE IF NOT EXISTS pengajuan_kemitraan (
    pengajuan_kemitraan_ref  TEXT PRIMARY KEY,
    koperasi_ref             TEXT NOT NULL
                              REFERENCES referensi_koperasi_wilayah(koperasi_ref),
    nik                      TEXT,
    penanggung_jawab         TEXT,
    nomor_penanggung_jawab   TEXT,
    status_permohonan        TEXT,
    bisnis_kemitraan         TEXT,
    paket_kemitraan          TEXT,
    formulir_permohonan      TEXT,
    ktp_penanggung_jawab     TEXT,
    tipe_kemitraan           TEXT,
    catatan                  TEXT,
    dibuat_pada              TIMESTAMPTZ DEFAULT NOW(),
    diperbarui_pada          TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS pengajuan_domain (
    domain_ref              TEXT PRIMARY KEY,
    koperasi_ref            TEXT NOT NULL
                             REFERENCES referensi_koperasi_wilayah(koperasi_ref),
    domain_koperasi         TEXT,
    status_verifikasi       TEXT,
    status_domain           TEXT,
    dibuat_pada             TIMESTAMPTZ DEFAULT NOW(),
    diperbarui_pada         TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- F. VILLAGE POTENTIAL & GOVERNANCE
-- ============================================================================

CREATE TABLE IF NOT EXISTS referensi_komoditas_desa (
    komoditas_ref           TEXT PRIMARY KEY,
    kode_wilayah            TEXT NOT NULL
                             REFERENCES referensi_wilayah(kode_wilayah),
    nama_komoditas          TEXT,
    luas_area               TEXT,
    volume                  TEXT,
    jumlah_sdm_terlibat     NUMERIC(18,2),
    nilai_potensi_desa      BIGINT,
    dibuat_pada             TIMESTAMPTZ DEFAULT NOW(),
    diperbarui_pada         TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS referensi_profil_desa (
    kode_wilayah            TEXT PRIMARY KEY
                             REFERENCES referensi_wilayah(kode_wilayah),
    tahun_populasi          INTEGER,
    total_penduduk          INTEGER,
    penduduk_laki_laki      INTEGER,
    penduduk_perempuan      INTEGER,
    tahun_pendanaan         INTEGER,
    anggaran_dana_desa      NUMERIC(18,2),
    dibuat_pada             TIMESTAMPTZ DEFAULT NOW(),
    diperbarui_pada         TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS rat_koperasi (
    rat_sample_id               TEXT PRIMARY KEY,
    koperasi_ref                TEXT NOT NULL
                                 REFERENCES referensi_koperasi_wilayah(koperasi_ref),
    jenis_sektor_koperasi       TEXT,
    urutan_rat                  TEXT,
    tahun_buku                  SMALLINT,
    tahun_rencana_kerja         SMALLINT,
    tahun_rencana_anggaran      SMALLINT,
    tanggal_rat                 DATE,
    jumlah_peserta_rat          INTEGER,
    status_rat                  TEXT,
    tahap_rat                   TEXT,
    laporan_posisi_keuangan     JSONB,
    laporan_hasil_usaha         JSONB,
    rapb_posisi_keuangan        JSONB,
    rapb_hasil_usaha            JSONB,
    dibuat_pada                 TIMESTAMPTZ DEFAULT NOW(),
    diperbarui_pada             TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- G. KOPTUMBUH OPERATIONAL & INTELLIGENCE EXTENSIONS
-- These are not assumed to exist in production SIMKOPDES.
-- ============================================================================

CREATE TABLE IF NOT EXISTS pengguna_koptumbuh (
    pengguna_id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    koperasi_ref            TEXT NOT NULL
                             REFERENCES referensi_koperasi_wilayah(koperasi_ref),
    pengurus_ref            TEXT REFERENCES pengurus_koperasi(pengurus_ref),
    karyawan_ref            TEXT REFERENCES karyawan_koperasi(karyawan_ref),
    nama                    TEXT NOT NULL,
    nomor_whatsapp          TEXT NOT NULL,
    role                    TEXT NOT NULL
                             CHECK (role IN ('OPERATOR','KETUA','BENDAHARA','PEMBINA','ADMIN')),
    status_aktif            BOOLEAN NOT NULL DEFAULT TRUE,
    consent_at              TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_pengguna_whatsapp UNIQUE (koperasi_ref, nomor_whatsapp),
    CONSTRAINT ck_pengguna_reference
        CHECK (
            pengurus_ref IS NOT NULL
            OR karyawan_ref IS NOT NULL
            OR role IN ('PEMBINA','ADMIN')
        )
);

CREATE TABLE IF NOT EXISTS pemasok_koptumbuh (
    pemasok_id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    koperasi_ref            TEXT NOT NULL
                             REFERENCES referensi_koperasi_wilayah(koperasi_ref),
    nama_pemasok            TEXT NOT NULL,
    nomor_hp                TEXT,
    alamat                  TEXT,
    lead_time_hari          NUMERIC(8,2),
    payment_term            TEXT,
    status_aktif            BOOLEAN NOT NULL DEFAULT TRUE,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS pelanggan_koptumbuh (
    pelanggan_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    koperasi_ref            TEXT NOT NULL
                             REFERENCES referensi_koperasi_wilayah(koperasi_ref),
    anggota_ref             TEXT REFERENCES anggota_koperasi(anggota_ref),
    nama_pelanggan          TEXT NOT NULL,
    nomor_whatsapp          TEXT,
    status_aktif            BOOLEAN NOT NULL DEFAULT TRUE,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS pesan_masuk (
    pesan_id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    koperasi_ref            TEXT NOT NULL
                             REFERENCES referensi_koperasi_wilayah(koperasi_ref),
    pengguna_id             UUID NOT NULL
                             REFERENCES pengguna_koptumbuh(pengguna_id),
    whatsapp_message_id     TEXT,
    input_type              TEXT NOT NULL
                             CHECK (input_type IN ('TEXT','VOICE','PHOTO','DOCUMENT')),
    raw_text                TEXT,
    media_url               TEXT,
    media_mime_type         TEXT,
    status                  TEXT NOT NULL DEFAULT 'RECEIVED'
                             CHECK (
                                 status IN (
                                     'RECEIVED','PROCESSING','PARSED',
                                     'NEEDS_REVIEW','CONFIRMED',
                                     'CANCELLED','FAILED'
                                 )
                             ),
    received_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processed_at            TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_whatsapp_message UNIQUE (whatsapp_message_id)
);

CREATE TABLE IF NOT EXISTS parsing_pesan (
    parsing_id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pesan_id                UUID NOT NULL REFERENCES pesan_masuk(pesan_id) ON DELETE CASCADE,
    parser_version          TEXT,
    detected_intent         TEXT,
    transcription_text      TEXT,
    extracted_payload       JSONB NOT NULL DEFAULT '{}'::JSONB,
    confidence_score        NUMERIC(5,4),
    validation_errors       JSONB NOT NULL DEFAULT '[]'::JSONB,
    status                  TEXT NOT NULL DEFAULT 'DRAFT'
                             CHECK (status IN ('DRAFT','VALID','INVALID','SUPERSEDED')),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_parsing_confidence
        CHECK (
            confidence_score IS NULL
            OR confidence_score BETWEEN 0 AND 1
        )
);

CREATE TABLE IF NOT EXISTS konfirmasi_pengguna (
    konfirmasi_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pesan_id                UUID NOT NULL REFERENCES pesan_masuk(pesan_id) ON DELETE CASCADE,
    parsing_id              UUID REFERENCES parsing_pesan(parsing_id),
    pengguna_id             UUID NOT NULL REFERENCES pengguna_koptumbuh(pengguna_id),
    keputusan               TEXT NOT NULL
                             CHECK (keputusan IN ('YA','UBAH','BATAL')),
    corrected_payload       JSONB,
    confirmed_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS relasi_transaksi_pihak (
    relasi_id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaksi_sample_id     TEXT NOT NULL
                             REFERENCES transaksi_penjualan(transaksi_sample_id) ON DELETE CASCADE,
    anggota_ref             TEXT REFERENCES anggota_koperasi(anggota_ref),
    pelanggan_id            UUID REFERENCES pelanggan_koptumbuh(pelanggan_id),
    pemasok_id              UUID REFERENCES pemasok_koptumbuh(pemasok_id),
    relationship_type       TEXT NOT NULL
                             CHECK (
                                 relationship_type IN (
                                     'MEMBER_CUSTOMER','NON_MEMBER_CUSTOMER',
                                     'SUPPLIER','OTHER'
                                 )
                             ),
    match_method            TEXT,
    match_confidence        NUMERIC(5,4),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_relasi_has_party
        CHECK (
            anggota_ref IS NOT NULL
            OR pelanggan_id IS NOT NULL
            OR pemasok_id IS NOT NULL
        ),
    CONSTRAINT ck_relasi_confidence
        CHECK (
            match_confidence IS NULL
            OR match_confidence BETWEEN 0 AND 1
        )
);

CREATE TABLE IF NOT EXISTS artikel_pengetahuan (
    artikel_id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    koperasi_ref            TEXT
                             REFERENCES referensi_koperasi_wilayah(koperasi_ref),
    judul                   TEXT NOT NULL,
    kategori                TEXT,
    isi                     TEXT NOT NULL,
    sumber                  TEXT,
    versi                   TEXT,
    tags                    TEXT[],
    status_aktif            BOOLEAN NOT NULL DEFAULT TRUE,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS rekomendasi (
    rekomendasi_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    koperasi_ref            TEXT NOT NULL
                             REFERENCES referensi_koperasi_wilayah(koperasi_ref),
    jenis                   TEXT NOT NULL
                             CHECK (
                                 jenis IN (
                                     'RESTOCK','BUNDLING','PROMOTION',
                                     'SLOW_MOVING','STOCKOUT_RISK',
                                     'MEMBER_ENGAGEMENT','SUPPLIER',
                                     'DATA_QUALITY','OTHER'
                                 )
                             ),
    judul                   TEXT NOT NULL,
    isi_rekomendasi         TEXT NOT NULL,
    alasan                  TEXT,
    produk_sample_id        TEXT REFERENCES produk_koperasi(produk_sample_id),
    anggota_ref             TEXT REFERENCES anggota_koperasi(anggota_ref),
    pemasok_id              UUID REFERENCES pemasok_koptumbuh(pemasok_id),
    transaksi_sample_id     TEXT REFERENCES transaksi_penjualan(transaksi_sample_id),
    priority                TEXT NOT NULL DEFAULT 'MEDIUM'
                             CHECK (priority IN ('LOW','MEDIUM','HIGH','CRITICAL')),
    status                  TEXT NOT NULL DEFAULT 'NEW'
                             CHECK (
                                 status IN (
                                     'NEW','READ','ACCEPTED','REJECTED',
                                     'COMPLETED','EXPIRED'
                                 )
                             ),
    explanation_payload     JSONB NOT NULL DEFAULT '{}'::JSONB,
    generated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actioned_at             TIMESTAMPTZ,
    expires_at              TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS notifikasi_log (
    notifikasi_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    koperasi_ref            TEXT NOT NULL
                             REFERENCES referensi_koperasi_wilayah(koperasi_ref),
    pengguna_id             UUID REFERENCES pengguna_koptumbuh(pengguna_id),
    rekomendasi_id          UUID REFERENCES rekomendasi(rekomendasi_id),
    pesan_id                UUID REFERENCES pesan_masuk(pesan_id),
    channel                 TEXT NOT NULL
                             CHECK (channel IN ('WHATSAPP','WEB','EMAIL','SYSTEM')),
    message_type            TEXT NOT NULL
                             CHECK (
                                 message_type IN (
                                     'CONFIRMATION','ALERT','SUMMARY',
                                     'RECOMMENDATION','REPORT','OTHER'
                                 )
                             ),
    title                   TEXT,
    content                 TEXT NOT NULL,
    provider_message_id     TEXT,
    status                  TEXT NOT NULL DEFAULT 'QUEUED'
                             CHECK (
                                 status IN (
                                     'QUEUED','SENT','DELIVERED',
                                     'READ','FAILED'
                                 )
                             ),
    sent_at                 TIMESTAMPTZ,
    read_at                 TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS penyesuaian_stok (
    penyesuaian_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    koperasi_ref            TEXT NOT NULL
                             REFERENCES referensi_koperasi_wilayah(koperasi_ref),
    produk_sample_id        TEXT NOT NULL
                             REFERENCES produk_koperasi(produk_sample_id),
    pengguna_id             UUID REFERENCES pengguna_koptumbuh(pengguna_id),
    quantity_delta          NUMERIC(18,3) NOT NULL,
    reason                  TEXT NOT NULL,
    source_message_id       UUID REFERENCES pesan_masuk(pesan_id),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS mapping_integrasi (
    mapping_id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    koperasi_ref            TEXT NOT NULL
                             REFERENCES referensi_koperasi_wilayah(koperasi_ref),
    entity_type             TEXT NOT NULL,
    local_table             TEXT NOT NULL,
    local_id                TEXT NOT NULL,
    external_table          TEXT NOT NULL,
    external_reference      TEXT,
    mapping_status          TEXT NOT NULL DEFAULT 'PENDING'
                             CHECK (
                                 mapping_status IN (
                                     'PENDING','VALID','INVALID',
                                     'EXPORTED','SYNCED'
                                 )
                             ),
    validation_errors       JSONB NOT NULL DEFAULT '[]'::JSONB,
    last_exported_at        TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_mapping_local
        UNIQUE (koperasi_ref, local_table, local_id, external_table)
);

CREATE TABLE IF NOT EXISTS ekspor_log (
    ekspor_id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    koperasi_ref            TEXT NOT NULL
                             REFERENCES referensi_koperasi_wilayah(koperasi_ref),
    pengguna_id             UUID REFERENCES pengguna_koptumbuh(pengguna_id),
    export_type             TEXT NOT NULL,
    format                  TEXT NOT NULL
                             CHECK (format IN ('CSV','XLSX','JSON')),
    period_start            TIMESTAMPTZ,
    period_end              TIMESTAMPTZ,
    file_url                TEXT,
    record_count            INTEGER,
    status                  TEXT NOT NULL DEFAULT 'PROCESSING'
                             CHECK (status IN ('PROCESSING','SUCCESS','FAILED')),
    error_detail            JSONB,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- H. INDEXES
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_koperasi_wilayah_kode
    ON referensi_koperasi_wilayah(kode_wilayah);

CREATE INDEX IF NOT EXISTS idx_anggota_koperasi_ref
    ON anggota_koperasi(koperasi_ref);

CREATE INDEX IF NOT EXISTS idx_anggota_kode_wilayah
    ON anggota_koperasi(kode_wilayah);

CREATE INDEX IF NOT EXISTS idx_produk_koperasi_ref
    ON produk_koperasi(koperasi_ref);

CREATE INDEX IF NOT EXISTS idx_produk_barcode
    ON produk_koperasi(kode_barcode);

CREATE INDEX IF NOT EXISTS idx_transaksi_koperasi_tanggal
    ON transaksi_penjualan(koperasi_ref, tanggal_dibuat DESC);

CREATE INDEX IF NOT EXISTS idx_barang_keluar_transaksi
    ON barang_keluar_produk(transaksi_sample_id);

CREATE INDEX IF NOT EXISTS idx_barang_keluar_produk_tanggal
    ON barang_keluar_produk(produk_sample_id, tanggal_keluar DESC);

CREATE INDEX IF NOT EXISTS idx_barang_masuk_produk_tanggal
    ON barang_masuk_produk(produk_sample_id, tanggal_masuk DESC);

CREATE INDEX IF NOT EXISTS idx_inventaris_koperasi_produk
    ON inventaris_produk(koperasi_ref, produk_sample_id);

CREATE INDEX IF NOT EXISTS idx_pesan_pengguna_status
    ON pesan_masuk(pengguna_id, status, received_at DESC);

CREATE INDEX IF NOT EXISTS idx_parsing_pesan
    ON parsing_pesan(pesan_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_rekomendasi_koperasi_status
    ON rekomendasi(koperasi_ref, status, priority, generated_at DESC);

CREATE INDEX IF NOT EXISTS idx_notifikasi_pengguna_status
    ON notifikasi_log(pengguna_id, status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_artikel_search
    ON artikel_pengetahuan
    USING GIN (to_tsvector('simple', coalesce(judul, '') || ' ' || coalesce(isi, '')));

CREATE INDEX IF NOT EXISTS idx_mapping_status
    ON mapping_integrasi(koperasi_ref, mapping_status, external_table);

-- ============================================================================
-- I. UPDATED-AT TRIGGERS
-- ============================================================================

DROP TRIGGER IF EXISTS trg_pengguna_updated_at ON pengguna_koptumbuh;
CREATE TRIGGER trg_pengguna_updated_at
BEFORE UPDATE ON pengguna_koptumbuh
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_pemasok_updated_at ON pemasok_koptumbuh;
CREATE TRIGGER trg_pemasok_updated_at
BEFORE UPDATE ON pemasok_koptumbuh
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_pelanggan_updated_at ON pelanggan_koptumbuh;
CREATE TRIGGER trg_pelanggan_updated_at
BEFORE UPDATE ON pelanggan_koptumbuh
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_artikel_updated_at ON artikel_pengetahuan;
CREATE TRIGGER trg_artikel_updated_at
BEFORE UPDATE ON artikel_pengetahuan
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_mapping_updated_at ON mapping_integrasi;
CREATE TRIGGER trg_mapping_updated_at
BEFORE UPDATE ON mapping_integrasi
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_produk_diperbarui ON produk_koperasi;
CREATE TRIGGER trg_produk_diperbarui
BEFORE UPDATE ON produk_koperasi
FOR EACH ROW EXECUTE FUNCTION set_diperbarui_pada();

DROP TRIGGER IF EXISTS trg_transaksi_diperbarui ON transaksi_penjualan;
CREATE TRIGGER trg_transaksi_diperbarui
BEFORE UPDATE ON transaksi_penjualan
FOR EACH ROW EXECUTE FUNCTION set_diperbarui_pada();

DROP TRIGGER IF EXISTS trg_inventaris_diperbarui ON inventaris_produk;
CREATE TRIGGER trg_inventaris_diperbarui
BEFORE UPDATE ON inventaris_produk
FOR EACH ROW EXECUTE FUNCTION set_diperbarui_pada();

-- ============================================================================
-- J. ANALYTICAL & RECONCILIATION VIEWS
-- ============================================================================

CREATE OR REPLACE VIEW v_stok_terhitung AS
WITH masuk AS (
    SELECT
        koperasi_ref,
        produk_sample_id,
        SUM(COALESCE(jumlah_masuk, 0)) AS total_masuk
    FROM barang_masuk_produk
    WHERE COALESCE(status, '') NOT IN ('Rejected', 'Cancelled')
    GROUP BY koperasi_ref, produk_sample_id
),
keluar AS (
    SELECT
        koperasi_ref,
        produk_sample_id,
        SUM(COALESCE(jumlah_keluar, 0)) AS total_keluar
    FROM barang_keluar_produk
    WHERE COALESCE(status_transaksi, '') NOT IN ('Refund', 'Cancelled')
    GROUP BY koperasi_ref, produk_sample_id
),
adjustment AS (
    SELECT
        koperasi_ref,
        produk_sample_id,
        SUM(quantity_delta) AS total_adjustment
    FROM penyesuaian_stok
    GROUP BY koperasi_ref, produk_sample_id
)
SELECT
    p.koperasi_ref,
    p.produk_sample_id,
    p.nama_produk,
    COALESCE(m.total_masuk, 0)
    - COALESCE(k.total_keluar, 0)
    + COALESCE(a.total_adjustment, 0) AS stok_terhitung
FROM produk_koperasi p
LEFT JOIN masuk m
    ON m.koperasi_ref = p.koperasi_ref
   AND m.produk_sample_id = p.produk_sample_id
LEFT JOIN keluar k
    ON k.koperasi_ref = p.koperasi_ref
   AND k.produk_sample_id = p.produk_sample_id
LEFT JOIN adjustment a
    ON a.koperasi_ref = p.koperasi_ref
   AND a.produk_sample_id = p.produk_sample_id;

CREATE OR REPLACE VIEW v_rekonsiliasi_stok AS
SELECT
    s.koperasi_ref,
    s.produk_sample_id,
    s.nama_produk,
    s.stok_terhitung,
    i.stok AS stok_snapshot,
    COALESCE(i.stok, 0) - COALESCE(s.stok_terhitung, 0) AS selisih,
    CASE
        WHEN i.inventaris_ref IS NULL THEN 'SNAPSHOT_MISSING'
        WHEN COALESCE(i.stok, 0) = COALESCE(s.stok_terhitung, 0) THEN 'MATCH'
        ELSE 'MISMATCH'
    END AS status_rekonsiliasi
FROM v_stok_terhitung s
LEFT JOIN inventaris_produk i
    ON i.koperasi_ref = s.koperasi_ref
   AND i.produk_sample_id = s.produk_sample_id;

CREATE OR REPLACE VIEW v_penjualan_harian AS
SELECT
    koperasi_ref,
    DATE_TRUNC('day', COALESCE(tanggal_dibuat, dibuat_pada)) AS hari,
    COUNT(*) AS jumlah_transaksi,
    SUM(COALESCE(total_pembayaran, 0)) AS omzet
FROM transaksi_penjualan
WHERE COALESCE(status_transaksi, '') NOT IN ('Refund', 'Cancelled')
GROUP BY
    koperasi_ref,
    DATE_TRUNC('day', COALESCE(tanggal_dibuat, dibuat_pada));

CREATE OR REPLACE VIEW v_produk_terlaris AS
SELECT
    b.koperasi_ref,
    b.produk_sample_id,
    COALESCE(MAX(p.nama_produk), MAX(b.nama_produk)) AS nama_produk,
    SUM(COALESCE(b.jumlah_keluar, 0)) AS jumlah_terjual,
    SUM(COALESCE(b.total_nilai, 0)) AS nilai_penjualan
FROM barang_keluar_produk b
LEFT JOIN produk_koperasi p
    ON p.produk_sample_id = b.produk_sample_id
WHERE COALESCE(b.status_transaksi, '') NOT IN ('Refund', 'Cancelled')
GROUP BY b.koperasi_ref, b.produk_sample_id;

CREATE OR REPLACE VIEW v_aktivitas_anggota AS
SELECT
    r.anggota_ref,
    a.koperasi_ref,
    a.nama,
    COUNT(DISTINCT r.transaksi_sample_id) AS jumlah_transaksi,
    MAX(t.tanggal_dibuat) AS transaksi_terakhir,
    SUM(COALESCE(t.total_pembayaran, 0)) AS total_belanja
FROM relasi_transaksi_pihak r
JOIN anggota_koperasi a
    ON a.anggota_ref = r.anggota_ref
JOIN transaksi_penjualan t
    ON t.transaksi_sample_id = r.transaksi_sample_id
WHERE r.anggota_ref IS NOT NULL
GROUP BY r.anggota_ref, a.koperasi_ref, a.nama;

-- ============================================================================
-- K. SCHEMA COMMENTS
-- ============================================================================

COMMENT ON SCHEMA koptumbuh IS
'KopTumbuh MVP schema: SIMKOPDES-compatible core plus conversational, operational, and intelligence extensions.';

COMMENT ON TABLE transaksi_penjualan IS
'Official-compatible sales transaction header. Product lines are stored in barang_keluar_produk.';

COMMENT ON TABLE pesan_masuk IS
'Raw WhatsApp text, voice, photo, or document input. This is never treated as an official transaction before human confirmation.';

COMMENT ON TABLE parsing_pesan IS
'AI/NLP/OCR draft extracted from pesan_masuk, including confidence and validation errors.';

COMMENT ON TABLE konfirmasi_pengguna IS
'Human decision YA/UBAH/BATAL. A confirmed operational record should only be created after YA or corrected approval.';

COMMENT ON TABLE mapping_integrasi IS
'Maps KopTumbuh local records to metadata_database_hackathon_final / future SIMKOPDES references.';

COMMENT ON VIEW v_rekonsiliasi_stok IS
'Compares movement-based stock with inventaris_produk snapshot and flags mismatches.';

COMMIT;

-- ============================================================================
-- Suggested execution:
--   psql -U <user> -d <database> -f koptumbuh_updated_minimal_data_model.sql
--
-- Suggested next migration:
--   - seed reference data
--   - add row-level security policies
--   - add API-specific idempotency keys
--   - add production secret management and encryption strategy
-- ============================================================================
