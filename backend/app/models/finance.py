from sqlalchemy import Column, String, Integer, Numeric, Date, TIMESTAMP, ForeignKey
from app.database import Base


class AkunBankKoperasi(Base):
    __tablename__ = "akun_bank_koperasi"
    __table_args__ = {"schema": "koptumbuh"}
    akun_bank_ref = Column(String, primary_key=True)
    koperasi_ref = Column(String, ForeignKey("koptumbuh.referensi_koperasi_wilayah.koperasi_ref"))
    nama_rekening = Column(String)
    nama_bank = Column(String)
    dibuat_pada = Column(TIMESTAMP(timezone=True))
    diperbarui_pada = Column(TIMESTAMP(timezone=True))


class ModalKoperasi(Base):
    __tablename__ = "modal_koperasi"
    __table_args__ = {"schema": "koptumbuh"}
    modal_ref = Column(String, primary_key=True)
    koperasi_ref = Column(String, ForeignKey("koptumbuh.referensi_koperasi_wilayah.koperasi_ref"))
    nomor_perjanjian = Column(String)
    tipe_sumber = Column(String)
    nama_sumber = Column(String)
    tipe_modal = Column(String)
    jumlah = Column(Numeric(18, 2))
    tanggal_diterima = Column(Date)
    file_perjanjian = Column(String)
    dibuat_pada = Column(TIMESTAMP(timezone=True))
    diperbarui_pada = Column(TIMESTAMP(timezone=True))


class PengajuanRekeningBank(Base):
    __tablename__ = "pengajuan_rekening_bank"
    __table_args__ = {"schema": "koptumbuh"}
    pengajuan_rekening_ref = Column(String, primary_key=True)
    koperasi_ref = Column(String, ForeignKey("koptumbuh.referensi_koperasi_wilayah.koperasi_ref"))
    nik = Column(String)
    penanggung_jawab = Column(String)
    nomor_penanggung_jawab = Column(String)
    status = Column(String)
    kode_bank = Column(String)
    nama_bank = Column(String)
    dibuat_pada = Column(TIMESTAMP(timezone=True))
    diperbarui_pada = Column(TIMESTAMP(timezone=True))


class PengajuanPembiayaan(Base):
    __tablename__ = "pengajuan_pembiayaan"
    __table_args__ = {"schema": "koptumbuh"}
    pengajuan_pembiayaan_ref = Column(String, primary_key=True)
    koperasi_ref = Column(String, ForeignKey("koptumbuh.referensi_koperasi_wilayah.koperasi_ref"))
    nik = Column(String)
    penanggung_jawab = Column(String)
    nomor_penanggung_jawab = Column(String)
    status_permohonan = Column(String)
    formulir_permohonan_pembiayaan = Column(String)
    nominal_permohonan = Column(Numeric(18, 2))
    tenor = Column(Integer)
    tujuan_permohonan = Column(String)
    dibuat_pada = Column(TIMESTAMP(timezone=True))
    diperbarui_pada = Column(TIMESTAMP(timezone=True))


class PengajuanKemitraan(Base):
    __tablename__ = "pengajuan_kemitraan"
    __table_args__ = {"schema": "koptumbuh"}
    pengajuan_kemitraan_ref = Column(String, primary_key=True)
    koperasi_ref = Column(String, ForeignKey("koptumbuh.referensi_koperasi_wilayah.koperasi_ref"))
    nik = Column(String)
    penanggung_jawab = Column(String)
    nomor_penanggung_jawab = Column(String)
    status_permohonan = Column(String)
    bisnis_kemitraan = Column(String)
    paket_kemitraan = Column(String)
    formulir_permohonan = Column(String)
    ktp_penanggung_jawab = Column(String)
    tipe_kemitraan = Column(String)
    catatan = Column(String)
    dibuat_pada = Column(TIMESTAMP(timezone=True))
    diperbarui_pada = Column(TIMESTAMP(timezone=True))
