from sqlalchemy import Column, String, Numeric, Date, TIMESTAMP, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class ReferensiWilayah(Base):
    __tablename__ = "referensi_wilayah"
    __table_args__ = {"schema": "koptumbuh"}
    kode_wilayah = Column(String, primary_key=True)
    provinsi = Column(String)
    kab_kota = Column(String)
    kecamatan = Column(String)
    desa_kelurahan = Column(String)
    dibuat_pada = Column(TIMESTAMP(timezone=True))
    diperbarui_pada = Column(TIMESTAMP(timezone=True))


class ReferensiKoperasiWilayah(Base):
    """CENTRAL HUB — all child tables FK to this, NOT directly to profil_koperasi."""
    __tablename__ = "referensi_koperasi_wilayah"
    __table_args__ = {"schema": "koptumbuh"}
    koperasi_ref = Column(String, primary_key=True)
    kode_wilayah = Column(String, ForeignKey("koptumbuh.referensi_wilayah.kode_wilayah"))
    dibuat_pada = Column(TIMESTAMP(timezone=True))
    diperbarui_pada = Column(TIMESTAMP(timezone=True))

    wilayah = relationship("ReferensiWilayah")
    profil = relationship("ProfilKoperasi", back_populates="hub", uselist=False)
    anggota = relationship("AnggotaKoperasi", back_populates="hub")
    produk = relationship("ProdukKoperasi", back_populates="hub")
    transaksi = relationship("TransaksiPenjualan", back_populates="hub")


class ReferensiDokumenKoperasi(Base):
    __tablename__ = "referensi_dokumen_koperasi"
    __table_args__ = {"schema": "koptumbuh"}
    jenis_dokumen_ref = Column(String, primary_key=True)
    nama_dokumen = Column(String)
    dibuat_pada = Column(TIMESTAMP(timezone=True))
    diperbarui_pada = Column(TIMESTAMP(timezone=True))


class ReferensiGeraiKoperasi(Base):
    __tablename__ = "referensi_gerai_koperasi"
    __table_args__ = {"schema": "koptumbuh"}
    jenis_gerai_ref = Column(String, primary_key=True)
    nama_jenis_gerai = Column(String)
    dibuat_pada = Column(TIMESTAMP(timezone=True))
    diperbarui_pada = Column(TIMESTAMP(timezone=True))


class ProfilKoperasi(Base):
    __tablename__ = "profil_koperasi"
    __table_args__ = {"schema": "koptumbuh"}
    koperasi_ref = Column(String, ForeignKey("koptumbuh.referensi_koperasi_wilayah.koperasi_ref"), primary_key=True)
    nama_koperasi = Column(String)
    status_registrasi = Column(String)
    bentuk_koperasi = Column(String)
    kategori_usaha = Column(String)
    nik_koperasi = Column(String)
    alamat_lengkap = Column(String)
    kode_pos = Column(String)
    koordinat_dibulatkan = Column(String)
    modal_awal = Column(String)
    sumber_persetujuan = Column(String)
    tentang_koperasi = Column(String)
    pola_pengelolaan = Column(String)
    metode_pengisian = Column(String)
    dibuat_pada = Column(TIMESTAMP(timezone=True))
    diperbarui_pada = Column(TIMESTAMP(timezone=True))

    hub = relationship("ReferensiKoperasiWilayah", back_populates="profil")


class PengurusKoperasi(Base):
    __tablename__ = "pengurus_koperasi"
    __table_args__ = {"schema": "koptumbuh"}
    pengurus_ref = Column(String, primary_key=True)
    koperasi_ref = Column(String, ForeignKey("koptumbuh.referensi_koperasi_wilayah.koperasi_ref"))
    nama = Column(String)
    jabatan = Column(String)
    status = Column(String)
    no_hp = Column(String)
    nik = Column(String)
    jenis_kelamin = Column(String)
    foto_profil = Column(String)
    email = Column(String)
    alamat = Column(String)
    kode_pos = Column(String)
    tanggal_lahir = Column(String)
    status_pendidikan = Column(String)
    periode_mulai = Column(String)
    periode_selesai = Column(Date)
    file_ktp = Column(String)
    sumber_data = Column(String)
    dibuat_pada = Column(TIMESTAMP(timezone=True))
    diperbarui_pada = Column(TIMESTAMP(timezone=True))


class KaryawanKoperasi(Base):
    __tablename__ = "karyawan_koperasi"
    __table_args__ = {"schema": "koptumbuh"}
    karyawan_ref = Column(String, primary_key=True)
    koperasi_ref = Column(String, ForeignKey("koptumbuh.referensi_koperasi_wilayah.koperasi_ref"))
    nama = Column(String)
    jabatan = Column(String)
    nomor_hp_karyawan = Column(String)
    jenis_kelamin = Column(String)
    nik = Column(String)
    email = Column(String)
    status_karyawan = Column(String)
    dibuat_pada = Column(TIMESTAMP(timezone=True))
    diperbarui_pada = Column(TIMESTAMP(timezone=True))


class DokumenKoperasi(Base):
    __tablename__ = "dokumen_koperasi"
    __table_args__ = {"schema": "koptumbuh"}
    dokumen_ref = Column(String, primary_key=True)
    koperasi_ref = Column(String, ForeignKey("koptumbuh.referensi_koperasi_wilayah.koperasi_ref"))
    jenis_dokumen_ref = Column(String, ForeignKey("koptumbuh.referensi_dokumen_koperasi.jenis_dokumen_ref"))
    nomor = Column(String)
    tanggal_berlaku = Column(Date)
    tanggal_kadaluarsa = Column(Date)
    alamat_pada_dokumen = Column(String)
    unggahan_dokumen = Column(String)
    dibuat_pada = Column(TIMESTAMP(timezone=True))
    diperbarui_pada = Column(TIMESTAMP(timezone=True))


class KbliKoperasi(Base):
    __tablename__ = "kbli_koperasi"
    __table_args__ = {"schema": "koptumbuh"}
    __row_id = Column(String, primary_key=True)
    koperasi_ref = Column(String, ForeignKey("koptumbuh.referensi_koperasi_wilayah.koperasi_ref"))
    kode_kbli = Column(String)
    nama_kbli = Column(String)
    tipe_izin_usaha = Column(String)
    tahun_kbli = Column(String)
    dibuat_pada = Column(TIMESTAMP(timezone=True))
    diperbarui_pada = Column(TIMESTAMP(timezone=True))


class AsetKoperasi(Base):
    __tablename__ = "aset_koperasi"
    __table_args__ = {"schema": "koptumbuh"}
    aset_ref = Column(String, primary_key=True)
    koperasi_ref = Column(String, ForeignKey("koptumbuh.referensi_koperasi_wilayah.koperasi_ref"))
    nama_aset = Column(String)
    tipe_aset = Column(String)
    status = Column(String)
    progres_pembangunan = Column(Numeric)
    foto_utama = Column(String)
    foto_sekunder = Column(String)
    dokumen_utama = Column(String)
    dokumen_sekunder = Column(String)
    dokumen_lainnya = Column(String)
    luas_lahan = Column(Numeric)
    panjang_lahan = Column(Numeric)
    lebar_lahan = Column(Numeric)
    akses_jalan = Column(String)
    koordinat_dibulatkan = Column(String)
    dibuat_pada = Column(TIMESTAMP(timezone=True))
    diperbarui_pada = Column(TIMESTAMP(timezone=True))


class GeraiKoperasi(Base):
    __tablename__ = "gerai_koperasi"
    __table_args__ = {"schema": "koptumbuh"}
    gerai_ref = Column(String, primary_key=True)
    koperasi_ref = Column(String, ForeignKey("koptumbuh.referensi_koperasi_wilayah.koperasi_ref"))
    jenis_gerai_ref = Column(String, ForeignKey("koptumbuh.referensi_gerai_koperasi.jenis_gerai_ref"))
    status_gerai = Column(String)
    foto_gerai = Column(String)
    pengisi = Column(String)
    akses_internet = Column(String)
    akses_listrik = Column(String)
    status_kepemilikan_aset_gerai = Column(String)
    status_pemanfaatan_aset_gerai = Column(String)
    sumber_air_bersih = Column(String)
    jenis_bangunan = Column(String)
    koordinat_dibulatkan = Column(String)
    dibuat_pada = Column(TIMESTAMP(timezone=True))
    diperbarui_pada = Column(TIMESTAMP(timezone=True))


class PengajuanDomain(Base):
    __tablename__ = "pengajuan_domain"
    __table_args__ = {"schema": "koptumbuh"}
    domain_ref = Column(String, primary_key=True)
    koperasi_ref = Column(String, ForeignKey("koptumbuh.referensi_koperasi_wilayah.koperasi_ref"))
    domain_koperasi = Column(String)
    status_verifikasi = Column(String)
    status_domain = Column(String)
    dibuat_pada = Column(TIMESTAMP(timezone=True))
    diperbarui_pada = Column(TIMESTAMP(timezone=True))
