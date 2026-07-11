from sqlalchemy import Column, String, Integer, Numeric, Date, TIMESTAMP, BigInteger, Float, ForeignKey
from app.database import Base


class ReferensiKomoditasDesa(Base):
    __tablename__ = "referensi_komoditas_desa"
    __table_args__ = {"schema": "koptumbuh"}
    komoditas_ref = Column(String, primary_key=True)
    kode_wilayah = Column(String, ForeignKey("koptumbuh.referensi_wilayah.kode_wilayah"))
    nama_komoditas = Column(String)
    luas_area = Column(String)
    volume = Column(String)
    jumlah_sdm_terlibat = Column(Float)
    nilai_potensi_desa = Column(BigInteger)
    dibuat_pada = Column(TIMESTAMP(timezone=True))
    diperbarui_pada = Column(TIMESTAMP(timezone=True))


class ReferensiProfilDesa(Base):
    __tablename__ = "referensi_profil_desa"
    __table_args__ = {"schema": "koptumbuh"}
    kode_wilayah = Column(String, ForeignKey("koptumbuh.referensi_wilayah.kode_wilayah"), primary_key=True)
    tahun_populasi = Column(Integer)
    total_penduduk = Column(Integer)
    penduduk_laki_laki = Column(Integer)
    penduduk_perempuan = Column(Integer)
    tahun_pendanaan = Column(Integer)
    anggaran_dana_desa = Column(Numeric(18, 2))
    dibuat_pada = Column(TIMESTAMP(timezone=True))
    diperbarui_pada = Column(TIMESTAMP(timezone=True))


class RatKoperasi(Base):
    __tablename__ = "rat_koperasi"
    __table_args__ = {"schema": "koptumbuh"}
    rat_sample_id = Column(String, primary_key=True)
    koperasi_ref = Column(String, ForeignKey("koptumbuh.referensi_koperasi_wilayah.koperasi_ref"))
    jenis_sektor_koperasi = Column(String)
    urutan_rat = Column(String)
    tahun_buku = Column(Integer)
    tahun_rencana_kerja = Column(Integer)
    tahun_rencana_anggaran = Column(Integer)
    tanggal_rat = Column(Date)
    jumlah_peserta_rat = Column(Integer)
    status_rat = Column(String)
    tahap_rat = Column(String)
    laporan_posisi_keuangan = Column(String)
    laporan_hasil_usaha = Column(String)
    rapb_posisi_keuangan = Column(String)
    rapb_hasil_usaha = Column(String)
    dibuat_pada = Column(TIMESTAMP(timezone=True))
    diperbarui_pada = Column(TIMESTAMP(timezone=True))
