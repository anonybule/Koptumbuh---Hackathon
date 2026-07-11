'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient, downloadExport } from '../../../lib/api';
import { formatDate } from '../../../lib/format';
import { Card, ErrorState, LoadingState, EmptyState, Badge } from '../../../components/ui';
import { Download, CheckCircle2 } from 'lucide-react';

type MappingRow = {
  id: string;
  transaksi_sample_id: string;
  ekspor_id: string | null;
  status: string;
  last_exported_at: string | null;
};

export default function ExportPage() {
  const qc = useQueryClient();
  const [format, setFormat] = useState('JSON');
  const [periodStart, setPeriodStart] = useState('');
  const [periodEnd, setPeriodEnd] = useState('');
  const [msg, setMsg] = useState('');
  const [lastId, setLastId] = useState<string | null>(null);

  const history = useQuery({
    queryKey: ['export-history'],
    queryFn: async () => (await apiClient<any[]>('/admin/export/history')).data || [],
  });

  const mappings = useQuery({
    queryKey: ['export-mappings'],
    queryFn: async () => (await apiClient<MappingRow[]>('/admin/export/mappings')).data || [],
  });

  const trigger = useMutation({
    mutationFn: async () => {
      const body: any = { format, export_type: 'TRANSAKSI' };
      if (periodStart) body.period_start = periodStart;
      if (periodEnd) body.period_end = periodEnd;
      return apiClient('/admin/export/simkopdes', { method: 'POST', body: JSON.stringify(body) });
    },
    onSuccess: (res) => {
      const d = res.data as {
        record_count?: number;
        format?: string;
        ekspor_id?: string;
        storage?: string;
      } | undefined;
      setLastId(d?.ekspor_id || null);
      const storageNote =
        d?.storage === 'local_fallback'
          ? ' (disimpan lokal — MinIO fallback)'
          : d?.storage
            ? ` (storage: ${d.storage})`
            : '';
      setMsg(
        `Ekspor berhasil: ${d?.record_count ?? 0} baris (${d?.format})${storageNote}` +
          (d?.ekspor_id ? ` · id ${d.ekspor_id}` : ''),
      );
      qc.invalidateQueries({ queryKey: ['export-history'] });
      qc.invalidateQueries({ queryKey: ['export-mappings'] });
    },
    onError: (e: any) => {
      setLastId(null);
      setMsg(e.message || 'Gagal mengekspor');
    },
  });

  const acceptOne = useMutation({
    mutationFn: async (id: string) =>
      apiClient(`/admin/export/mappings/${id}/accept`, { method: 'POST', body: '{}' }),
    onSuccess: () => {
      setMsg('Ditandai diterima (simulasi Dinas)');
      qc.invalidateQueries({ queryKey: ['export-mappings'] });
    },
    onError: (e: any) => setMsg(e.message || 'Gagal menandai'),
  });

  const acceptAll = useMutation({
    mutationFn: async () =>
      apiClient('/admin/export/mappings/accept-all', { method: 'POST', body: '{}' }),
    onSuccess: (res) => {
      const n = (res.data as { accepted_count?: number })?.accepted_count ?? 0;
      setMsg(`${n} transaksi ditandai diterima (simulasi Dinas)`);
      qc.invalidateQueries({ queryKey: ['export-mappings'] });
    },
    onError: (e: any) => setMsg(e.message || 'Gagal menandai semua'),
  });

  async function handleDownload(id: string) {
    try {
      setMsg(`Mengunduh ${id}…`);
      await downloadExport(id);
      setMsg(`Unduhan dimulai · ${id}`);
    } catch (e: any) {
      setMsg(e.message || 'Gagal mengunduh');
    }
  }

  const exported = (mappings.data || []).filter((m) => m.status === 'EXPORTED');
  const synced = (mappings.data || []).filter((m) => m.status === 'SYNCED');

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
              onClick={() => {
                if (trigger.isPending) return;
                setMsg('');
                trigger.mutate();
              }}
              className="w-full bg-primary text-white py-2 rounded-lg text-sm disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {trigger.isPending ? 'Memproses...' : 'Ekspor Sekarang'}
            </button>
          </div>
        </div>
        {msg && (
          <p className={`text-sm mt-3 ${trigger.isError ? 'text-red-600' : 'text-gray-600'}`}>
            {msg}
          </p>
        )}
        {lastId && !trigger.isError && (
          <button
            type="button"
            onClick={() => handleDownload(lastId)}
            className="mt-2 inline-flex items-center gap-1 text-sm text-primary hover:underline"
          >
            <Download size={14} /> Unduh ekspor terakhir
          </button>
        )}
      </Card>

      <Card className="p-6 mb-6">
        <div className="flex flex-wrap items-start justify-between gap-3 mb-3">
          <div>
            <h2 className="text-lg font-semibold">Penerimaan SIMKOPDES</h2>
            <p className="text-xs text-gray-500 mt-1 max-w-xl">
              Setelah ekspor, setiap transaksi masuk status EXPORTED. Tombol di bawah mensimulasikan
              penerimaan Dinas (SYNCED) — bukan writeback live ke sistem pemerintah.
            </p>
          </div>
          <button
            type="button"
            disabled={acceptAll.isPending || exported.length === 0}
            onClick={() => acceptAll.mutate()}
            className="inline-flex items-center gap-1.5 px-3 py-2 text-sm rounded-lg bg-emerald-700 text-white disabled:opacity-40"
          >
            <CheckCircle2 size={14} /> Tandai semua diterima ({exported.length})
          </button>
        </div>
        {mappings.isError ? (
          <ErrorState onRetry={() => mappings.refetch()} />
        ) : mappings.isLoading ? (
          <LoadingState />
        ) : (mappings.data || []).length === 0 ? (
          <EmptyState message="Belum ada mapping. Jalankan ekspor dulu." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="text-left p-3 font-medium">Transaksi</th>
                  <th className="text-left p-3 font-medium">Ekspor</th>
                  <th className="text-left p-3 font-medium">Status</th>
                  <th className="text-left p-3 font-medium">Diekspor</th>
                  <th className="text-right p-3 font-medium">Aksi</th>
                </tr>
              </thead>
              <tbody>
                {(mappings.data || []).slice(0, 40).map((m) => (
                  <tr key={m.id} className="border-b last:border-0">
                    <td className="p-3 font-mono text-xs">{m.transaksi_sample_id}</td>
                    <td className="p-3 font-mono text-xs text-gray-500">
                      {m.ekspor_id ? `${m.ekspor_id.slice(0, 8)}…` : '—'}
                    </td>
                    <td className="p-3">
                      <Badge tone={m.status === 'SYNCED' ? 'green' : m.status === 'EXPORTED' ? 'yellow' : 'gray'}>
                        {m.status}
                      </Badge>
                    </td>
                    <td className="p-3 text-xs">{formatDate(m.last_exported_at)}</td>
                    <td className="p-3 text-right">
                      {m.status === 'EXPORTED' && (
                        <button
                          type="button"
                          disabled={acceptOne.isPending}
                          onClick={() => acceptOne.mutate(m.id)}
                          className="text-xs text-emerald-700 hover:underline"
                        >
                          Tandai diterima
                        </button>
                      )}
                      {m.status === 'SYNCED' && (
                        <span className="text-xs text-gray-400">Diterima · {synced.length} total</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Card className="overflow-hidden">
        <div className="p-4 border-b"><h2 className="text-lg font-semibold">Riwayat Ekspor</h2></div>
        {history.isError ? <ErrorState onRetry={() => history.refetch()} /> :
         history.isLoading ? <LoadingState /> :
         (history.data || []).length === 0 ? <EmptyState message="Belum ada riwayat ekspor. Klik Ekspor Sekarang untuk membuat file SIMKOPDES." /> : (
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
