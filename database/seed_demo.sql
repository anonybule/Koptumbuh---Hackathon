-- ============================================
-- KopTumbuh Seed Data — Team JasaAI
-- Real SIMKOPDES reference data + demo cooperative
-- Desa Jonggol, Kec. Jonggol, Kab. Bogor, Jawa Barat
-- kode_wilayah: 32.01.06.2009
-- ============================================

SET search_path = koptumbuh, public;

-- ============================================
-- 0. ADDITIVE MIGRATIONS (post-canonical)
-- ============================================

-- Extend pengguna_koptumbuh role constraint for ANGGOTA
ALTER TABLE koptumbuh.pengguna_koptumbuh DROP CONSTRAINT IF EXISTS pengguna_koptumbuh_role_check;
ALTER TABLE koptumbuh.pengguna_koptumbuh ADD CONSTRAINT pengguna_koptumbuh_role_check
  CHECK (role IN ('OPERATOR','KETUA','BENDAHARA','PEMBINA','ADMIN','ANGGOTA'));

-- Allow ANGGOTA without pengurus/karyawan refs (self-service members)
ALTER TABLE koptumbuh.pengguna_koptumbuh DROP CONSTRAINT IF EXISTS ck_pengguna_reference;
ALTER TABLE koptumbuh.pengguna_koptumbuh ADD CONSTRAINT ck_pengguna_reference
  CHECK (
    pengurus_ref IS NOT NULL
    OR karyawan_ref IS NOT NULL
    OR role IN ('PEMBINA', 'ADMIN', 'ANGGOTA')
  );

-- Subsidy columns on produk_koperasi
ALTER TABLE koptumbuh.produk_koperasi ADD COLUMN IF NOT EXISTS is_subsidi BOOLEAN DEFAULT FALSE;
ALTER TABLE koptumbuh.produk_koperasi ADD COLUMN IF NOT EXISTS nama_subsidi TEXT;

-- Warehouse location on inventaris_produk
ALTER TABLE koptumbuh.inventaris_produk ADD COLUMN IF NOT EXISTS lokasi_simpan TEXT;
ALTER TABLE koptumbuh.inventaris_produk ADD COLUMN IF NOT EXISTS tanggal_masuk_gudang TIMESTAMPTZ;

-- ============================================
-- 1. REFERENCE DATA (pulled from official SIMKOPDES DB)
-- ============================================

INSERT INTO referensi_wilayah (kode_wilayah, provinsi, kab_kota, kecamatan, desa_kelurahan)
VALUES ('32.01.06.2009', 'JAWA BARAT', 'KAB. BOGOR', 'Jonggol', 'Jonggol');

-- Real document types from official SIMKOPDES
INSERT INTO referensi_dokumen_koperasi (jenis_dokumen_ref, nama_dokumen) VALUES
    ('JENIS-DOC-F49EF56C92', 'Akta Pendirian'),
    ('JENIS-DOC-E27F233795', 'Akta Pendirian - Perubahan'),
    ('JENIS-DOC-62A46E908D', 'Berita Negara (BN)'),
    ('JENIS-DOC-018B05092C', 'Nomor Induk Berusaha (NIB)'),
    ('JENIS-DOC-BD46961E09', 'Nomor Pokok Wajib Pajak (NPWP)'),
    ('JENIS-DOC-180AA1F25E', 'Surat Keputusan Kemenkumham (SK AHU)'),
    ('JENIS-DOC-8693952152', 'Surat Keputusan Kemenkumham (SK AHU) - Perubahan'),
    ('JENIS-DOC-8693952152aaa', '-');

-- Real outlet types from official SIMKOPDES
INSERT INTO referensi_gerai_koperasi (jenis_gerai_ref, nama_jenis_gerai) VALUES
    ('JENIS-GERAI-9B8BB8396D', 'Apotek Desa'),
    ('JENIS-GERAI-BE6B6A2B01', 'Gerai Cold Storage/Cold Chain'),
    ('JENIS-GERAI-8112C21704', 'Gerai Kantor Koperasi'),
    ('JENIS-GERAI-FDB1681AD5', 'Gerai Klinik Desa'),
    ('JENIS-GERAI-B5D536E874', 'Gerai Sembako (Embrio KopHub)'),
    ('JENIS-GERAI-40F1F69AF4', 'Gerai Unit Usaha Simpan Pinjam (Embrio Kop Bank)'),
    ('JENIS-GERAI-5BB9593DB7', 'Logistik (Distribusi)'),
    ('JENIS-GERAI-CCD4662078', 'Usaha Lainnya (KBLI 2020)');

-- ============================================
-- 2. COOPERATIVE HUB & PROFILE
-- ID format: KOP-JasaAI-{12-HEX}
-- Status: Approved, Primer (matching official SIMKOPDES)
-- ============================================

INSERT INTO referensi_koperasi_wilayah (koperasi_ref, kode_wilayah)
VALUES ('KOP-JasaAI-A1B2C3D4E5F6', '32.01.06.2009');

INSERT INTO profil_koperasi (
    koperasi_ref, nama_koperasi, status_registrasi, bentuk_koperasi,
    kategori_usaha, nik_koperasi, alamat_lengkap, kode_pos
) VALUES (
    'KOP-JasaAI-A1B2C3D4E5F6',
    'KOPERASI DESA MERAH PUTIH TUMBUH BERSAMA JONGGOL',
    'Approved', 'Primer',
    'SEMBAKO', '1234567890123456',
    'Jl. Raya Jonggol No. 42, Desa Jonggol, Kec. Jonggol, Kab. Bogor', '16830'
);

-- Board/Management (pengurus_koperasi)
INSERT INTO pengurus_koperasi (
    pengurus_ref, koperasi_ref, nama, jabatan, status, no_hp, nik, jenis_kelamin, email
) VALUES
    ('PENG-A1B2C3D4E5F6', 'KOP-JasaAI-A1B2C3D4E5F6', 'Agus Wijaya', 'KETUA', 'Aktif',
     '628123456001', '327301******0001', 'LAKI-LAKI', 'agus.wijaya@email.com'),
    ('PENG-B2C3D4E5F6A1', 'KOP-JasaAI-A1B2C3D4E5F6', 'Ratna Dewi', 'BENDAHARA', 'Aktif',
     '628123456002', '327301******0002', 'PEREMPUAN', 'ratna.dewi@email.com');

-- Employees
INSERT INTO karyawan_koperasi (
    karyawan_ref, koperasi_ref, nama, jabatan, nomor_hp_karyawan, jenis_kelamin, status_karyawan
) VALUES
    ('KAR-C3D4E5F6A1B2', 'KOP-JasaAI-A1B2C3D4E5F6', 'Budi Santoso', 'OPERATOR KASIR',
     '628123456003', 'LAKI-LAKI', 'TETAP'),
    ('KAR-D4E5F6A1B2C3', 'KOP-JasaAI-A1B2C3D4E5F6', 'Siti Rahmawati', 'ADMIN STOK',
     '628123456004', 'PEREMPUAN', 'TETAP');

-- Outlet (using official gerai type)
INSERT INTO gerai_koperasi (
    gerai_ref, koperasi_ref, jenis_gerai_ref, status_gerai,
    akses_internet, akses_listrik, jenis_bangunan
) VALUES (
    'GERAI-E5F6A1B2C3D4', 'KOP-JasaAI-A1B2C3D4E5F6', 'JENIS-GERAI-B5D536E874',
    'Aktif', 'Ada', 'Ada', 'PERMANEN'
);

-- KBLI
INSERT INTO kbli_koperasi (koperasi_ref, kode_kbli, nama_kbli, tipe_izin_usaha, tahun_kbli)
VALUES ('KOP-JasaAI-A1B2C3D4E5F6', '47111', 'Perdagangan Eceran Sembako', 'Mikro', 2024);

-- Legal Documents
INSERT INTO dokumen_koperasi (
    dokumen_ref, koperasi_ref, jenis_dokumen_ref, nomor, tanggal_berlaku
) VALUES
    ('DOK-F6A1B2C3D4E5', 'KOP-JasaAI-A1B2C3D4E5F6', 'JENIS-DOC-F49EF56C92',
     'AHU-0012345.AH.01.01.TAHUN.2023', '2023-06-15'),
    ('DOK-A1B2C3D4E5F6', 'KOP-JasaAI-A1B2C3D4E5F6', 'JENIS-DOC-BD46961E09',
     '12.345.678.9-012.000', '2023-06-15');

-- RAT (Annual Member Meeting)
INSERT INTO rat_koperasi (
    rat_sample_id, koperasi_ref, jenis_sektor_koperasi, urutan_rat,
    tahun_buku, tahun_rencana_kerja, tahun_rencana_anggaran, tanggal_rat,
    jumlah_peserta_rat, status_rat, tahap_rat
) VALUES (
    'RAT-000342', 'KOP-JasaAI-A1B2C3D4E5F6', 'Perdagangan', 'RAT KE-5',
    2024, 2025, 2025, '2025-01-20', 45, 'Verified', 'PASCA_RAT'
);

-- ============================================
-- 3. USERS (JasaAI_ prefixed on shared DB)
-- NOTE: The canonical schema CHECK constraint allows OPERATOR,KETUA,
-- BENDAHARA,PEMBINA,ADMIN. Add migration for ANGGOTA role.
-- ============================================

INSERT INTO pengguna_koptumbuh (koperasi_ref, pengurus_ref, karyawan_ref, nama, nomor_whatsapp, role, status_aktif)
VALUES
    ('KOP-JasaAI-A1B2C3D4E5F6', 'PENG-A1B2C3D4E5F6', NULL, 'Agus Wijaya', '628123456001', 'KETUA', TRUE),
    ('KOP-JasaAI-A1B2C3D4E5F6', NULL, 'KAR-C3D4E5F6A1B2', 'Budi Santoso', '628123456003', 'OPERATOR', TRUE),
    ('KOP-JasaAI-A1B2C3D4E5F6', 'PENG-B2C3D4E5F6A1', NULL, 'Ratna Dewi', '628123456002', 'BENDAHARA', TRUE),
    ('KOP-JasaAI-A1B2C3D4E5F6', NULL, NULL, 'Pak Haji Ahmad', '628120000001', 'ANGGOTA', TRUE);

-- ============================================
-- 4. PRODUCTS & INVENTORY
-- ID format: PROD-{12-HEX} (matching official SIMKOPDES)
-- ============================================

INSERT INTO produk_koperasi (produk_sample_id, koperasi_ref, kode_barcode, nama_produk, unit)
VALUES
    ('PROD-A1B2C3D4E5F6', 'KOP-JasaAI-A1B2C3D4E5F6', '8991001000001', 'Beras Premium 5kg', 'Kg'),
    ('PROD-B2C3D4E5F6A1', 'KOP-JasaAI-A1B2C3D4E5F6', '8991002000002', 'Minyak Goreng 2L', 'Liter'),
    ('PROD-C3D4E5F6A1B2', 'KOP-JasaAI-A1B2C3D4E5F6', '8991003000003', 'Gula Pasir 1kg', 'Kg'),
    ('PROD-D4E5F6A1B2C3', 'KOP-JasaAI-A1B2C3D4E5F6', '8991004000004', 'Telur Ayam 1kg', 'Kg'),
    ('PROD-E5F6A1B2C3D4', 'KOP-JasaAI-A1B2C3D4E5F6', '8991005000005', 'Mie Instan Dus', 'Dus'),
    ('PROD-F6A1B2C3D4E5', 'KOP-JasaAI-A1B2C3D4E5F6', '8990347787806', 'Minyakita 1L (Subsidi)', 'Liter');

-- Initial stock via barang_masuk
INSERT INTO barang_masuk_produk (
    barang_masuk_ref, produk_sample_id, koperasi_ref, nama_produk,
    jumlah_masuk, jumlah_tersedia, harga_beli, harga_jual, total_biaya, status, tanggal_masuk
) VALUES
    ('BM-A1B2C3D4E5F6', 'PROD-A1B2C3D4E5F6', 'KOP-JasaAI-A1B2C3D4E5F6', 'Beras Premium 5kg',
     100, 50, 55000, 65000, 5500000, 'Diterima', '2026-07-01 08:00:00+07'),
    ('BM-B2C3D4E5F6A1', 'PROD-B2C3D4E5F6A1', 'KOP-JasaAI-A1B2C3D4E5F6', 'Minyak Goreng 2L',
     60, 30, 24000, 28000, 1440000, 'Diterima', '2026-07-01 08:00:00+07'),
    ('BM-C3D4E5F6A1B2', 'PROD-C3D4E5F6A1B2', 'KOP-JasaAI-A1B2C3D4E5F6', 'Gula Pasir 1kg',
     80, 25, 12000, 14000, 960000, 'Diterima', '2026-07-01 08:00:00+07'),
    ('BM-D4E5F6A1B2C3', 'PROD-D4E5F6A1B2C3', 'KOP-JasaAI-A1B2C3D4E5F6', 'Telur Ayam 1kg',
     40, 15, 23000, 27000, 920000, 'Diterima', '2026-07-03 08:00:00+07'),
    ('BM-E5F6A1B2C3D4', 'PROD-E5F6A1B2C3D4', 'KOP-JasaAI-A1B2C3D4E5F6', 'Mie Instan Dus',
     50, 35, 45000, 52000, 2250000, 'Diterima', '2026-07-01 08:00:00+07'),
    ('BM-F6A1B2C3D4E5', 'PROD-F6A1B2C3D4E5', 'KOP-JasaAI-A1B2C3D4E5F6', 'Minyakita 1L (Subsidi)',
     100, 40, 12000, 14000, 1200000, 'Diterima', '2026-07-01 08:00:00+07');

-- Inventory snapshots
INSERT INTO inventaris_produk (inventaris_ref, produk_sample_id, koperasi_ref, nama_produk, stok)
VALUES
    ('INV-A1B2C3D4E5F6', 'PROD-A1B2C3D4E5F6', 'KOP-JasaAI-A1B2C3D4E5F6', 'Beras Premium 5kg', 50),
    ('INV-B2C3D4E5F6A1', 'PROD-B2C3D4E5F6A1', 'KOP-JasaAI-A1B2C3D4E5F6', 'Minyak Goreng 2L', 30),
    ('INV-C3D4E5F6A1B2', 'PROD-C3D4E5F6A1B2', 'KOP-JasaAI-A1B2C3D4E5F6', 'Gula Pasir 1kg', 25),
    ('INV-D4E5F6A1B2C3', 'PROD-D4E5F6A1B2C3', 'KOP-JasaAI-A1B2C3D4E5F6', 'Telur Ayam 1kg', 15),
    ('INV-E5F6A1B2C3D4', 'PROD-E5F6A1B2C3D4', 'KOP-JasaAI-A1B2C3D4E5F6', 'Mie Instan Dus', 35),
    ('INV-F6A1B2C3D4E5', 'PROD-F6A1B2C3D4E5', 'KOP-JasaAI-A1B2C3D4E5F6', 'Minyakita 1L (Subsidi)', 40);

-- ============================================
-- 5. MEMBERS, CUSTOMERS & SUPPLIERS
-- ID format: AGT-{12-HEX}
-- Status: Approved (matching official SIMKOPDES)
-- Gender: LAKI-LAKI / PEREMPUAN
-- ============================================

INSERT INTO anggota_koperasi (
    anggota_ref, koperasi_ref, nama, nik, kode_wilayah, jenis_kelamin,
    status_keanggotaan, tanggal_terdaftar, pekerjaan
) VALUES
    ('AGT-A1B2C3D4E5F6', 'KOP-JasaAI-A1B2C3D4E5F6', 'Haji Ahmad Suherman',
     '327301******0001', '32.01.06.2009', 'LAKI-LAKI', 'Approved', '2024-01-15', 'Petani'),
    ('AGT-B2C3D4E5F6A1', 'KOP-JasaAI-A1B2C3D4E5F6', 'Siti Nurhaliza',
     '327301******0002', '32.01.06.2009', 'PEREMPUAN', 'Approved', '2024-02-01', 'Pedagang'),
    ('AGT-C3D4E5F6A1B2', 'KOP-JasaAI-A1B2C3D4E5F6', 'Dimas Prayogo',
     '327301******0003', '32.01.06.2009', 'LAKI-LAKI', 'Approved', '2024-03-10', 'Buruh'),
    ('AGT-D4E5F6A1B2C3', 'KOP-JasaAI-A1B2C3D4E5F6', 'Dewi Lestari',
     '327301******0004', '32.01.06.2009', 'PEREMPUAN', 'Approved', '2024-03-15', 'Guru'),
    ('AGT-E5F6A1B2C3D4', 'KOP-JasaAI-A1B2C3D4E5F6', 'Joko Supriyanto',
     '327301******0005', '32.01.06.2009', 'LAKI-LAKI', 'Approved', '2024-04-01', 'Wiraswasta');

-- Member savings (status: PAID/UNPAID — matching official SIMKOPDES)
INSERT INTO simpanan_anggota (
    simpanan_ref, koperasi_ref, anggota_ref, periode_pembayaran, jumlah_simpanan, status
) VALUES
    ('SIMPAN-A1B2C3D4E5F6', 'KOP-JasaAI-A1B2C3D4E5F6', 'AGT-A1B2C3D4E5F6', 'Simpanan Wajib - Juli 2026', 50000, 'PAID'),
    ('SIMPAN-B2C3D4E5F6A1', 'KOP-JasaAI-A1B2C3D4E5F6', 'AGT-B2C3D4E5F6A1', 'Simpanan Wajib - Juli 2026', 50000, 'PAID'),
    ('SIMPAN-C3D4E5F6A1B2', 'KOP-JasaAI-A1B2C3D4E5F6', 'AGT-A1B2C3D4E5F6', 'Simpanan Wajib - Juni 2026', 50000, 'PAID'),
    ('SIMPAN-D4E5F6A1B2C3', 'KOP-JasaAI-A1B2C3D4E5F6', 'AGT-B2C3D4E5F6A1', 'Simpanan Wajib - Juni 2026', 50000, 'PAID');

-- Customers (4 members + 1 walk-in)
INSERT INTO pelanggan_koptumbuh (koperasi_ref, anggota_ref, nama_pelanggan, nomor_whatsapp)
VALUES
    ('KOP-JasaAI-A1B2C3D4E5F6', 'AGT-A1B2C3D4E5F6', 'Pak Haji Ahmad', '628120000001'),
    ('KOP-JasaAI-A1B2C3D4E5F6', 'AGT-B2C3D4E5F6A1', 'Bu Siti Nurhaliza', '628120000002'),
    ('KOP-JasaAI-A1B2C3D4E5F6', 'AGT-C3D4E5F6A1B2', 'Mas Dimas', '628120000003'),
    ('KOP-JasaAI-A1B2C3D4E5F6', 'AGT-D4E5F6A1B2C3', 'Mbak Dewi', '628120000004'),
    ('KOP-JasaAI-A1B2C3D4E5F6', NULL, 'Pelanggan Umum', NULL);

-- Supplier
INSERT INTO pemasok_koptumbuh (koperasi_ref, nama_pemasok, nomor_hp, alamat, lead_time_hari, payment_term)
VALUES ('KOP-JasaAI-A1B2C3D4E5F6', 'PT Pangan Sejahtera Nusantara', '628120000099',
        'Jl. Raya Bogor KM 45, Bogor', 3, 'NET 30');

-- ============================================
-- 6. HISTORICAL TRANSACTIONS (for dashboard)
-- ID format: TRX-{12-HEX}
-- Status: Paid, Cash/Transfer
-- ============================================

INSERT INTO transaksi_penjualan (
    transaksi_sample_id, koperasi_ref, nama_pelanggan, tanggal_dibuat,
    total_pembayaran, status_transaksi, metode_pembayaran
) VALUES
    ('TRX-A1B2C3D4E5F6', 'KOP-JasaAI-A1B2C3D4E5F6', 'Bu Siti Nurhaliza',
     '2026-07-03 10:15:00+07', 158000, 'Paid', 'Cash'),
    ('TRX-B2C3D4E5F6A1', 'KOP-JasaAI-A1B2C3D4E5F6', 'Pak Haji Ahmad',
     '2026-07-05 14:30:00+07', 270000, 'Paid', 'Cash'),
    ('TRX-C3D4E5F6A1B2', 'KOP-JasaAI-A1B2C3D4E5F6', 'Mas Dimas',
     '2026-07-07 09:00:00+07', 65000, 'Paid', 'Transfer'),
    ('TRX-D4E5F6A1B2C3', 'KOP-JasaAI-A1B2C3D4E5F6', 'Mbak Dewi',
     '2026-07-08 16:45:00+07', 196000, 'Paid', 'Cash'),
    ('TRX-E5F6A1B2C3D4', 'KOP-JasaAI-A1B2C3D4E5F6', 'Pelanggan Umum',
     '2026-07-09 11:20:00+07', 52000, 'Paid', 'Cash'),
    -- Extra history for RFM tiers (DIAMOND / EMAS / PERAK)
    ('TRX-F1A2B3C4D5E6', 'KOP-JasaAI-A1B2C3D4E5F6', 'Pak Haji Ahmad',
     '2026-06-12 09:00:00+07', 130000, 'Paid', 'Cash'),
    ('TRX-F2A2B3C4D5E6', 'KOP-JasaAI-A1B2C3D4E5F6', 'Pak Haji Ahmad',
     '2026-06-20 11:00:00+07', 93000, 'Paid', 'Cash'),
    ('TRX-F3A2B3C4D5E6', 'KOP-JasaAI-A1B2C3D4E5F6', 'Pak Haji Ahmad',
     '2026-06-28 15:00:00+07', 65000, 'Paid', 'Transfer'),
    ('TRX-F4A2B3C4D5E6', 'KOP-JasaAI-A1B2C3D4E5F6', 'Pak Haji Ahmad',
     '2026-07-02 08:30:00+07', 158000, 'Paid', 'Cash'),
    ('TRX-F5A2B3C4D5E6', 'KOP-JasaAI-A1B2C3D4E5F6', 'Pak Haji Ahmad',
     '2026-07-10 10:00:00+07', 92000, 'Paid', 'Cash'),
    ('TRX-G1A2B3C4D5E6', 'KOP-JasaAI-A1B2C3D4E5F6', 'Bu Siti Nurhaliza',
     '2026-06-15 13:00:00+07', 65000, 'Paid', 'Cash'),
    ('TRX-G2A2B3C4D5E6', 'KOP-JasaAI-A1B2C3D4E5F6', 'Bu Siti Nurhaliza',
     '2026-06-25 16:00:00+07', 140000, 'Paid', 'Cash'),
    ('TRX-G3A2B3C4D5E6', 'KOP-JasaAI-A1B2C3D4E5F6', 'Bu Siti Nurhaliza',
     '2026-07-01 09:30:00+07', 79000, 'Paid', 'Transfer'),
    ('TRX-G4A2B3C4D5E6', 'KOP-JasaAI-A1B2C3D4E5F6', 'Bu Siti Nurhaliza',
     '2026-07-09 17:00:00+07', 117000, 'Paid', 'Cash'),
    ('TRX-H1A2B3C4D5E6', 'KOP-JasaAI-A1B2C3D4E5F6', 'Mbak Dewi',
     '2026-06-18 10:00:00+07', 65000, 'Paid', 'Cash'),
    ('TRX-H2A2B3C4D5E6', 'KOP-JasaAI-A1B2C3D4E5F6', 'Mbak Dewi',
     '2026-07-04 12:00:00+07', 28000, 'Paid', 'Cash'),
    ('TRX-I1A2B3C4D5E6', 'KOP-JasaAI-A1B2C3D4E5F6', 'Mas Dimas',
     '2026-05-10 10:00:00+07', 65000, 'Paid', 'Cash');

-- Line items
INSERT INTO barang_keluar_produk (
    transaksi_sample_id, produk_sample_id, koperasi_ref, nama_produk,
    jumlah_keluar, harga, total_nilai, status_transaksi, tanggal_keluar
) VALUES
    ('TRX-A1B2C3D4E5F6', 'PROD-A1B2C3D4E5F6', 'KOP-JasaAI-A1B2C3D4E5F6', 'Beras Premium 5kg', 2, 65000, 130000, 'Paid', '2026-07-03 10:15:00+07'),
    ('TRX-A1B2C3D4E5F6', 'PROD-B2C3D4E5F6A1', 'KOP-JasaAI-A1B2C3D4E5F6', 'Minyak Goreng 2L', 1, 28000, 28000, 'Paid', '2026-07-03 10:15:00+07'),
    ('TRX-B2C3D4E5F6A1', 'PROD-A1B2C3D4E5F6', 'KOP-JasaAI-A1B2C3D4E5F6', 'Beras Premium 5kg', 3, 65000, 195000, 'Paid', '2026-07-05 14:30:00+07'),
    ('TRX-B2C3D4E5F6A1', 'PROD-D4E5F6A1B2C3', 'KOP-JasaAI-A1B2C3D4E5F6', 'Telur Ayam 1kg', 2, 27000, 54000, 'Paid', '2026-07-05 14:30:00+07'),
    ('TRX-B2C3D4E5F6A1', 'PROD-C3D4E5F6A1B2', 'KOP-JasaAI-A1B2C3D4E5F6', 'Gula Pasir 1kg', 1, 14000, 14000, 'Paid', '2026-07-05 14:30:00+07'),
    ('TRX-C3D4E5F6A1B2', 'PROD-A1B2C3D4E5F6', 'KOP-JasaAI-A1B2C3D4E5F6', 'Beras Premium 5kg', 1, 65000, 65000, 'Paid', '2026-07-07 09:00:00+07'),
    ('TRX-D4E5F6A1B2C3', 'PROD-B2C3D4E5F6A1', 'KOP-JasaAI-A1B2C3D4E5F6', 'Minyak Goreng 2L', 3, 28000, 84000, 'Paid', '2026-07-08 16:45:00+07'),
    ('TRX-D4E5F6A1B2C3', 'PROD-A1B2C3D4E5F6', 'KOP-JasaAI-A1B2C3D4E5F6', 'Beras Premium 5kg', 1, 65000, 65000, 'Paid', '2026-07-08 16:45:00+07'),
    ('TRX-D4E5F6A1B2C3', 'PROD-D4E5F6A1B2C3', 'KOP-JasaAI-A1B2C3D4E5F6', 'Telur Ayam 1kg', 1, 27000, 27000, 'Paid', '2026-07-08 16:45:00+07'),
    ('TRX-E5F6A1B2C3D4', 'PROD-E5F6A1B2C3D4', 'KOP-JasaAI-A1B2C3D4E5F6', 'Mie Instan Dus', 1, 52000, 52000, 'Paid', '2026-07-09 11:20:00+07'),
    ('TRX-F1A2B3C4D5E6', 'PROD-A1B2C3D4E5F6', 'KOP-JasaAI-A1B2C3D4E5F6', 'Beras Premium 5kg', 2, 65000, 130000, 'Paid', '2026-06-12 09:00:00+07'),
    ('TRX-F2A2B3C4D5E6', 'PROD-B2C3D4E5F6A1', 'KOP-JasaAI-A1B2C3D4E5F6', 'Minyak Goreng 2L', 2, 28000, 56000, 'Paid', '2026-06-20 11:00:00+07'),
    ('TRX-F2A2B3C4D5E6', 'PROD-C3D4E5F6A1B2', 'KOP-JasaAI-A1B2C3D4E5F6', 'Gula Pasir 1kg', 1, 14000, 14000, 'Paid', '2026-06-20 11:00:00+07'),
    ('TRX-F2A2B3C4D5E6', 'PROD-D4E5F6A1B2C3', 'KOP-JasaAI-A1B2C3D4E5F6', 'Telur Ayam 1kg', 1, 27000, 27000, 'Paid', '2026-06-20 11:00:00+07'),
    ('TRX-F3A2B3C4D5E6', 'PROD-A1B2C3D4E5F6', 'KOP-JasaAI-A1B2C3D4E5F6', 'Beras Premium 5kg', 1, 65000, 65000, 'Paid', '2026-06-28 15:00:00+07'),
    ('TRX-F4A2B3C4D5E6', 'PROD-A1B2C3D4E5F6', 'KOP-JasaAI-A1B2C3D4E5F6', 'Beras Premium 5kg', 2, 65000, 130000, 'Paid', '2026-07-02 08:30:00+07'),
    ('TRX-F4A2B3C4D5E6', 'PROD-B2C3D4E5F6A1', 'KOP-JasaAI-A1B2C3D4E5F6', 'Minyak Goreng 2L', 1, 28000, 28000, 'Paid', '2026-07-02 08:30:00+07'),
    ('TRX-F5A2B3C4D5E6', 'PROD-E5F6A1B2C3D4', 'KOP-JasaAI-A1B2C3D4E5F6', 'Mie Instan Dus', 1, 52000, 52000, 'Paid', '2026-07-10 10:00:00+07'),
    ('TRX-F5A2B3C4D5E6', 'PROD-C3D4E5F6A1B2', 'KOP-JasaAI-A1B2C3D4E5F6', 'Gula Pasir 1kg', 1, 14000, 14000, 'Paid', '2026-07-10 10:00:00+07'),
    ('TRX-F5A2B3C4D5E6', 'PROD-D4E5F6A1B2C3', 'KOP-JasaAI-A1B2C3D4E5F6', 'Telur Ayam 1kg', 1, 27000, 27000, 'Paid', '2026-07-10 10:00:00+07'),
    ('TRX-G1A2B3C4D5E6', 'PROD-A1B2C3D4E5F6', 'KOP-JasaAI-A1B2C3D4E5F6', 'Beras Premium 5kg', 1, 65000, 65000, 'Paid', '2026-06-15 13:00:00+07'),
    ('TRX-G2A2B3C4D5E6', 'PROD-A1B2C3D4E5F6', 'KOP-JasaAI-A1B2C3D4E5F6', 'Beras Premium 5kg', 1, 65000, 65000, 'Paid', '2026-06-25 16:00:00+07'),
    ('TRX-G2A2B3C4D5E6', 'PROD-B2C3D4E5F6A1', 'KOP-JasaAI-A1B2C3D4E5F6', 'Minyak Goreng 2L', 1, 28000, 28000, 'Paid', '2026-06-25 16:00:00+07'),
    ('TRX-G2A2B3C4D5E6', 'PROD-E5F6A1B2C3D4', 'KOP-JasaAI-A1B2C3D4E5F6', 'Mie Instan Dus', 1, 52000, 52000, 'Paid', '2026-06-25 16:00:00+07'),
    ('TRX-G3A2B3C4D5E6', 'PROD-B2C3D4E5F6A1', 'KOP-JasaAI-A1B2C3D4E5F6', 'Minyak Goreng 2L', 1, 28000, 28000, 'Paid', '2026-07-01 09:30:00+07'),
    ('TRX-G3A2B3C4D5E6', 'PROD-D4E5F6A1B2C3', 'KOP-JasaAI-A1B2C3D4E5F6', 'Telur Ayam 1kg', 1, 27000, 27000, 'Paid', '2026-07-01 09:30:00+07'),
    ('TRX-G3A2B3C4D5E6', 'PROD-C3D4E5F6A1B2', 'KOP-JasaAI-A1B2C3D4E5F6', 'Gula Pasir 1kg', 1, 14000, 14000, 'Paid', '2026-07-01 09:30:00+07'),
    ('TRX-G4A2B3C4D5E6', 'PROD-A1B2C3D4E5F6', 'KOP-JasaAI-A1B2C3D4E5F6', 'Beras Premium 5kg', 1, 65000, 65000, 'Paid', '2026-07-09 17:00:00+07'),
    ('TRX-G4A2B3C4D5E6', 'PROD-E5F6A1B2C3D4', 'KOP-JasaAI-A1B2C3D4E5F6', 'Mie Instan Dus', 1, 52000, 52000, 'Paid', '2026-07-09 17:00:00+07'),
    ('TRX-H1A2B3C4D5E6', 'PROD-A1B2C3D4E5F6', 'KOP-JasaAI-A1B2C3D4E5F6', 'Beras Premium 5kg', 1, 65000, 65000, 'Paid', '2026-06-18 10:00:00+07'),
    ('TRX-H2A2B3C4D5E6', 'PROD-B2C3D4E5F6A1', 'KOP-JasaAI-A1B2C3D4E5F6', 'Minyak Goreng 2L', 1, 28000, 28000, 'Paid', '2026-07-04 12:00:00+07'),
    ('TRX-I1A2B3C4D5E6', 'PROD-A1B2C3D4E5F6', 'KOP-JasaAI-A1B2C3D4E5F6', 'Beras Premium 5kg', 1, 65000, 65000, 'Paid', '2026-05-10 10:00:00+07');

-- Member-TX links
INSERT INTO relasi_transaksi_pihak (transaksi_sample_id, anggota_ref, relationship_type, match_method)
VALUES
    ('TRX-A1B2C3D4E5F6', 'AGT-B2C3D4E5F6A1', 'MEMBER_CUSTOMER', 'auto'),
    ('TRX-B2C3D4E5F6A1', 'AGT-A1B2C3D4E5F6', 'MEMBER_CUSTOMER', 'auto'),
    ('TRX-C3D4E5F6A1B2', 'AGT-C3D4E5F6A1B2', 'MEMBER_CUSTOMER', 'auto'),
    ('TRX-D4E5F6A1B2C3', 'AGT-D4E5F6A1B2C3', 'MEMBER_CUSTOMER', 'auto'),
    ('TRX-F1A2B3C4D5E6', 'AGT-A1B2C3D4E5F6', 'MEMBER_CUSTOMER', 'auto'),
    ('TRX-F2A2B3C4D5E6', 'AGT-A1B2C3D4E5F6', 'MEMBER_CUSTOMER', 'auto'),
    ('TRX-F3A2B3C4D5E6', 'AGT-A1B2C3D4E5F6', 'MEMBER_CUSTOMER', 'auto'),
    ('TRX-F4A2B3C4D5E6', 'AGT-A1B2C3D4E5F6', 'MEMBER_CUSTOMER', 'auto'),
    ('TRX-F5A2B3C4D5E6', 'AGT-A1B2C3D4E5F6', 'MEMBER_CUSTOMER', 'auto'),
    ('TRX-G1A2B3C4D5E6', 'AGT-B2C3D4E5F6A1', 'MEMBER_CUSTOMER', 'auto'),
    ('TRX-G2A2B3C4D5E6', 'AGT-B2C3D4E5F6A1', 'MEMBER_CUSTOMER', 'auto'),
    ('TRX-G3A2B3C4D5E6', 'AGT-B2C3D4E5F6A1', 'MEMBER_CUSTOMER', 'auto'),
    ('TRX-G4A2B3C4D5E6', 'AGT-B2C3D4E5F6A1', 'MEMBER_CUSTOMER', 'auto'),
    ('TRX-H1A2B3C4D5E6', 'AGT-D4E5F6A1B2C3', 'MEMBER_CUSTOMER', 'auto'),
    ('TRX-H2A2B3C4D5E6', 'AGT-D4E5F6A1B2C3', 'MEMBER_CUSTOMER', 'auto'),
    ('TRX-I1A2B3C4D5E6', 'AGT-C3D4E5F6A1B2', 'MEMBER_CUSTOMER', 'auto');

-- ============================================
-- 7. SUBSIDIES, KNOWLEDGE & STOCK UPDATE
-- ============================================

-- Mark subsidized products (Minyakita is government-subsidized)
UPDATE produk_koperasi SET is_subsidi = TRUE, nama_subsidi = 'Minyak Goreng Bersubsidi Pemerintah'
WHERE produk_sample_id = 'PROD-F6A1B2C3D4E5' AND koperasi_ref = 'KOP-JasaAI-A1B2C3D4E5F6';

INSERT INTO artikel_pengetahuan (koperasi_ref, judul, kategori, isi, sumber)
VALUES ('KOP-JasaAI-A1B2C3D4E5F6',
    'SOP Pencatatan Transaksi Harian via WhatsApp',
    'SOP',
    'Kirim pesan dengan format: [Nama Pelanggan] beli [Jumlah] [Nama Produk]. Contoh: Bu Siti beli 2 Beras Premium 5kg, bayar tunai.',
    'JasaAI Admin');

-- Seed recommendations (visible before Generate)
INSERT INTO rekomendasi (
    koperasi_ref, jenis, judul, isi_rekomendasi, alasan, produk_sample_id, priority, status
) VALUES
    ('KOP-JasaAI-A1B2C3D4E5F6', 'STOCKOUT_RISK',
     'Stok Telur Ayam hampir habis',
     'Stok Telur Ayam 1kg tersisa rendah. Segera restock dari pemasok sebelum weekend.',
     'ADS tinggi + stok di bawah safety stock',
     'PROD-D4E5F6A1B2C3', 'CRITICAL', 'NEW'),
    ('KOP-JasaAI-A1B2C3D4E5F6', 'RESTOCK',
     'Restock Beras Premium 5kg',
     'Beras Premium adalah top seller. Rencana restock 40 unit dalam 3 hari (lead time pemasok).',
     'Top product by volume + declining available stock',
     'PROD-A1B2C3D4E5F6', 'HIGH', 'NEW'),
    ('KOP-JasaAI-A1B2C3D4E5F6', 'SLOW_MOVING',
     'Minyakita 1L bergerak lambat',
     'Produk subsidi Minyakita jarang terjual 14 hari terakhir. Pertimbangkan bundling dengan beras.',
     'Zero/low outbound vs inbound age',
     'PROD-F6A1B2C3D4E5', 'MEDIUM', 'NEW');

-- Update inventory to reflect demo sales (original + RFM enrichment)
UPDATE inventaris_produk SET stok = GREATEST(stok - 16, 5) WHERE produk_sample_id = 'PROD-A1B2C3D4E5F6' AND koperasi_ref = 'KOP-JasaAI-A1B2C3D4E5F6';
UPDATE inventaris_produk SET stok = GREATEST(stok - 10, 4) WHERE produk_sample_id = 'PROD-B2C3D4E5F6A1' AND koperasi_ref = 'KOP-JasaAI-A1B2C3D4E5F6';
UPDATE inventaris_produk SET stok = GREATEST(stok - 5, 3) WHERE produk_sample_id = 'PROD-C3D4E5F6A1B2' AND koperasi_ref = 'KOP-JasaAI-A1B2C3D4E5F6';
UPDATE inventaris_produk SET stok = GREATEST(stok - 7, 2) WHERE produk_sample_id = 'PROD-D4E5F6A1B2C3' AND koperasi_ref = 'KOP-JasaAI-A1B2C3D4E5F6';
UPDATE inventaris_produk SET stok = GREATEST(stok - 4, 5) WHERE produk_sample_id = 'PROD-E5F6A1B2C3D4' AND koperasi_ref = 'KOP-JasaAI-A1B2C3D4E5F6';

-- ============================================
-- 9. NETWORK SUPPLY � sibling Kopdes in Kec. Jonggol
-- For multi-store SCM / consolidated logistics demo
-- ============================================

INSERT INTO referensi_wilayah (kode_wilayah, provinsi, kab_kota, kecamatan, desa_kelurahan) VALUES
    ('32.01.06.2001', 'JAWA BARAT', 'KAB. BOGOR', 'Jonggol', 'Sukamaju'),
    ('32.01.06.2005', 'JAWA BARAT', 'KAB. BOGOR', 'Jonggol', 'Weninggalih'),
    ('32.01.06.2012', 'JAWA BARAT', 'KAB. BOGOR', 'Jonggol', 'Singasari')
ON CONFLICT (kode_wilayah) DO NOTHING;

INSERT INTO referensi_koperasi_wilayah (koperasi_ref, kode_wilayah) VALUES
    ('KOP-JasaAI-B2C3D4E5F6A1', '32.01.06.2001'),
    ('KOP-JasaAI-C3D4E5F6A1B2', '32.01.06.2005'),
    ('KOP-JasaAI-D4E5F6A1B2C3', '32.01.06.2012')
ON CONFLICT (koperasi_ref) DO NOTHING;

INSERT INTO profil_koperasi (
    koperasi_ref, nama_koperasi, status_registrasi, bentuk_koperasi,
    kategori_usaha, nik_koperasi, alamat_lengkap, kode_pos
) VALUES
    ('KOP-JasaAI-B2C3D4E5F6A1', 'KOPERASI DESA MERAH PUTIH SUKAMAJU JONGGOL',
     'Approved', 'Primer', 'SEMBAKO', '1234567890123457',
     'Jl. Sukamaju Raya No. 8, Desa Sukamaju, Kec. Jonggol', '16830'),
    ('KOP-JasaAI-C3D4E5F6A1B2', 'KOPERASI DESA MERAH PUTIH WENINGGALIH',
     'Approved', 'Primer', 'SEMBAKO', '1234567890123458',
     'Kp. Weninggalih, Desa Weninggalih, Kec. Jonggol', '16830'),
    ('KOP-JasaAI-D4E5F6A1B2C3', 'KOPERASI DESA MERAH PUTIH SINGASARI',
     'Approved', 'Primer', 'SEMBAKO', '1234567890123459',
     'Jl. Singasari No. 15, Desa Singasari, Kec. Jonggol', '16830')
ON CONFLICT (koperasi_ref) DO NOTHING;

-- Shared SKU names across network (unique product IDs per store)
INSERT INTO produk_koperasi (produk_sample_id, koperasi_ref, kode_barcode, nama_produk, unit) VALUES
    ('PROD-NS-B-BERAS', 'KOP-JasaAI-B2C3D4E5F6A1', '8992001000001', 'Beras Premium 5kg', 'Kg'),
    ('PROD-NS-B-MINYAK', 'KOP-JasaAI-B2C3D4E5F6A1', '8992002000002', 'Minyak Goreng 2L', 'Liter'),
    ('PROD-NS-B-GULA', 'KOP-JasaAI-B2C3D4E5F6A1', '8992003000003', 'Gula Pasir 1kg', 'Kg'),
    ('PROD-NS-B-TELUR', 'KOP-JasaAI-B2C3D4E5F6A1', '8992004000004', 'Telur Ayam 1kg', 'Kg'),
    ('PROD-NS-C-BERAS', 'KOP-JasaAI-C3D4E5F6A1B2', '8993001000001', 'Beras Premium 5kg', 'Kg'),
    ('PROD-NS-C-MINYAK', 'KOP-JasaAI-C3D4E5F6A1B2', '8993002000002', 'Minyak Goreng 2L', 'Liter'),
    ('PROD-NS-C-GULA', 'KOP-JasaAI-C3D4E5F6A1B2', '8993003000003', 'Gula Pasir 1kg', 'Kg'),
    ('PROD-NS-C-MIE', 'KOP-JasaAI-C3D4E5F6A1B2', '8993005000005', 'Mie Instan Dus', 'Dus'),
    ('PROD-NS-D-BERAS', 'KOP-JasaAI-D4E5F6A1B2C3', '8994001000001', 'Beras Premium 5kg', 'Kg'),
    ('PROD-NS-D-MINYAK', 'KOP-JasaAI-D4E5F6A1B2C3', '8994002000002', 'Minyak Goreng 2L', 'Liter'),
    ('PROD-NS-D-TELUR', 'KOP-JasaAI-D4E5F6A1B2C3', '8994004000004', 'Telur Ayam 1kg', 'Kg'),
    ('PROD-NS-D-GULA', 'KOP-JasaAI-D4E5F6A1B2C3', '8994003000003', 'Gula Pasir 1kg', 'Kg')
ON CONFLICT (produk_sample_id) DO NOTHING;

-- Critical / low stock at satellite stores (forces restock needs)
INSERT INTO inventaris_produk (inventaris_ref, produk_sample_id, koperasi_ref, nama_produk, stok) VALUES
    ('INV-NS-B-BERAS', 'PROD-NS-B-BERAS', 'KOP-JasaAI-B2C3D4E5F6A1', 'Beras Premium 5kg', 3),
    ('INV-NS-B-MINYAK', 'PROD-NS-B-MINYAK', 'KOP-JasaAI-B2C3D4E5F6A1', 'Minyak Goreng 2L', 2),
    ('INV-NS-B-GULA', 'PROD-NS-B-GULA', 'KOP-JasaAI-B2C3D4E5F6A1', 'Gula Pasir 1kg', 8),
    ('INV-NS-B-TELUR', 'PROD-NS-B-TELUR', 'KOP-JasaAI-B2C3D4E5F6A1', 'Telur Ayam 1kg', 1),
    ('INV-NS-C-BERAS', 'PROD-NS-C-BERAS', 'KOP-JasaAI-C3D4E5F6A1B2', 'Beras Premium 5kg', 4),
    ('INV-NS-C-MINYAK', 'PROD-NS-C-MINYAK', 'KOP-JasaAI-C3D4E5F6A1B2', 'Minyak Goreng 2L', 12),
    ('INV-NS-C-GULA', 'PROD-NS-C-GULA', 'KOP-JasaAI-C3D4E5F6A1B2', 'Gula Pasir 1kg', 2),
    ('INV-NS-C-MIE', 'PROD-NS-C-MIE', 'KOP-JasaAI-C3D4E5F6A1B2', 'Mie Instan Dus', 6),
    ('INV-NS-D-BERAS', 'PROD-NS-D-BERAS', 'KOP-JasaAI-D4E5F6A1B2C3', 'Beras Premium 5kg', 2),
    ('INV-NS-D-MINYAK', 'PROD-NS-D-MINYAK', 'KOP-JasaAI-D4E5F6A1B2C3', 'Minyak Goreng 2L', 3),
    ('INV-NS-D-TELUR', 'PROD-NS-D-TELUR', 'KOP-JasaAI-D4E5F6A1B2C3', 'Telur Ayam 1kg', 4),
    ('INV-NS-D-GULA', 'PROD-NS-D-GULA', 'KOP-JasaAI-D4E5F6A1B2C3', 'Gula Pasir 1kg', 1)
ON CONFLICT (inventaris_ref) DO NOTHING;

INSERT INTO pemasok_koptumbuh (koperasi_ref, nama_pemasok, nomor_hp, alamat, lead_time_hari, payment_term)
SELECT v.koperasi_ref, 'PT Pangan Sejahtera Nusantara (Regional Jonggol)', '628120000099',
       'Gudang Jonggol, Kab. Bogor', 3, 'NET 14'
FROM (VALUES
    ('KOP-JasaAI-B2C3D4E5F6A1'),
    ('KOP-JasaAI-C3D4E5F6A1B2'),
    ('KOP-JasaAI-D4E5F6A1B2C3')
) AS v(koperasi_ref)
WHERE NOT EXISTS (
    SELECT 1 FROM pemasok_koptumbuh p WHERE p.koperasi_ref = v.koperasi_ref
);

-- Recent outbound so ADS > 0 (triggers days_remaining restock logic)
INSERT INTO transaksi_penjualan (
    transaksi_sample_id, koperasi_ref, nama_pelanggan, total_pembayaran, status_transaksi, tanggal_dibuat
) VALUES
    ('TRX-NS-B1', 'KOP-JasaAI-B2C3D4E5F6A1', 'Pelanggan Sukamaju', 260000, 'Paid', NOW() - INTERVAL '2 days'),
    ('TRX-NS-B2', 'KOP-JasaAI-B2C3D4E5F6A1', 'Pelanggan Sukamaju', 84000, 'Paid', NOW() - INTERVAL '1 days'),
    ('TRX-NS-B3', 'KOP-JasaAI-B2C3D4E5F6A1', 'Pelanggan Sukamaju', 135000, 'Paid', NOW() - INTERVAL '3 days'),
    ('TRX-NS-C1', 'KOP-JasaAI-C3D4E5F6A1B2', 'Pelanggan Weninggalih', 195000, 'Paid', NOW() - INTERVAL '2 days'),
    ('TRX-NS-C2', 'KOP-JasaAI-C3D4E5F6A1B2', 'Pelanggan Weninggalih', 56000, 'Paid', NOW() - INTERVAL '1 days'),
    ('TRX-NS-D1', 'KOP-JasaAI-D4E5F6A1B2C3', 'Pelanggan Singasari', 325000, 'Paid', NOW() - INTERVAL '1 days'),
    ('TRX-NS-D2', 'KOP-JasaAI-D4E5F6A1B2C3', 'Pelanggan Singasari', 56000, 'Paid', NOW() - INTERVAL '4 days'),
    ('TRX-NS-D3', 'KOP-JasaAI-D4E5F6A1B2C3', 'Pelanggan Singasari', 42000, 'Paid', NOW() - INTERVAL '2 days')
ON CONFLICT (transaksi_sample_id) DO NOTHING;

INSERT INTO barang_keluar_produk (
    transaksi_sample_id, produk_sample_id, koperasi_ref, nama_produk,
    jumlah_keluar, harga, total_nilai, status_transaksi, tanggal_keluar
)
SELECT * FROM (VALUES
    ('TRX-NS-B1', 'PROD-NS-B-BERAS', 'KOP-JasaAI-B2C3D4E5F6A1', 'Beras Premium 5kg', 4::numeric, 65000::numeric, 260000::numeric, 'Paid', NOW() - INTERVAL '2 days'),
    ('TRX-NS-B2', 'PROD-NS-B-MINYAK', 'KOP-JasaAI-B2C3D4E5F6A1', 'Minyak Goreng 2L', 3::numeric, 28000::numeric, 84000::numeric, 'Paid', NOW() - INTERVAL '1 days'),
    ('TRX-NS-B3', 'PROD-NS-B-TELUR', 'KOP-JasaAI-B2C3D4E5F6A1', 'Telur Ayam 1kg', 5::numeric, 27000::numeric, 135000::numeric, 'Paid', NOW() - INTERVAL '3 days'),
    ('TRX-NS-C1', 'PROD-NS-C-BERAS', 'KOP-JasaAI-C3D4E5F6A1B2', 'Beras Premium 5kg', 3::numeric, 65000::numeric, 195000::numeric, 'Paid', NOW() - INTERVAL '2 days'),
    ('TRX-NS-C2', 'PROD-NS-C-GULA', 'KOP-JasaAI-C3D4E5F6A1B2', 'Gula Pasir 1kg', 4::numeric, 14000::numeric, 56000::numeric, 'Paid', NOW() - INTERVAL '1 days'),
    ('TRX-NS-D1', 'PROD-NS-D-BERAS', 'KOP-JasaAI-D4E5F6A1B2C3', 'Beras Premium 5kg', 5::numeric, 65000::numeric, 325000::numeric, 'Paid', NOW() - INTERVAL '1 days'),
    ('TRX-NS-D2', 'PROD-NS-D-MINYAK', 'KOP-JasaAI-D4E5F6A1B2C3', 'Minyak Goreng 2L', 2::numeric, 28000::numeric, 56000::numeric, 'Paid', NOW() - INTERVAL '4 days'),
    ('TRX-NS-D3', 'PROD-NS-D-GULA', 'KOP-JasaAI-D4E5F6A1B2C3', 'Gula Pasir 1kg', 3::numeric, 14000::numeric, 42000::numeric, 'Paid', NOW() - INTERVAL '2 days')
) AS v(transaksi_sample_id, produk_sample_id, koperasi_ref, nama_produk, jumlah_keluar, harga, total_nilai, status_transaksi, tanggal_keluar)
WHERE NOT EXISTS (
    SELECT 1 FROM barang_keluar_produk b
    WHERE b.transaksi_sample_id = v.transaksi_sample_id AND b.produk_sample_id = v.produk_sample_id
);

INSERT INTO barang_masuk_produk (
    barang_masuk_ref, produk_sample_id, koperasi_ref, nama_produk,
    jumlah_masuk, jumlah_tersedia, harga_beli, harga_jual, total_biaya, status, tanggal_masuk
) VALUES
    ('BM-NS-B-BERAS', 'PROD-NS-B-BERAS', 'KOP-JasaAI-B2C3D4E5F6A1', 'Beras Premium 5kg', 20, 3, 55000, 65000, 1100000, 'Diterima', NOW() - INTERVAL '20 days'),
    ('BM-NS-B-MINYAK', 'PROD-NS-B-MINYAK', 'KOP-JasaAI-B2C3D4E5F6A1', 'Minyak Goreng 2L', 15, 2, 24000, 28000, 360000, 'Diterima', NOW() - INTERVAL '18 days'),
    ('BM-NS-C-BERAS', 'PROD-NS-C-BERAS', 'KOP-JasaAI-C3D4E5F6A1B2', 'Beras Premium 5kg', 20, 4, 55000, 65000, 1100000, 'Diterima', NOW() - INTERVAL '15 days'),
    ('BM-NS-D-BERAS', 'PROD-NS-D-BERAS', 'KOP-JasaAI-D4E5F6A1B2C3', 'Beras Premium 5kg', 25, 2, 55000, 65000, 1375000, 'Diterima', NOW() - INTERVAL '12 days')
ON CONFLICT (barang_masuk_ref) DO NOTHING;
