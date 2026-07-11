'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../../../lib/api';
import { formatRp, formatDate } from '../../../../lib/format';
import { Card, ErrorState, LoadingState, Tabs, EmptyState, Badge } from '../../../../components/ui';

export default function CooperativeDetailPage() {
  const params = useParams();
  const ref = decodeURIComponent(String(params.ref));
  const [tab, setTab] = useState('board');

  const detail = useQuery({
    queryKey: ['coop', ref],
    queryFn: async () => (await apiClient<any>(`/admin/cooperatives/${encodeURIComponent(ref)}`)).data!,
  });

  const child = useQuery({
    queryKey: ['coop-child', ref, tab],
    queryFn: async () => {
      const path =
        tab === 'board' ? 'board' :
        tab === 'outlets' ? 'outlets' :
        tab === 'assets' ? 'assets' :
        tab === 'docs' ? 'documents' :
        tab === 'rat' ? 'rat' :
        tab === 'kbli' ? 'kbli' : 'capital';
      return (await apiClient<any[]>(`/admin/cooperatives/${encodeURIComponent(ref)}/${path}`)).data || [];
    },
  });

  if (detail.isError) return <ErrorState onRetry={() => detail.refetch()} />;
  if (detail.isLoading || !detail.data) return <LoadingState />;

  const d = detail.data;

  return (
    <div>
      <div className="mb-4">
        <Link href="/cooperatives" className="text-sm text-primary hover:underline">← Kembali ke Koperasi</Link>
      </div>
      <h1 className="text-2xl font-bold text-gray-800">{d.nama_koperasi}</h1>
      <p className="text-sm text-gray-500 font-mono mb-2">{d.koperasi_ref}</p>
      <div className="flex flex-wrap gap-2 mb-6 text-sm text-gray-600">
        <Badge tone="green">{d.status_registrasi || '—'}</Badge>
        <span>{d.bentuk_koperasi}</span>
        <span>·</span>
        <span>{d.kategori_usaha}</span>
        {d.wilayah?.desa_kelurahan && (
          <>
            <span>·</span>
            <span>{d.wilayah.desa_kelurahan}, {d.wilayah.kab_kota}</span>
          </>
        )}
      </div>

      <Card className="p-4 mb-6 text-sm text-gray-600">
        <p>{d.alamat_lengkap || '—'}</p>
        {d.tentang_koperasi && <p className="mt-2 text-gray-500">{d.tentang_koperasi}</p>}
      </Card>

      <Tabs
        tabs={[
          { id: 'board', label: 'Pengurus' },
          { id: 'outlets', label: 'Gerai' },
          { id: 'assets', label: 'Aset' },
          { id: 'docs', label: 'Dokumen' },
          { id: 'rat', label: 'RAT' },
          { id: 'kbli', label: 'KBLI' },
          { id: 'capital', label: 'Modal' },
        ]}
        active={tab}
        onChange={setTab}
      />

      <Card className="overflow-hidden">
        {child.isError ? (
          <ErrorState onRetry={() => child.refetch()} />
        ) : child.isLoading ? (
          <LoadingState />
        ) : (child.data || []).length === 0 ? (
          <EmptyState message="Tidak ada data." />
        ) : tab === 'board' ? (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b"><tr>
              <th className="text-left p-3 font-medium">Nama</th>
              <th className="text-left p-3 font-medium">Jabatan</th>
              <th className="text-left p-3 font-medium">HP</th>
              <th className="text-left p-3 font-medium">Status</th>
            </tr></thead>
            <tbody>
              {(child.data || []).map((r: any) => (
                <tr key={r.pengurus_ref} className="border-b last:border-0">
                  <td className="p-3 font-medium">{r.nama}</td>
                  <td className="p-3">{r.jabatan}</td>
                  <td className="p-3">{r.no_hp || '—'}</td>
                  <td className="p-3"><Badge>{r.status || '—'}</Badge></td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : tab === 'outlets' ? (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b"><tr>
              <th className="text-left p-3 font-medium">Gerai</th>
              <th className="text-left p-3 font-medium">Jenis</th>
              <th className="text-left p-3 font-medium">Status</th>
              <th className="text-left p-3 font-medium">Internet</th>
            </tr></thead>
            <tbody>
              {(child.data || []).map((r: any) => (
                <tr key={r.gerai_ref} className="border-b last:border-0">
                  <td className="p-3 font-mono text-xs">{r.gerai_ref}</td>
                  <td className="p-3">{r.jenis_gerai_ref || '—'}</td>
                  <td className="p-3"><Badge tone="green">{r.status_gerai || '—'}</Badge></td>
                  <td className="p-3">{r.akses_internet || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : tab === 'assets' ? (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b"><tr>
              <th className="text-left p-3 font-medium">Aset</th>
              <th className="text-left p-3 font-medium">Tipe</th>
              <th className="text-left p-3 font-medium">Status</th>
              <th className="text-right p-3 font-medium">Luas</th>
            </tr></thead>
            <tbody>
              {(child.data || []).map((r: any) => (
                <tr key={r.aset_ref} className="border-b last:border-0">
                  <td className="p-3 font-medium">{r.nama_aset}</td>
                  <td className="p-3">{r.tipe_aset || '—'}</td>
                  <td className="p-3"><Badge>{r.status || '—'}</Badge></td>
                  <td className="p-3 text-right">{r.luas_lahan ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : tab === 'docs' ? (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b"><tr>
              <th className="text-left p-3 font-medium">Dokumen</th>
              <th className="text-left p-3 font-medium">Nomor</th>
              <th className="text-left p-3 font-medium">Berlaku</th>
              <th className="text-left p-3 font-medium">Kadaluarsa</th>
            </tr></thead>
            <tbody>
              {(child.data || []).map((r: any) => (
                <tr key={r.dokumen_ref} className="border-b last:border-0">
                  <td className="p-3 font-medium">{r.nama_dokumen || r.jenis_dokumen_ref}</td>
                  <td className="p-3">{r.nomor || '—'}</td>
                  <td className="p-3 text-xs">{formatDate(r.tanggal_berlaku)}</td>
                  <td className="p-3 text-xs">{formatDate(r.tanggal_kadaluarsa)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : tab === 'rat' ? (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b"><tr>
              <th className="text-left p-3 font-medium">Tahun Buku</th>
              <th className="text-left p-3 font-medium">Tanggal</th>
              <th className="text-right p-3 font-medium">Peserta</th>
              <th className="text-left p-3 font-medium">Status</th>
              <th className="text-left p-3 font-medium">Tahap</th>
            </tr></thead>
            <tbody>
              {(child.data || []).map((r: any) => (
                <tr key={r.rat_sample_id} className="border-b last:border-0">
                  <td className="p-3 font-medium">{r.tahun_buku}</td>
                  <td className="p-3 text-xs">{formatDate(r.tanggal_rat)}</td>
                  <td className="p-3 text-right">{r.jumlah_peserta ?? '—'}</td>
                  <td className="p-3"><Badge>{r.status_rat || '—'}</Badge></td>
                  <td className="p-3">{r.tahap_rat || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : tab === 'kbli' ? (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b"><tr>
              <th className="text-left p-3 font-medium">Kode</th>
              <th className="text-left p-3 font-medium">Nama KBLI</th>
              <th className="text-left p-3 font-medium">Tipe Izin</th>
              <th className="text-left p-3 font-medium">Tahun</th>
            </tr></thead>
            <tbody>
              {(child.data || []).map((r: any) => (
                <tr key={r.id} className="border-b last:border-0">
                  <td className="p-3 font-mono text-xs">{r.kode_kbli}</td>
                  <td className="p-3">{r.nama_kbli}</td>
                  <td className="p-3">{r.tipe_izin_usaha || '—'}</td>
                  <td className="p-3">{r.tahun_kbli || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b"><tr>
              <th className="text-left p-3 font-medium">Sumber</th>
              <th className="text-left p-3 font-medium">Tipe</th>
              <th className="text-right p-3 font-medium">Jumlah</th>
              <th className="text-left p-3 font-medium">Tanggal</th>
            </tr></thead>
            <tbody>
              {(child.data || []).map((r: any) => (
                <tr key={r.modal_ref} className="border-b last:border-0">
                  <td className="p-3 font-medium">{r.nama_sumber || r.tipe_sumber}</td>
                  <td className="p-3">{r.tipe_modal || '—'}</td>
                  <td className="p-3 text-right font-semibold">{formatRp(r.jumlah)}</td>
                  <td className="p-3 text-xs">{formatDate(r.tanggal_diterima)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
