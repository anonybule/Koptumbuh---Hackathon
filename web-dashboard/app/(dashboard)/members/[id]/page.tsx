'use client';

import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../../../lib/api';
import { formatRp, formatDate } from '../../../../lib/format';
import { Card, ErrorState, LoadingState, EmptyState, Badge } from '../../../../components/ui';

export default function MemberDetailPage() {
  const params = useParams();
  const id = decodeURIComponent(String(params.id));

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['member', id],
    queryFn: async () => (await apiClient<any>(`/admin/members/${encodeURIComponent(id)}`)).data!,
  });

  if (isError) return <ErrorState onRetry={() => refetch()} />;
  if (isLoading || !data) return <LoadingState />;

  return (
    <div>
      <div className="mb-4">
        <Link href="/members" className="text-sm text-primary hover:underline">← Kembali ke Anggota</Link>
      </div>
      <div className="flex flex-wrap justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">{data.name}</h1>
          <p className="text-sm text-gray-500 font-mono">{data.id}</p>
        </div>
        <div className="text-right">
          <p className="text-sm text-gray-500">Total Simpanan</p>
          <p className="text-2xl font-bold text-primary">{formatRp(data.savings_total)}</p>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {[
          { label: 'NIK', value: data.nik || '—' },
          { label: 'JK', value: data.gender || '—' },
          { label: 'Status', value: data.status || '—' },
          { label: 'Pekerjaan', value: data.pekerjaan || '—' },
          { label: 'Terdaftar', value: formatDate(data.registered) },
          { label: 'Status Akun', value: data.status_akun || '—' },
          { label: 'Koperasi', value: data.koperasi_ref || '—' },
          { label: 'Wilayah', value: data.kode_wilayah || '—' },
        ].map((x) => (
          <Card key={x.label} className="p-4">
            <p className="text-xs text-gray-500">{x.label}</p>
            <p className="font-medium text-gray-800 mt-1 text-sm break-all">{x.value}</p>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="overflow-hidden">
          <div className="p-4 border-b"><h2 className="text-lg font-semibold">Simpanan</h2></div>
          {(data.savings || []).length === 0 ? (
            <EmptyState message="Belum ada simpanan." />
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="text-left p-3 font-medium">Periode</th>
                  <th className="text-right p-3 font-medium">Jumlah</th>
                  <th className="text-left p-3 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {data.savings.map((s: any) => (
                  <tr key={s.simpanan_ref} className="border-b last:border-0">
                    <td className="p-3">{s.periode || formatDate(s.created)}</td>
                    <td className="p-3 text-right font-semibold">{formatRp(s.jumlah)}</td>
                    <td className="p-3"><Badge tone="green">{s.status || '—'}</Badge></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>

        <Card className="overflow-hidden">
          <div className="p-4 border-b"><h2 className="text-lg font-semibold">Aktivitas Transaksi</h2></div>
          {(data.activity || []).length === 0 ? (
            <EmptyState message="Belum ada transaksi." />
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="text-left p-3 font-medium">Tanggal</th>
                  <th className="text-right p-3 font-medium">Total</th>
                  <th className="text-left p-3 font-medium">Bayar</th>
                </tr>
              </thead>
              <tbody>
                {data.activity.map((a: any) => (
                  <tr key={a.transaksi_sample_id} className="border-b last:border-0">
                    <td className="p-3 text-xs">{formatDate(a.date)}</td>
                    <td className="p-3 text-right font-semibold">{formatRp(a.total)}</td>
                    <td className="p-3 text-xs">{a.method || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      </div>
    </div>
  );
}
