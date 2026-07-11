'use client';

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../../lib/api';
import { formatRp } from '../../../lib/format';
import { Card, ErrorState, LoadingState } from '../../../components/ui';

const COOP = 'KOP-JasaAI-A1B2C3D4E5F6';

interface RatRow {
  rat_sample_id: string;
  tahun_buku: string | number;
  tanggal_rat?: string;
  jumlah_peserta?: number;
  status_rat?: string;
  tahap_rat?: string;
  urutan_rat?: string;
}

interface ShuRow {
  bulan?: string;
  total_omzet?: number;
  jumlah_transaksi?: number;
  estimasi_shu?: number;
}

export default function RatPage() {
  const rat = useQuery({
    queryKey: ['rat', COOP],
    queryFn: async () => (await apiClient<RatRow[]>(`/admin/cooperatives/${encodeURIComponent(COOP)}/rat`)).data || [],
  });
  const shu = useQuery({
    queryKey: ['shu'],
    queryFn: async () => (await apiClient<ShuRow[]>('/admin/shu/estimate')).data || [],
  });
  const kpi = useQuery({
    queryKey: ['rat-kpi'],
    queryFn: async () => (await apiClient<any>('/admin/dashboard/kpi')).data,
  });

  if (rat.isError && shu.isError) {
    return <ErrorState onRetry={() => { rat.refetch(); shu.refetch(); }} />;
  }

  const latestShu = (shu.data || [])[0];

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-800 mb-6">Rapat Anggota Tahunan (RAT)</h1>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <Card className="p-4">
          <p className="text-sm text-gray-500">Omzet (KPI)</p>
          <p className="text-xl font-bold">{formatRp(kpi.data?.total_revenue || 0)}</p>
        </Card>
        <Card className="p-4">
          <p className="text-sm text-gray-500">Estimasi SHU (bulan terakhir)</p>
          <p className="text-xl font-bold">{formatRp(latestShu?.estimasi_shu || 0)}</p>
        </Card>
        <Card className="p-4">
          <p className="text-sm text-gray-500">Jumlah RAT</p>
          <p className="text-xl font-bold">{(rat.data || []).length}</p>
        </Card>
      </div>

      <Card className="overflow-hidden mb-6">
        <div className="p-4 border-b font-semibold">Riwayat RAT</div>
        {rat.isLoading ? <LoadingState /> : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="text-left p-3">Tahun Buku</th>
                <th className="text-left p-3">Urutan</th>
                <th className="text-left p-3">Tanggal</th>
                <th className="text-left p-3">Peserta</th>
                <th className="text-left p-3">Status</th>
              </tr>
            </thead>
            <tbody>
              {(rat.data || []).map((r) => (
                <tr key={r.rat_sample_id} className="border-b">
                  <td className="p-3">{r.tahun_buku}</td>
                  <td className="p-3">{r.urutan_rat || r.tahap_rat || '—'}</td>
                  <td className="p-3">{r.tanggal_rat || '—'}</td>
                  <td className="p-3">{r.jumlah_peserta ?? '—'}</td>
                  <td className="p-3">
                    <span className="px-2 py-0.5 bg-green-100 text-green-700 rounded-full text-xs">
                      {r.status_rat || '—'}
                    </span>
                  </td>
                </tr>
              ))}
              {(rat.data || []).length === 0 && (
                <tr><td colSpan={5} className="p-8 text-center text-gray-400">Belum ada data RAT.</td></tr>
              )}
            </tbody>
          </table>
        )}
      </Card>

      <Card className="overflow-hidden">
        <div className="p-4 border-b font-semibold">Estimasi SHU bulanan</div>
        {shu.isLoading ? <LoadingState /> : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="text-left p-3">Bulan</th>
                <th className="text-left p-3">Omzet</th>
                <th className="text-left p-3">TX</th>
                <th className="text-left p-3">Estimasi SHU</th>
              </tr>
            </thead>
            <tbody>
              {(shu.data || []).slice(0, 12).map((s, i) => (
                <tr key={i} className="border-b">
                  <td className="p-3">{String(s.bulan || '').slice(0, 10)}</td>
                  <td className="p-3">{formatRp(s.total_omzet || 0)}</td>
                  <td className="p-3">{s.jumlah_transaksi || 0}</td>
                  <td className="p-3 font-medium">{formatRp(s.estimasi_shu || 0)}</td>
                </tr>
              ))}
              {(shu.data || []).length === 0 && (
                <tr><td colSpan={4} className="p-8 text-center text-gray-400">Belum ada estimasi.</td></tr>
              )}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
