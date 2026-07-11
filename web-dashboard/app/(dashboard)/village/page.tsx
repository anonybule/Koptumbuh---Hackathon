'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../../lib/api';
import { formatRp } from '../../../lib/format';
import { Card, ErrorState, LoadingState, Tabs, EmptyState } from '../../../components/ui';

export default function VillagePage() {
  const [tab, setTab] = useState('commodities');

  const commodities = useQuery({
    queryKey: ['village-commodities'],
    queryFn: async () => (await apiClient<any[]>('/admin/village/commodities')).data || [],
    enabled: tab === 'commodities',
  });

  const profiles = useQuery({
    queryKey: ['village-profiles'],
    queryFn: async () => (await apiClient<any[]>('/admin/village/profiles')).data || [],
    enabled: tab === 'profiles',
  });

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-800 mb-6">Desa</h1>
      <Tabs
        tabs={[
          { id: 'commodities', label: 'Komoditas' },
          { id: 'profiles', label: 'Profil Desa' },
        ]}
        active={tab}
        onChange={setTab}
      />

      {tab === 'commodities' && (
        <Card className="overflow-hidden">
          {commodities.isError ? <ErrorState onRetry={() => commodities.refetch()} /> :
           commodities.isLoading ? <LoadingState /> :
           (commodities.data || []).length === 0 ? <EmptyState message="Belum ada data komoditas." /> : (
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b"><tr>
                <th className="text-left p-3 font-medium">Komoditas</th>
                <th className="text-left p-3 font-medium">Wilayah</th>
                <th className="text-right p-3 font-medium">Luas</th>
                <th className="text-right p-3 font-medium">Volume</th>
                <th className="text-right p-3 font-medium">SDM</th>
                <th className="text-right p-3 font-medium">Nilai Potensi</th>
              </tr></thead>
              <tbody>
                {(commodities.data || []).map((r) => (
                  <tr key={r.komoditas_ref} className="border-b last:border-0">
                    <td className="p-3 font-medium">{r.nama_komoditas}</td>
                    <td className="p-3 text-xs font-mono">{r.kode_wilayah}</td>
                    <td className="p-3 text-right">{r.luas_area ?? '—'}</td>
                    <td className="p-3 text-right">{r.volume ?? '—'}</td>
                    <td className="p-3 text-right">{r.jumlah_sdm ?? '—'}</td>
                    <td className="p-3 text-right">{r.nilai_potensi != null ? formatRp(r.nilai_potensi) : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      )}

      {tab === 'profiles' && (
        <Card className="overflow-hidden">
          {profiles.isError ? <ErrorState onRetry={() => profiles.refetch()} /> :
           profiles.isLoading ? <LoadingState /> :
           (profiles.data || []).length === 0 ? <EmptyState message="Belum ada profil desa." /> : (
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b"><tr>
                <th className="text-left p-3 font-medium">Desa</th>
                <th className="text-left p-3 font-medium">Kecamatan</th>
                <th className="text-right p-3 font-medium">Penduduk</th>
                <th className="text-right p-3 font-medium">L / P</th>
                <th className="text-right p-3 font-medium">Dana Desa</th>
              </tr></thead>
              <tbody>
                {(profiles.data || []).map((r) => (
                  <tr key={r.kode_wilayah} className="border-b last:border-0">
                    <td className="p-3">
                      <p className="font-medium">{r.desa_kelurahan || r.kode_wilayah}</p>
                      <p className="text-xs text-gray-400">{r.kab_kota}, {r.provinsi}</p>
                    </td>
                    <td className="p-3">{r.kecamatan || '—'}</td>
                    <td className="p-3 text-right">{r.total_penduduk?.toLocaleString('id-ID') ?? '—'}</td>
                    <td className="p-3 text-right text-xs">
                      {r.penduduk_laki_laki ?? '—'} / {r.penduduk_perempuan ?? '—'}
                    </td>
                    <td className="p-3 text-right">
                      {r.anggaran_dana_desa != null ? formatRp(r.anggaran_dana_desa) : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      )}
    </div>
  );
}
