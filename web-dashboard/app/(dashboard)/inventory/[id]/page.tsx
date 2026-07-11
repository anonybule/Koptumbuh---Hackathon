'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../../../lib/api';
import { formatDate } from '../../../../lib/format';
import { Card, ErrorState, LoadingState, Badge, EmptyState } from '../../../../components/ui';
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
} from 'recharts';

interface Detail {
  id: string;
  name: string;
  stock: number;
  barcode?: string;
  lokasi_simpan?: string;
  unit?: string;
  is_subsidi?: boolean;
  low_stock?: boolean;
  chart: { date: string; type: string; qty: number }[];
}

interface Movement {
  date: string;
  type: string;
  ref_id: string;
  qty: number;
  harga: number | null;
  status: string;
}

export default function InventoryDetailPage() {
  const params = useParams();
  const id = decodeURIComponent(String(params.id));
  const qc = useQueryClient();
  const [delta, setDelta] = useState(0);
  const [reason, setReason] = useState('');
  const [msg, setMsg] = useState('');

  const detail = useQuery({
    queryKey: ['inventory-detail', id],
    queryFn: async () => (await apiClient<Detail>(`/admin/inventory/${encodeURIComponent(id)}`)).data!,
  });

  const movements = useQuery({
    queryKey: ['inventory-movements', id],
    queryFn: async () =>
      (await apiClient<Movement[]>(`/admin/inventory/${encodeURIComponent(id)}/movements`)).data || [],
  });

  const adjust = useMutation({
    mutationFn: async () => {
      const res = await apiClient('/admin/inventory/adjustments', {
        method: 'POST',
        body: JSON.stringify({ produk_sample_id: id, quantity_delta: delta, reason }),
      });
      if (!res.success) throw new Error('Gagal');
      return res;
    },
    onSuccess: () => {
      setMsg('Penyesuaian berhasil');
      setDelta(0);
      setReason('');
      qc.invalidateQueries({ queryKey: ['inventory-detail', id] });
      qc.invalidateQueries({ queryKey: ['inventory-movements', id] });
      qc.invalidateQueries({ queryKey: ['inventory'] });
    },
    onError: (e: any) => setMsg(e.message || 'Gagal menyesuaikan stok'),
  });

  if (detail.isError) return <ErrorState onRetry={() => detail.refetch()} />;
  if (detail.isLoading || !detail.data) return <LoadingState />;

  const d = detail.data;
  const chartData = [...(d.chart || [])]
    .reverse()
    .map((c) => ({
      date: (c.date || '').slice(0, 10),
      masuk: c.type === 'MASUK' ? c.qty : 0,
      keluar: c.type === 'KELUAR' ? Math.abs(c.qty) : 0,
      adjust: c.type === 'ADJUST' ? c.qty : 0,
    }));

  return (
    <div>
      <div className="mb-4">
        <Link href="/inventory" className="text-sm text-primary hover:underline">← Kembali ke Inventaris</Link>
      </div>
      <div className="flex flex-wrap items-start justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">{d.name}</h1>
          <p className="text-sm text-gray-500 font-mono mt-1">{d.id}</p>
        </div>
        <div className="text-right">
          <p className="text-sm text-gray-500">Stok saat ini</p>
          <p className={`text-3xl font-bold ${d.low_stock ? 'text-red-600' : 'text-gray-800'}`}>{d.stock}</p>
          {d.low_stock && <Badge tone="red">Stok rendah</Badge>}
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {[
          { label: 'Barcode', value: d.barcode || '—' },
          { label: 'Lokasi', value: d.lokasi_simpan || '—' },
          { label: 'Unit', value: d.unit || '—' },
          { label: 'Subsidi', value: d.is_subsidi ? 'Ya' : 'Tidak' },
        ].map((x) => (
          <Card key={x.label} className="p-4">
            <p className="text-xs text-gray-500">{x.label}</p>
            <p className="font-medium text-gray-800 mt-1">{x.value}</p>
          </Card>
        ))}
      </div>

      <Card className="p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4">Riwayat Pergerakan</h2>
        {chartData.length === 0 ? (
          <EmptyState message="Belum ada pergerakan stok." />
        ) : (
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="date" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Legend />
                <Bar dataKey="masuk" fill="#a0ba3b" name="Masuk" stackId="a" />
                <Bar dataKey="keluar" fill="#065366" name="Keluar" stackId="a" />
                <Bar dataKey="adjust" fill="#f59e0b" name="Adjust" stackId="a" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        <Card className="p-6 lg:col-span-1">
          <h2 className="text-lg font-semibold mb-4">Penyesuaian Stok</h2>
          <div className="space-y-3">
            <div>
              <label className="text-sm text-gray-600">Delta (+/-)</label>
              <input
                type="number"
                value={delta || ''}
                onChange={(e) => setDelta(+e.target.value)}
                className="w-full mt-1 px-3 py-2 border rounded-lg text-sm"
              />
            </div>
            <div>
              <label className="text-sm text-gray-600">Alasan *</label>
              <input
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="Contoh: koreksi hitung fisik"
                className="w-full mt-1 px-3 py-2 border rounded-lg text-sm"
              />
            </div>
            <button
              disabled={!reason || delta === 0 || adjust.isPending}
              onClick={() => adjust.mutate()}
              className="w-full bg-primary text-white py-2 rounded-lg text-sm disabled:opacity-50"
            >
              {adjust.isPending ? 'Menyimpan...' : 'Simpan Penyesuaian'}
            </button>
            {msg && <p className="text-sm text-gray-500">{msg}</p>}
          </div>
        </Card>

        <Card className="overflow-hidden lg:col-span-2">
          <div className="p-4 border-b">
            <h2 className="text-lg font-semibold">Log Pergerakan</h2>
          </div>
          {movements.isLoading ? <LoadingState /> : (movements.data || []).length === 0 ? (
            <EmptyState message="Belum ada log." />
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="text-left p-3 font-medium">Tanggal</th>
                  <th className="text-left p-3 font-medium">Tipe</th>
                  <th className="text-right p-3 font-medium">Qty</th>
                  <th className="text-left p-3 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {(movements.data || []).map((m, i) => (
                  <tr key={i} className="border-b last:border-0">
                    <td className="p-3 text-xs text-gray-500">{formatDate(m.date)}</td>
                    <td className="p-3">
                      <Badge tone={m.type === 'MASUK' ? 'green' : m.type === 'KELUAR' ? 'blue' : 'yellow'}>
                        {m.type}
                      </Badge>
                    </td>
                    <td className="p-3 text-right font-medium">{m.qty}</td>
                    <td className="p-3 text-xs text-gray-500">{m.status || '—'}</td>
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
