'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient, downloadExport } from '../../../lib/api';
import { formatDate } from '../../../lib/format';
import { Card, ErrorState, LoadingState, EmptyState, Badge } from '../../../components/ui';
import { Download } from 'lucide-react';

export default function ExportPage() {
  const qc = useQueryClient();
  const [format, setFormat] = useState('JSON');
  const [periodStart, setPeriodStart] = useState('');
  const [periodEnd, setPeriodEnd] = useState('');
  const [msg, setMsg] = useState('');

  const history = useQuery({
    queryKey: ['export-history'],
    queryFn: async () => (await apiClient<any[]>('/admin/export/history')).data || [],
  });

  const trigger = useMutation({
    mutationFn: async () => {
      const body: any = { format, export_type: 'TRANSAKSI' };
      if (periodStart) body.period_start = periodStart;
      if (periodEnd) body.period_end = periodEnd;
      return apiClient('/admin/export/simkopdes', { method: 'POST', body: JSON.stringify(body) });
    },
    onSuccess: (res) => {
      const d = res.data as { record_count?: number; format?: string } | undefined;
      setMsg(`Ekspor berhasil: ${d?.record_count ?? 0} baris (${d?.format})`);
      qc.invalidateQueries({ queryKey: ['export-history'] });
    },
    onError: (e: any) => setMsg(e.message || 'Gagal mengekspor'),
  });

  async function handleDownload(id: string) {
    try {
      setMsg('Mengunduh...');
      await downloadExport(id);
      setMsg('Unduhan dimulai');
    } catch (e: any) {
      setMsg(e.message || 'Gagal mengunduh');
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-800 mb-6">Ekspor SIMKOPDES</h1>

      <Card className="p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4">Trigger Ekspor</h2>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          <div>
            <label className="text-sm text-gray-600">Format</label>
            <select
              value={format}
              onChange={(e) => setFormat(e.target.value)}
              className="w-full mt-1 px-3 py-2 border rounded-lg text-sm"
            >
              <option value="JSON">JSON</option>
              <option value="CSV">CSV</option>
              <option value="XLSX">XLSX</option>
            </select>
          </div>
          <div>
            <label className="text-sm text-gray-600">Dari tanggal</label>
            <input
              type="date"
              value={periodStart}
              onChange={(e) => setPeriodStart(e.target.value)}
              className="w-full mt-1 px-3 py-2 border rounded-lg text-sm"
            />
          </div>
          <div>
            <label className="text-sm text-gray-600">Sampai tanggal</label>
            <input
              type="date"
              value={periodEnd}
              onChange={(e) => setPeriodEnd(e.target.value)}
              className="w-full mt-1 px-3 py-2 border rounded-lg text-sm"
            />
          </div>
          <div className="flex items-end">
            <button
              disabled={trigger.isPending}
              onClick={() => trigger.mutate()}
              className="w-full bg-primary text-white py-2 rounded-lg text-sm disabled:opacity-50"
            >
              {trigger.isPending ? 'Memproses...' : 'Ekspor Sekarang'}
            </button>
          </div>
        </div>
        {msg && <p className="text-sm text-gray-500 mt-3">{msg}</p>}
      </Card>

      <Card className="overflow-hidden">
        <div className="p-4 border-b"><h2 className="text-lg font-semibold">Riwayat Ekspor</h2></div>
        {history.isError ? <ErrorState onRetry={() => history.refetch()} /> :
         history.isLoading ? <LoadingState /> :
         (history.data || []).length === 0 ? <EmptyState message="Belum ada riwayat ekspor." /> : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="text-left p-3 font-medium">Tanggal</th>
                <th className="text-left p-3 font-medium">Tipe</th>
                <th className="text-left p-3 font-medium">Format</th>
                <th className="text-right p-3 font-medium">Baris</th>
                <th className="text-left p-3 font-medium">Status</th>
                <th className="text-right p-3 font-medium">Aksi</th>
              </tr>
            </thead>
            <tbody>
              {(history.data || []).map((h) => (
                <tr key={h.id} className="border-b last:border-0">
                  <td className="p-3 text-xs">{formatDate(h.created_at)}</td>
                  <td className="p-3">{h.export_type}</td>
                  <td className="p-3">{h.format}</td>
                  <td className="p-3 text-right">{h.record_count ?? '—'}</td>
                  <td className="p-3">
                    <Badge tone={h.status === 'SUCCESS' ? 'green' : h.status === 'FAILED' ? 'red' : 'yellow'}>
                      {h.status}
                    </Badge>
                  </td>
                  <td className="p-3 text-right">
                    {h.status !== 'FAILED' && (
                      <button
                        onClick={() => handleDownload(h.id)}
                        className="inline-flex items-center gap-1 text-primary text-xs hover:underline"
                      >
                        <Download size={12} /> Unduh
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
