-- ============================================
-- KopTumbuh Additive Migrations — Team JasaAI
-- Run AFTER canonical schema + seed data
-- All tables prefixed JasaAI_ on shared DB
-- ============================================

-- ============================================
-- 1. EXTEND EXISTING TABLES
-- ============================================

-- WhatsApp idempotency: unique message id when present (allows multiple NULLs)
CREATE UNIQUE INDEX IF NOT EXISTS uq_pesan_masuk_whatsapp_message_id
  ON koptumbuh.pesan_masuk (whatsapp_message_id)
  WHERE whatsapp_message_id IS NOT NULL;

-- Role constraint: add ANGGOTA
ALTER TABLE koptumbuh.pengguna_koptumbuh DROP CONSTRAINT IF EXISTS pengguna_koptumbuh_role_check;
ALTER TABLE koptumbuh.pengguna_koptumbuh ADD CONSTRAINT pengguna_koptumbuh_role_check
  CHECK (role IN ('OPERATOR','KETUA','BENDAHARA','PEMBINA','ADMIN','ANGGOTA'));

-- Subsidy fields
ALTER TABLE koptumbuh.produk_koperasi ADD COLUMN IF NOT EXISTS is_subsidi BOOLEAN DEFAULT FALSE;
ALTER TABLE koptumbuh.produk_koperasi ADD COLUMN IF NOT EXISTS nama_subsidi TEXT;

-- Warehouse location
ALTER TABLE koptumbuh.inventaris_produk ADD COLUMN IF NOT EXISTS lokasi_simpan TEXT;
ALTER TABLE koptumbuh.inventaris_produk ADD COLUMN IF NOT EXISTS tanggal_masuk_gudang TIMESTAMPTZ;

-- Link incoming goods to supplier (needed by purchase-history + v_skor_pemasok)
ALTER TABLE koptumbuh.barang_masuk_produk
  ADD COLUMN IF NOT EXISTS pemasok_id UUID REFERENCES koptumbuh.pemasok_koptumbuh(pemasok_id);
CREATE INDEX IF NOT EXISTS idx_barang_masuk_pemasok
  ON koptumbuh.barang_masuk_produk(pemasok_id);

-- ============================================
-- 2. NEW TABLES
-- ============================================

-- Purchase Orders
CREATE TABLE IF NOT EXISTS koptumbuh.purchase_order (
    po_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    koperasi_ref    TEXT NOT NULL REFERENCES koptumbuh.referensi_koperasi_wilayah(koperasi_ref),
    pemasok_id      UUID NOT NULL REFERENCES koptumbuh.pemasok_koptumbuh(pemasok_id),
    status          TEXT NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT','DIKIRIM','DITERIMA_SEBAGIAN','DITERIMA','DIBATALKAN')),
    tanggal_order   DATE NOT NULL DEFAULT CURRENT_DATE,
    tanggal_estimasi DATE,
    catatan         TEXT,
    dibuat_pada     TIMESTAMPTZ DEFAULT NOW(),
    diperbarui_pada TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS koptumbuh.purchase_order_item (
    poi_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    po_id           UUID NOT NULL REFERENCES koptumbuh.purchase_order(po_id) ON DELETE CASCADE,
    produk_sample_id TEXT NOT NULL REFERENCES koptumbuh.produk_koperasi(produk_sample_id),
    jumlah_dipesan  NUMERIC(18,3) NOT NULL CHECK (jumlah_dipesan > 0),
    jumlah_diterima NUMERIC(18,3) DEFAULT 0 CHECK (jumlah_diterima >= 0),
    harga_per_unit  NUMERIC(18,2),
    dibuat_pada     TIMESTAMPTZ DEFAULT NOW()
);

-- Loans
CREATE TABLE IF NOT EXISTS koptumbuh.pinjaman_anggota (
    pinjaman_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    koperasi_ref        TEXT NOT NULL REFERENCES koptumbuh.referensi_koperasi_wilayah(koperasi_ref),
    anggota_ref         TEXT NOT NULL REFERENCES koptumbuh.anggota_koperasi(anggota_ref),
    jumlah_pinjaman     NUMERIC(18,2) NOT NULL CHECK (jumlah_pinjaman > 0),
    tenor_bulan         INTEGER NOT NULL CHECK (tenor_bulan > 0),
    bunga_persen        NUMERIC(5,2) DEFAULT 0,
    angsuran_per_bulan  NUMERIC(18,2),
    total_pengembalian  NUMERIC(18,2),
    status              TEXT NOT NULL DEFAULT 'AKTIF' CHECK (status IN ('AKTIF','LUNAS','MACET')),
    tanggal_mulai       DATE NOT NULL DEFAULT CURRENT_DATE,
    tanggal_jatuh_tempo DATE,
    dibuat_pada         TIMESTAMPTZ DEFAULT NOW(),
    diperbarui_pada     TIMESTAMPTZ DEFAULT NOW()
);

-- Banners
CREATE TABLE IF NOT EXISTS koptumbuh.banner (
    banner_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    koperasi_ref    TEXT NOT NULL REFERENCES koptumbuh.referensi_koperasi_wilayah(koperasi_ref),
    judul           TEXT NOT NULL,
    gambar_url      TEXT,
    link_url        TEXT,
    urutan          INTEGER DEFAULT 0,
    status_aktif    BOOLEAN DEFAULT TRUE,
    dibuat_pada     TIMESTAMPTZ DEFAULT NOW()
);

-- Member Complaints
CREATE TABLE IF NOT EXISTS koptumbuh.pengaduan (
    pengaduan_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    koperasi_ref    TEXT NOT NULL REFERENCES koptumbuh.referensi_koperasi_wilayah(koperasi_ref),
    anggota_ref     TEXT REFERENCES koptumbuh.anggota_koperasi(anggota_ref),
    pengadu_nama    TEXT NOT NULL,
    pengadu_kontak  TEXT,
    kategori        TEXT CHECK (kategori IN ('LAYANAN','PRODUK','KEUANGAN','TEKNIS','LAINNYA')),
    isi_pengaduan   TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'BARU' CHECK (status IN ('BARU','PROSES','SELESAI','DITOLAK')),
    respon          TEXT,
    dibuat_pada     TIMESTAMPTZ DEFAULT NOW(),
    diperbarui_pada TIMESTAMPTZ DEFAULT NOW()
);

-- Market Price Comparison
CREATE TABLE IF NOT EXISTS koptumbuh.harga_pasar (
    harga_pasar_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    produk_sample_id   TEXT REFERENCES koptumbuh.produk_koperasi(produk_sample_id),
    nama_produk_mentah TEXT NOT NULL,
    harga              NUMERIC(18,2) NOT NULL,
    nama_toko          TEXT NOT NULL,
    jenis_toko         TEXT CHECK (jenis_toko IN ('PASAR','MINIMARKET','SUPERMARKET','E_COMMERCE','WARUNG','LAINNYA')),
    kab_kota           TEXT,
    sumber_data        TEXT,
    sumber_url         TEXT,
    tanggal_lapor      TIMESTAMPTZ DEFAULT NOW(),
    kadaluarsa_pada    TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '7 days')
);
CREATE INDEX IF NOT EXISTS idx_harga_pasar_produk ON koptumbuh.harga_pasar(produk_sample_id, tanggal_lapor DESC);

-- Delivery
CREATE TABLE IF NOT EXISTS koptumbuh.pengiriman (
    pengiriman_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaksi_sample_id TEXT NOT NULL REFERENCES koptumbuh.transaksi_penjualan(transaksi_sample_id),
    koperasi_ref        TEXT NOT NULL REFERENCES koptumbuh.referensi_koperasi_wilayah(koperasi_ref),
    tipe_pengiriman     TEXT NOT NULL CHECK (tipe_pengiriman IN ('PICKUP','DELIVERY')),
    alamat_tujuan       TEXT,
    kurir_id            TEXT REFERENCES koptumbuh.karyawan_koperasi(karyawan_ref),
    status              TEXT NOT NULL DEFAULT 'MENUNGGU' CHECK (status IN ('MENUNGGU','DIKIRIM','TIBA','GAGAL')),
    dibuat_pada         TIMESTAMPTZ DEFAULT NOW(),
    diperbarui_pada     TIMESTAMPTZ DEFAULT NOW()
);

-- Courier GPS Tracking
CREATE TABLE IF NOT EXISTS koptumbuh.pelacakan_kurir (
    pelacakan_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pengiriman_id   UUID NOT NULL REFERENCES koptumbuh.pengiriman(pengiriman_id),
    kurir_id        TEXT NOT NULL REFERENCES koptumbuh.karyawan_koperasi(karyawan_ref),
    latitude        NUMERIC(10,7) NOT NULL,
    longitude       NUMERIC(10,7) NOT NULL,
    akurasi_meter   NUMERIC(8,2),
    kecepatan_kmh   NUMERIC(5,1),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_pelacakan_pengiriman ON koptumbuh.pelacakan_kurir(pengiriman_id, created_at DESC);

-- ============================================
-- 3. ANALYTICAL VIEWS
-- ============================================

-- BI: Product Margins
CREATE OR REPLACE VIEW koptumbuh.v_margin_produk AS
SELECT p.koperasi_ref, p.produk_sample_id, p.nama_produk,
    latest_bm.harga_beli, latest_bm.harga_jual,
    (latest_bm.harga_jual - latest_bm.harga_beli) AS margin_nominal,
    CASE WHEN latest_bm.harga_beli > 0 THEN ROUND(((latest_bm.harga_jual - latest_bm.harga_beli) / latest_bm.harga_beli * 100)::numeric, 1) ELSE 0 END AS margin_persen,
    COALESCE(sales.total_terjual, 0) AS total_terjual,
    (latest_bm.harga_jual - latest_bm.harga_beli) * COALESCE(sales.total_terjual, 0) AS total_profit
FROM koptumbuh.produk_koperasi p
LEFT JOIN LATERAL (SELECT harga_beli, harga_jual FROM koptumbuh.barang_masuk_produk WHERE produk_sample_id = p.produk_sample_id AND koperasi_ref = p.koperasi_ref AND COALESCE(status,'') NOT IN ('Rejected','Cancelled') ORDER BY tanggal_masuk DESC LIMIT 1) latest_bm ON TRUE
LEFT JOIN (SELECT produk_sample_id, koperasi_ref, SUM(jumlah_keluar) AS total_terjual FROM koptumbuh.barang_keluar_produk WHERE COALESCE(status_transaksi,'') NOT IN ('Refund','Cancelled') GROUP BY produk_sample_id, koperasi_ref) sales ON sales.produk_sample_id = p.produk_sample_id AND sales.koperasi_ref = p.koperasi_ref;

-- BI: Slow-Moving Products
CREATE OR REPLACE VIEW koptumbuh.v_produk_lambat_bergerak AS
SELECT p.koperasi_ref, p.produk_sample_id, p.nama_produk, i.stok AS stok_saat_ini, latest_sale.terakhir_terjual,
    CASE WHEN latest_sale.terakhir_terjual IS NOT NULL THEN (CURRENT_DATE - latest_sale.terakhir_terjual::date) ELSE 999 END AS hari_tanpa_penjualan
FROM koptumbuh.produk_koperasi p
JOIN koptumbuh.inventaris_produk i ON i.produk_sample_id = p.produk_sample_id AND i.koperasi_ref = p.koperasi_ref
LEFT JOIN LATERAL (SELECT MAX(tanggal_keluar) AS terakhir_terjual FROM koptumbuh.barang_keluar_produk WHERE produk_sample_id = p.produk_sample_id AND koperasi_ref = p.koperasi_ref AND COALESCE(status_transaksi,'') NOT IN ('Refund','Cancelled')) latest_sale ON TRUE
WHERE i.stok > 0 AND (latest_sale.terakhir_terjual IS NULL OR latest_sale.terakhir_terjual < CURRENT_DATE - INTERVAL '14 days');

-- BI: Active Members
CREATE OR REPLACE VIEW koptumbuh.v_anggota_aktif AS
SELECT a.koperasi_ref, a.anggota_ref, a.nama, a.status_keanggotaan, a.tanggal_terdaftar,
    COUNT(DISTINCT r.transaksi_sample_id) AS jumlah_transaksi,
    COALESCE(SUM(t.total_pembayaran), 0) AS total_belanja,
    MAX(t.tanggal_dibuat) AS transaksi_terakhir,
    CASE WHEN MAX(t.tanggal_dibuat) IS NULL THEN 'TIDAK_AKTIF'
         WHEN MAX(t.tanggal_dibuat) < CURRENT_DATE - INTERVAL '30 days' THEN 'TIDAK_AKTIF_30_HARI'
         WHEN MAX(t.tanggal_dibuat) < CURRENT_DATE - INTERVAL '7 days' THEN 'KURANG_AKTIF' ELSE 'AKTIF' END AS status_aktivitas
FROM koptumbuh.anggota_koperasi a
LEFT JOIN koptumbuh.relasi_transaksi_pihak r ON r.anggota_ref = a.anggota_ref
LEFT JOIN koptumbuh.transaksi_penjualan t ON t.transaksi_sample_id = r.transaksi_sample_id AND COALESCE(t.status_transaksi,'') NOT IN ('Refund','Cancelled')
GROUP BY a.koperasi_ref, a.anggota_ref, a.nama, a.status_keanggotaan, a.tanggal_terdaftar;

-- RFM Segmentation
CREATE OR REPLACE VIEW koptumbuh.v_segmentasi_anggota AS
WITH rfm AS (
    SELECT a.koperasi_ref, a.anggota_ref, a.nama, a.status_keanggotaan,
        COUNT(DISTINCT r.transaksi_sample_id) AS frekuensi,
        COALESCE(SUM(t.total_pembayaran), 0) AS moneter,
        MAX(t.tanggal_dibuat) AS transaksi_terakhir,
        CASE WHEN MAX(t.tanggal_dibuat) IS NOT NULL THEN (CURRENT_DATE - MAX(t.tanggal_dibuat)::date) ELSE 999 END AS resensi_hari
    FROM koptumbuh.anggota_koperasi a
    LEFT JOIN koptumbuh.relasi_transaksi_pihak r ON r.anggota_ref = a.anggota_ref
    LEFT JOIN koptumbuh.transaksi_penjualan t ON t.transaksi_sample_id = r.transaksi_sample_id AND COALESCE(t.status_transaksi,'') NOT IN ('Refund','Cancelled')
    GROUP BY a.koperasi_ref, a.anggota_ref, a.nama, a.status_keanggotaan
)
SELECT *, CASE WHEN frekuensi >= 10 AND moneter >= 500000 THEN 'DIAMOND' WHEN frekuensi >= 5 AND moneter >= 250000 THEN 'EMAS' WHEN frekuensi >= 2 AND moneter >= 100000 THEN 'PERAK' WHEN frekuensi >= 1 THEN 'PERUNGGU' ELSE 'TIDAK_AKTIF' END AS segmentasi,
    CASE WHEN resensi_hari <= 7 AND frekuensi >= 5 THEN 'PELANGGAN_SETIA' WHEN resensi_hari <= 30 AND frekuensi >= 3 THEN 'PELANGGAN_REGULER' WHEN resensi_hari <= 60 THEN 'PELANGGAN_JARANG' WHEN resensi_hari <= 180 THEN 'RISIKO_HILANG' ELSE 'HILANG' END AS status_retensi
FROM rfm;

-- Supplier Scorecard
CREATE OR REPLACE VIEW koptumbuh.v_skor_pemasok AS
SELECT s.koperasi_ref, s.pemasok_id, s.nama_pemasok, s.lead_time_hari AS lead_time_dijanjikan,
    COALESCE(AVG(EXTRACT(DAY FROM (bm.tanggal_masuk - bm.dibuat_pada))), 0) AS lead_time_aktual_rata,
    COUNT(DISTINCT bm.produk_sample_id) AS produk_disuplai, COUNT(*) AS total_pengiriman,
    ROUND((COUNT(*) FILTER (WHERE EXTRACT(DAY FROM (bm.tanggal_masuk - bm.dibuat_pada)) <= s.lead_time_hari)::numeric / NULLIF(COUNT(*),0) * 100)::numeric, 1) AS persentase_tepat_waktu
FROM koptumbuh.pemasok_koptumbuh s
LEFT JOIN koptumbuh.barang_masuk_produk bm ON bm.pemasok_id = s.pemasok_id AND bm.koperasi_ref = s.koperasi_ref AND COALESCE(bm.status,'') NOT IN ('Rejected','Cancelled')
GROUP BY s.koperasi_ref, s.pemasok_id, s.nama_pemasok, s.lead_time_hari, s.status_aktif;

-- RAT SHU Summary
CREATE OR REPLACE VIEW koptumbuh.v_rat_shu_summary AS
SELECT r.koperasi_ref, p.nama_koperasi, r.tahun_buku, r.status_rat, r.tanggal_rat, r.jumlah_peserta_rat,
    (r.laporan_hasil_usaha::jsonb->>'shu_tahun_berjalan')::numeric AS shu_tahun_berjalan,
    (r.laporan_hasil_usaha::jsonb->>'total_pendapatan')::numeric AS total_pendapatan,
    (r.laporan_posisi_keuangan::jsonb->>'total_aset')::numeric AS total_aset,
    CASE WHEN (r.laporan_hasil_usaha::jsonb->>'shu_tahun_berjalan')::numeric > 0 THEN 'PROFIT' ELSE 'LOSS' END AS hasil
FROM koptumbuh.rat_koperasi r JOIN koptumbuh.profil_koperasi p ON p.koperasi_ref = r.koperasi_ref WHERE r.laporan_hasil_usaha IS NOT NULL;

-- Price Comparison
CREATE OR REPLACE VIEW koptumbuh.v_perbandingan_harga AS
WITH our AS (SELECT DISTINCT ON (produk_sample_id) produk_sample_id, harga_jual FROM koptumbuh.barang_masuk_produk WHERE COALESCE(status,'') NOT IN ('Rejected','Cancelled') ORDER BY produk_sample_id, tanggal_masuk DESC),
market AS (SELECT produk_sample_id, COUNT(*) AS jumlah, ROUND(AVG(harga),0) AS rata FROM koptumbuh.harga_pasar WHERE kadaluarsa_pada > NOW() GROUP BY produk_sample_id)
SELECT p.produk_sample_id, p.nama_produk, o.harga_jual AS harga_kita, m.rata AS harga_pasar_rata, m.jumlah AS jumlah_sumber,
    CASE WHEN m.rata IS NULL THEN 'NO_DATA' WHEN o.harga_jual <= m.rata THEN 'TERMURAH' ELSE 'LEBIH_MAHAL' END AS status_harga
FROM koptumbuh.produk_koperasi p JOIN our o ON o.produk_sample_id = p.produk_sample_id LEFT JOIN market m ON m.produk_sample_id = p.produk_sample_id;

-- Real-time SHU Estimation
CREATE OR REPLACE VIEW koptumbuh.v_shu_estimasi AS
SELECT t.koperasi_ref, DATE_TRUNC('month', COALESCE(t.tanggal_dibuat, t.dibuat_pada)) AS bulan,
    SUM(COALESCE(t.total_pembayaran,0)) AS total_omzet, COUNT(*) AS jumlah_transaksi,
    SUM(COALESCE(t.total_pembayaran,0)) * 0.85 AS estimasi_shu
FROM koptumbuh.transaksi_penjualan t WHERE COALESCE(t.status_transaksi,'') NOT IN ('Refund','Cancelled')
GROUP BY t.koperasi_ref, DATE_TRUNC('month', COALESCE(t.tanggal_dibuat, t.dibuat_pada)) ORDER BY bulan DESC;

-- Credit Receivables
CREATE OR REPLACE VIEW koptumbuh.v_piutang_anggota AS
SELECT r.anggota_ref, a.nama, t.koperasi_ref, COUNT(*) AS jumlah_hutang, SUM(t.total_pembayaran) AS total_piutang
FROM koptumbuh.transaksi_penjualan t JOIN koptumbuh.relasi_transaksi_pihak r ON r.transaksi_sample_id = t.transaksi_sample_id
JOIN koptumbuh.anggota_koperasi a ON a.anggota_ref = r.anggota_ref
WHERE t.status_transaksi = 'Unpaid' AND t.metode_pembayaran = 'Hutang' GROUP BY r.anggota_ref, a.nama, t.koperasi_ref;

-- Bundle Suggestions
CREATE OR REPLACE VIEW koptumbuh.v_bundle_suggestions AS
SELECT a.koperasi_ref, a.produk_sample_id AS a_id, b.produk_sample_id AS b_id, pa.nama_produk AS nama_a, pb.nama_produk AS nama_b,
    COUNT(*) AS dibeli_bersama, ma.harga_jual + mb.harga_jual AS harga_normal, ROUND((ma.harga_jual + mb.harga_jual) * 0.93) AS harga_bundle
FROM koptumbuh.barang_keluar_produk a JOIN koptumbuh.barang_keluar_produk b ON a.transaksi_sample_id = b.transaksi_sample_id AND a.produk_sample_id < b.produk_sample_id
JOIN koptumbuh.produk_koperasi pa ON pa.produk_sample_id = a.produk_sample_id JOIN koptumbuh.produk_koperasi pb ON pb.produk_sample_id = b.produk_sample_id
JOIN LATERAL (SELECT harga_jual FROM koptumbuh.barang_masuk_produk WHERE produk_sample_id = a.produk_sample_id ORDER BY tanggal_masuk DESC LIMIT 1) ma ON TRUE
JOIN LATERAL (SELECT harga_jual FROM koptumbuh.barang_masuk_produk WHERE produk_sample_id = b.produk_sample_id ORDER BY tanggal_masuk DESC LIMIT 1) mb ON TRUE
WHERE COALESCE(a.status_transaksi,'') NOT IN ('Refund','Cancelled') AND COALESCE(b.status_transaksi,'') NOT IN ('Refund','Cancelled')
GROUP BY a.koperasi_ref, a.produk_sample_id, b.produk_sample_id, pa.nama_produk, pb.nama_produk, ma.harga_jual, mb.harga_jual HAVING COUNT(*) >= 3;

-- Safety stock (ADS × 5, floor 5)
CREATE OR REPLACE VIEW koptumbuh.v_safety_stock AS
SELECT i.koperasi_ref, i.produk_sample_id, i.nama_produk, i.stok,
  COALESCE(ads.avg_daily, 0) AS ads,
  GREATEST(COALESCE(ads.avg_daily,0) * 5, 5) AS safety_stock,
  CASE WHEN i.stok < GREATEST(COALESCE(ads.avg_daily,0) * 5, 5) THEN 'BELOW_SAFETY' ELSE 'OK' END AS status
FROM koptumbuh.inventaris_produk i
LEFT JOIN (
  SELECT produk_sample_id, koperasi_ref, SUM(jumlah_keluar)/14.0 AS avg_daily
  FROM koptumbuh.barang_keluar_produk
  WHERE tanggal_keluar >= CURRENT_DATE - 14
  GROUP BY produk_sample_id, koperasi_ref
) ads ON ads.produk_sample_id=i.produk_sample_id AND ads.koperasi_ref=i.koperasi_ref;

-- Expiring stock estimate (180-day shelf life from inbound)
CREATE OR REPLACE VIEW koptumbuh.v_stok_expiring AS
SELECT bm.koperasi_ref, bm.produk_sample_id, p.nama_produk, bm.tanggal_masuk, bm.jumlah_masuk,
  bm.tanggal_masuk + INTERVAL '180 days' AS estimasi_kadaluarsa,
  CASE WHEN bm.tanggal_masuk + INTERVAL '180 days' < CURRENT_DATE + 30 THEN 'EXPIRING_SOON' ELSE 'OK' END AS status
FROM koptumbuh.barang_masuk_produk bm
JOIN koptumbuh.produk_koperasi p ON p.produk_sample_id=bm.produk_sample_id
WHERE COALESCE(bm.status,'') NOT IN ('Rejected','Cancelled');

-- RAT financial health alias
CREATE OR REPLACE VIEW koptumbuh.v_rat_financial_health AS
SELECT * FROM koptumbuh.v_rat_shu_summary;

-- Village commodity potential (actual table: referensi_komoditas_desa)
CREATE OR REPLACE VIEW koptumbuh.v_potensi_desa AS
SELECT kode_wilayah, nama_komoditas, volume AS potensi_produksi, luas_area AS satuan,
  nilai_potensi_desa, jumlah_sdm_terlibat
FROM koptumbuh.referensi_komoditas_desa;

-- Village demographics (actual table: referensi_profil_desa)
CREATE OR REPLACE VIEW koptumbuh.v_demografi_desa AS
SELECT * FROM koptumbuh.referensi_profil_desa;
