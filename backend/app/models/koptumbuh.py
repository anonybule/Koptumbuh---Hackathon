from sqlalchemy import Column, String, Integer, Numeric, Date, TIMESTAMP, Text, Boolean, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import Base
import uuid


class PenggunaKoptumbuh(Base):
    __tablename__ = "pengguna_koptumbuh"
    __table_args__ = {"schema": "koptumbuh"}
    pengguna_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    koperasi_ref = Column(String, ForeignKey("koptumbuh.referensi_koperasi_wilayah.koperasi_ref"))
    pengurus_ref = Column(String, ForeignKey("koptumbuh.pengurus_koperasi.pengurus_ref"))
    karyawan_ref = Column(String, ForeignKey("koptumbuh.karyawan_koperasi.karyawan_ref"))
    nama = Column(String, nullable=False)
    nomor_whatsapp = Column(String, nullable=False)
    role = Column(String, nullable=False)
    status_aktif = Column(Boolean, default=True)
    consent_at = Column(TIMESTAMP(timezone=True))
    created_at = Column(TIMESTAMP(timezone=True))
    updated_at = Column(TIMESTAMP(timezone=True))


class PemasokKoptumbuh(Base):
    __tablename__ = "pemasok_koptumbuh"
    __table_args__ = {"schema": "koptumbuh"}
    pemasok_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    koperasi_ref = Column(String, ForeignKey("koptumbuh.referensi_koperasi_wilayah.koperasi_ref"))
    nama_pemasok = Column(String, nullable=False)
    nomor_hp = Column(String)
    alamat = Column(String)
    lead_time_hari = Column(Numeric(8, 2))
    payment_term = Column(String)
    status_aktif = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP(timezone=True))
    updated_at = Column(TIMESTAMP(timezone=True))


class PelangganKoptumbuh(Base):
    __tablename__ = "pelanggan_koptumbuh"
    __table_args__ = {"schema": "koptumbuh"}
    pelanggan_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    koperasi_ref = Column(String, ForeignKey("koptumbuh.referensi_koperasi_wilayah.koperasi_ref"))
    anggota_ref = Column(String, ForeignKey("koptumbuh.anggota_koperasi.anggota_ref"))
    nama_pelanggan = Column(String, nullable=False)
    nomor_whatsapp = Column(String)
    status_aktif = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP(timezone=True))
    updated_at = Column(TIMESTAMP(timezone=True))


class PesanMasuk(Base):
    __tablename__ = "pesan_masuk"
    __table_args__ = {"schema": "koptumbuh"}
    pesan_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    koperasi_ref = Column(String, ForeignKey("koptumbuh.referensi_koperasi_wilayah.koperasi_ref"))
    pengguna_id = Column(UUID(as_uuid=True), ForeignKey("koptumbuh.pengguna_koptumbuh.pengguna_id"))
    whatsapp_message_id = Column(String, unique=True)
    input_type = Column(String, nullable=False)
    raw_text = Column(Text)
    media_url = Column(String)
    media_mime_type = Column(String)
    status = Column(String, default="RECEIVED")
    received_at = Column(TIMESTAMP(timezone=True))
    processed_at = Column(TIMESTAMP(timezone=True))
    created_at = Column(TIMESTAMP(timezone=True))


class ParsingPesan(Base):
    __tablename__ = "parsing_pesan"
    __table_args__ = {"schema": "koptumbuh"}
    parsing_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pesan_id = Column(UUID(as_uuid=True), ForeignKey("koptumbuh.pesan_masuk.pesan_id"))
    parser_version = Column(String)
    detected_intent = Column(String)
    transcription_text = Column(Text)
    extracted_payload = Column(JSONB, default=dict)
    confidence_score = Column(Numeric(5, 4))
    validation_errors = Column(JSONB, default=list)
    status = Column(String, default="DRAFT")
    created_at = Column(TIMESTAMP(timezone=True))


class KonfirmasiPengguna(Base):
    __tablename__ = "konfirmasi_pengguna"
    __table_args__ = {"schema": "koptumbuh"}
    konfirmasi_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pesan_id = Column(UUID(as_uuid=True), ForeignKey("koptumbuh.pesan_masuk.pesan_id"))
    parsing_id = Column(UUID(as_uuid=True), ForeignKey("koptumbuh.parsing_pesan.parsing_id"))
    pengguna_id = Column(UUID(as_uuid=True), ForeignKey("koptumbuh.pengguna_koptumbuh.pengguna_id"))
    keputusan = Column(String, nullable=False)
    corrected_payload = Column(JSONB)
    confirmed_at = Column(TIMESTAMP(timezone=True))


class RelasiTransaksiPihak(Base):
    __tablename__ = "relasi_transaksi_pihak"
    __table_args__ = {"schema": "koptumbuh"}
    relasi_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaksi_sample_id = Column(String, ForeignKey("koptumbuh.transaksi_penjualan.transaksi_sample_id"))
    anggota_ref = Column(String, ForeignKey("koptumbuh.anggota_koperasi.anggota_ref"))
    pelanggan_id = Column(UUID(as_uuid=True), ForeignKey("koptumbuh.pelanggan_koptumbuh.pelanggan_id"))
    pemasok_id = Column(UUID(as_uuid=True), ForeignKey("koptumbuh.pemasok_koptumbuh.pemasok_id"))
    relationship_type = Column(String, nullable=False)
    match_method = Column(String)
    match_confidence = Column(Numeric(5, 4))
    created_at = Column(TIMESTAMP(timezone=True))


class ArtikelPengetahuan(Base):
    __tablename__ = "artikel_pengetahuan"
    __table_args__ = {"schema": "koptumbuh"}
    artikel_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    koperasi_ref = Column(String, ForeignKey("koptumbuh.referensi_koperasi_wilayah.koperasi_ref"))
    judul = Column(String, nullable=False)
    kategori = Column(String)
    isi = Column(Text, nullable=False)
    sumber = Column(String)
    versi = Column(String)
    tags = Column(JSONB)
    status_aktif = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP(timezone=True))
    updated_at = Column(TIMESTAMP(timezone=True))


class Rekomendasi(Base):
    __tablename__ = "rekomendasi"
    __table_args__ = {"schema": "koptumbuh"}
    rekomendasi_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    koperasi_ref = Column(String, ForeignKey("koptumbuh.referensi_koperasi_wilayah.koperasi_ref"))
    jenis = Column(String, nullable=False)
    judul = Column(String, nullable=False)
    isi_rekomendasi = Column(Text, nullable=False)
    alasan = Column(Text)
    produk_sample_id = Column(String, ForeignKey("koptumbuh.produk_koperasi.produk_sample_id"))
    anggota_ref = Column(String, ForeignKey("koptumbuh.anggota_koperasi.anggota_ref"))
    pemasok_id = Column(UUID(as_uuid=True), ForeignKey("koptumbuh.pemasok_koptumbuh.pemasok_id"))
    transaksi_sample_id = Column(String, ForeignKey("koptumbuh.transaksi_penjualan.transaksi_sample_id"))
    priority = Column(String, default="MEDIUM")
    status = Column(String, default="NEW")
    explanation_payload = Column(JSONB, default=dict)
    generated_at = Column(TIMESTAMP(timezone=True))
    actioned_at = Column(TIMESTAMP(timezone=True))
    expires_at = Column(TIMESTAMP(timezone=True))


class NotifikasiLog(Base):
    __tablename__ = "notifikasi_log"
    __table_args__ = {"schema": "koptumbuh"}
    notifikasi_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    koperasi_ref = Column(String, ForeignKey("koptumbuh.referensi_koperasi_wilayah.koperasi_ref"))
    pengguna_id = Column(UUID(as_uuid=True), ForeignKey("koptumbuh.pengguna_koptumbuh.pengguna_id"))
    rekomendasi_id = Column(UUID(as_uuid=True), ForeignKey("koptumbuh.rekomendasi.rekomendasi_id"))
    pesan_id = Column(UUID(as_uuid=True), ForeignKey("koptumbuh.pesan_masuk.pesan_id"))
    channel = Column(String, nullable=False)
    message_type = Column(String, nullable=False)
    title = Column(String)
    content = Column(Text, nullable=False)
    provider_message_id = Column(String)
    status = Column(String, default="QUEUED")
    sent_at = Column(TIMESTAMP(timezone=True))
    read_at = Column(TIMESTAMP(timezone=True))
    created_at = Column(TIMESTAMP(timezone=True))


class PenyesuaianStok(Base):
    __tablename__ = "penyesuaian_stok"
    __table_args__ = {"schema": "koptumbuh"}
    penyesuaian_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    koperasi_ref = Column(String, ForeignKey("koptumbuh.referensi_koperasi_wilayah.koperasi_ref"))
    produk_sample_id = Column(String, ForeignKey("koptumbuh.produk_koperasi.produk_sample_id"))
    pengguna_id = Column(UUID(as_uuid=True), ForeignKey("koptumbuh.pengguna_koptumbuh.pengguna_id"))
    quantity_delta = Column(Numeric(18, 3), nullable=False)
    reason = Column(Text, nullable=False)
    source_message_id = Column(UUID(as_uuid=True), ForeignKey("koptumbuh.pesan_masuk.pesan_id"))
    created_at = Column(TIMESTAMP(timezone=True))


class MappingIntegrasi(Base):
    __tablename__ = "mapping_integrasi"
    __table_args__ = {"schema": "koptumbuh"}
    mapping_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    koperasi_ref = Column(String, ForeignKey("koptumbuh.referensi_koperasi_wilayah.koperasi_ref"))
    entity_type = Column(String, nullable=False)
    local_table = Column(String, nullable=False)
    local_id = Column(String, nullable=False)
    external_table = Column(String, nullable=False)
    external_reference = Column(String)
    mapping_status = Column(String, default="PENDING")
    validation_errors = Column(JSONB, default=list)
    last_exported_at = Column(TIMESTAMP(timezone=True))
    created_at = Column(TIMESTAMP(timezone=True))
    updated_at = Column(TIMESTAMP(timezone=True))


class EksporLog(Base):
    __tablename__ = "ekspor_log"
    __table_args__ = {"schema": "koptumbuh"}
    ekspor_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    koperasi_ref = Column(String, ForeignKey("koptumbuh.referensi_koperasi_wilayah.koperasi_ref"))
    pengguna_id = Column(UUID(as_uuid=True), ForeignKey("koptumbuh.pengguna_koptumbuh.pengguna_id"))
    export_type = Column(String, nullable=False)
    format = Column(String, nullable=False)
    period_start = Column(TIMESTAMP(timezone=True))
    period_end = Column(TIMESTAMP(timezone=True))
    file_url = Column(String)
    record_count = Column(Integer)
    status = Column(String, default="PROCESSING")
    error_detail = Column(JSONB)
    created_at = Column(TIMESTAMP(timezone=True))
