from sqlalchemy import Column, String, Numeric, TIMESTAMP, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class TransaksiPenjualan(Base):
    __tablename__ = "transaksi_penjualan"
    __table_args__ = {"schema": "koptumbuh"}
    transaksi_sample_id = Column(String, primary_key=True)
    koperasi_ref = Column(String, ForeignKey("koptumbuh.referensi_koperasi_wilayah.koperasi_ref"))
    nama_pelanggan = Column(String)
    tanggal_dibuat = Column(TIMESTAMP(timezone=True))
    total_pembayaran = Column(Numeric(18, 2))
    status_transaksi = Column(String)
    metode_pembayaran = Column(String)
    dibuat_pada = Column(TIMESTAMP(timezone=True))
    diperbarui_pada = Column(TIMESTAMP(timezone=True))

    hub = relationship("ReferensiKoperasiWilayah", back_populates="transaksi")
