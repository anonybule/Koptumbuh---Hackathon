from sqlalchemy import Column, String, Numeric, Date, TIMESTAMP, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base


class AnggotaKoperasi(Base):
    __tablename__ = "anggota_koperasi"
    __table_args__ = {"schema": "koptumbuh"}
    anggota_ref = Column(String, primary_key=True)
    koperasi_ref = Column(String, ForeignKey("koptumbuh.referensi_koperasi_wilayah.koperasi_ref"))
    nama = Column(String)
    nik = Column(String)
    kode_wilayah = Column(String, ForeignKey("koptumbuh.referensi_wilayah.kode_wilayah"))
    jenis_kelamin = Column(String)
    status_keanggotaan = Column(String)
    tanggal_terdaftar = Column(Date)
    dibuat_pada = Column(TIMESTAMP(timezone=True))
    diperbarui_pada = Column(TIMESTAMP(timezone=True))
    file_ktp = Column(String)
    status_akun = Column(String)
    pekerjaan = Column(String)

    hub = relationship("ReferensiKoperasiWilayah", back_populates="anggota")
    simpanan = relationship("SimpananAnggota", back_populates="anggota")


class SimpananAnggota(Base):
    __tablename__ = "simpanan_anggota"
    __table_args__ = {"schema": "koptumbuh"}
    simpanan_ref = Column(String, primary_key=True)
    koperasi_ref = Column(String, ForeignKey("koptumbuh.referensi_koperasi_wilayah.koperasi_ref"))
    anggota_ref = Column(String, ForeignKey("koptumbuh.anggota_koperasi.anggota_ref"))
    periode_pembayaran = Column(String)
    jumlah_simpanan = Column(Numeric(18, 2))
    status = Column(String)
    dibuat_pada = Column(TIMESTAMP(timezone=True))
    dibayar_pada = Column(TIMESTAMP(timezone=True))

    anggota = relationship("AnggotaKoperasi", back_populates="simpanan")
