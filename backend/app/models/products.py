from sqlalchemy import Column, String, Integer, Numeric, TIMESTAMP, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.database import Base


class ProdukKoperasi(Base):
    __tablename__ = "produk_koperasi"
    __table_args__ = {"schema": "koptumbuh"}
    produk_sample_id = Column(String, primary_key=True)
    koperasi_ref = Column(String, ForeignKey("koptumbuh.referensi_koperasi_wilayah.koperasi_ref"))
    kode_barcode = Column(String)
    nama_produk = Column(String)
    unit = Column(String)
    is_subsidi = Column(Boolean, default=False)
    nama_subsidi = Column(String)
    dibuat_pada = Column(TIMESTAMP(timezone=True))
    diperbarui_pada = Column(TIMESTAMP(timezone=True))

    hub = relationship("ReferensiKoperasiWilayah", back_populates="produk")
    inventaris = relationship("InventarisProduk", back_populates="produk", uselist=False)
    barang_masuk = relationship("BarangMasukProduk", back_populates="produk")
    barang_keluar = relationship("BarangKeluarProduk", back_populates="produk")


class InventarisProduk(Base):
    __tablename__ = "inventaris_produk"
    __table_args__ = {"schema": "koptumbuh"}
    inventaris_ref = Column(String, primary_key=True)
    produk_sample_id = Column(String, ForeignKey("koptumbuh.produk_koperasi.produk_sample_id"))
    koperasi_ref = Column(String, ForeignKey("koptumbuh.referensi_koperasi_wilayah.koperasi_ref"))
    nama_produk = Column(String)
    stok = Column(Numeric(18, 3))
    kode_barcode = Column(String)
    lokasi_simpan = Column(String)
    tanggal_masuk_gudang = Column(TIMESTAMP(timezone=True))
    dibuat_pada = Column(TIMESTAMP(timezone=True))
    diperbarui_pada = Column(TIMESTAMP(timezone=True))

    produk = relationship("ProdukKoperasi", back_populates="inventaris")


class BarangMasukProduk(Base):
    __tablename__ = "barang_masuk_produk"
    __table_args__ = {"schema": "koptumbuh"}
    barang_masuk_ref = Column(String, primary_key=True)
    produk_sample_id = Column(String, ForeignKey("koptumbuh.produk_koperasi.produk_sample_id"))
    koperasi_ref = Column(String, ForeignKey("koptumbuh.referensi_koperasi_wilayah.koperasi_ref"))
    kode_barcode = Column(String)
    nama_produk = Column(String)
    nama_tampilan = Column(String)
    jumlah_masuk = Column(Numeric(18, 3))
    jumlah_tersedia = Column(Numeric(18, 3))
    harga_beli = Column(Numeric(18, 2))
    harga_jual = Column(Numeric(18, 2))
    total_biaya = Column(Numeric(18, 2))
    keterangan = Column(String)
    status = Column(String)
    tanggal_masuk = Column(TIMESTAMP(timezone=True))
    dibuat_pada = Column(TIMESTAMP(timezone=True))
    diperbarui_pada = Column(TIMESTAMP(timezone=True))

    produk = relationship("ProdukKoperasi", back_populates="barang_masuk")


class BarangKeluarProduk(Base):
    __tablename__ = "barang_keluar_produk"
    __table_args__ = {"schema": "koptumbuh"}
    __row_id = Column(Integer, primary_key=True, autoincrement=True)
    transaksi_sample_id = Column(String, ForeignKey("koptumbuh.transaksi_penjualan.transaksi_sample_id"))
    produk_sample_id = Column(String, ForeignKey("koptumbuh.produk_koperasi.produk_sample_id"))
    koperasi_ref = Column(String, ForeignKey("koptumbuh.referensi_koperasi_wilayah.koperasi_ref"))
    kode_barcode = Column(String)
    tanggal_keluar = Column(TIMESTAMP(timezone=True))
    status = Column(String)
    nama_produk = Column(String)
    nama_tampilan = Column(String)
    jumlah_keluar = Column(Numeric(18, 3))
    harga = Column(Numeric(18, 2))
    total_nilai = Column(Numeric(18, 2))
    status_transaksi = Column(String)
    dibuat_pada = Column(TIMESTAMP(timezone=True))
    diperbarui_pada = Column(TIMESTAMP(timezone=True))

    produk = relationship("ProdukKoperasi", back_populates="barang_keluar")
