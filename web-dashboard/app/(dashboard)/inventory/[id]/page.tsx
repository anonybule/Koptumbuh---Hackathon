'use client';

import { useMemo, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../../../lib/api';
import { formatDate } from '../../../../lib/format';
import { Card, ErrorState, LoadingState, Badge, EmptyState } from '../../../../components/ui';
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
} from 'recharts';

const SERIES = {
  masuk: { key: 'masuk', label: 'Masuk', color: '#a0ba3b' },
  keluar: { key: 'keluar', label: 'Keluar', color: '#065366' },
  adjust: { key: 'adjust', label: 'Adjust', color: '#d97706' },
} as const;

function formatAxisDate(value: string) {
  if (!value || value.length < 10) return value;
  const d = new Date(`${value.slice(0, 10)}T00:00:00`);
  if (Number.isNaN(d.getTime())) return value.slice(5);
  return d.toLocaleDateString('id-ID', { day: '2-digit', month: 'short' });
}

function MovementTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ dataKey?: string; value?: number; color?: string; name?: string }>;
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  const total = payload.reduce((s, p) => s + (Number(p.value) || 0), 0);
  return (
    <div className="rounded-lg border border-gray-200 bg-white px-3 py-2.5 shadow-sm min-w-[160px]">
      <p className="text-xs font-semibold text-gray-800 mb-2">{formatAxisDate(String(label || ''))}</p>
      <div className="space-y-1">
        {payload.map((p) => (
          <div key={String(p.dataKey)} className="flex items-center justify-between gap-4 text-xs">
            <span className="flex items-center gap-1.5 text-gray-600">
              <span className="inline-block h-2 w-2 rounded-sm" style={{ background: p.color }} />
              {p.name}
            </span>
            <span className="font-semibold tabular-nums text-gray-900">{Number(p.value || 0).toLocaleString('id-ID')}</span>
          </div>
        ))}
      </div>
      <div className="mt-2 pt-2 border-t border-gray-100 flex justify-between text-xs">
        <span className="text-gray-500">Total qty</span>
        <span className="font-semibold tabular-nums text-gray-900">{total.toLocaleString('id-ID')}</span>
      </div>
    </div>
  );
}

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

  const chartData = useMemo(() => {
    const byDate = new Map<string, { date: string; masuk: number; keluar: number; adjust: number }>();
    for (const c of detail.data?.chart || []) {
      const date = (c.date || '').slice(0, 10);
      if (!date) continue;
      if (!byDate.has(date)) byDate.set(date, { date, masuk: 0, keluar: 0, adjust: 0 });
      const row = byDate.get(date)!;
      const qty = Math.abs(Number(c.qty) || 0);
      if (c.type === 'MASUK') row.masuk += qty;
      else if (c.type === 'KELUAR') row.keluar += qty;
      else if (c.type === 'ADJUST') row.adjust += qty;
    }
    return Array.from(byDate.values()).sort((a, b) => a.date.localeCompare(b.date));
  }, [detail.data?.chart]);

  const chartTotals = useMemo(() => {
    return chartData.reduce(
      (acc, row) => ({
        masuk: acc.masuk + row.masuk,
        keluar: acc.keluar + row.keluar,
        adjust: acc.adjust + row.adjust,
      }),
      { masuk: 0, keluar: 0, adjust: 0 },
    );
  }, [chartData]);

  if (detail.isError) return <ErrorState onRetry={() => detail.refetch()} />;
  if (detail.isLoading || !detail.data) return <LoadingState />;

  const d = detail.data;

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
        <div className="flex flex-wrap items-end justify-between gap-4 mb-5">
          <div>
            <h2 className="text-lg font-semibold text-gray-800">Riwayat Pergerakan</h2>
            <p className="text-xs text-gray-500 mt-1">Qty harian · Masuk / Keluar / Adjust (agregat per tanggal)</p>
          </div>
          {chartData.length > 0 && (
            <div className="flex flex-wrap gap-4 text-xs">
              {(Object.keys(SERIES) as Array<keyof typeof SERIES>).map((k) => (
                <div key={k} className="text-right">
                  <p className="text-gray-400 uppercase tracking-wide">{SERIES[k].label}</p>
                  <p className="font-semibold tabular-nums text-gray-800" style={{ color: SERIES[k].color }}>
                    {chartTotals[k].toLocaleString('id-ID')}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
        {chartData.length === 0 ? (
          <EmptyState message="Belum ada pergerakan stok." />
        ) : (
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={chartData}
                margin={{ top: 8, right: 8, left: 0, bottom: 4 }}
                barCategoryGap="28%"
                barGap={4}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#e8eef0" vertical={false} />
                <XAxis
                  dataKey="date"
                  tickFormatter={formatAxisDate}
                  tick={{ fontSize: 11, fill: '#6b7280' }}
                  axisLine={{ stroke: '#e5e7eb' }}
                  tickLine={false}
                  dy={6}
                />
                <YAxis
                  tick={{ fontSize: 11, fill: '#6b7280' }}
                  axisLine={false}
                  tickLine={false}
                  width={40}
                  allowDecimals={false}
                  label={{
                    value: 'Qty',
                    angle: -90,
                    position: 'insideLeft',
                    offset: 8,
                    style: { fill: '#9ca3af', fontSize: 11 },
                  }}
                />
                <Tooltip
                  cursor={{ fill: 'rgba(6, 83, 102, 0.06)' }}
                  content={<MovementTooltip />}
                />
                <Legend
                  verticalAlign="bottom"
                  height={32}
                  iconType="square"
                  iconSize={10}
                  wrapperStyle={{ fontSize: 12, color: '#4b5563', paddingTop: 8 }}
                />
                <Bar
                  dataKey="masuk"
                  name={SERIES.masuk.label}
                  fill={SERIES.masuk.color}
                  radius={[4, 4, 0, 0]}
                  maxBarSize={36}
                />
                <Bar
                  dataKey="keluar"
                  name={SERIES.keluar.label}
                  fill={SERIES.keluar.color}
                  radius={[4, 4, 0, 0]}
                  maxBarSize={36}
                />
                <Bar
                  dataKey="adjust"
                  name={SERIES.adjust.label}
                  fill={SERIES.adjust.color}
                  radius={[4, 4, 0, 0]}
                  maxBarSize={36}
                />
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
