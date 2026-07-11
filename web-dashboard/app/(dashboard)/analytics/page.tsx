'use client';

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../../lib/api';
import { formatRp } from '../../../lib/format';
import { Card, ErrorState, LoadingState } from '../../../components/ui';
import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  BarChart, Bar, PieChart, Pie, Cell,
} from 'recharts';

interface SalePoint { date: string; revenue: number; count: number }
interface TopProduct { name: string; qty: number; revenue: number }
interface MarginRow {
  name: string; buy: number; sell: number; margin: number; margin_pct: number; profit: number;
}

const COLORS = ['#065366', '#a0ba3b', '#0a6b80', '#7a9430', '#3d8a9a', '#c4d46a'];

export default function AnalyticsPage() {
  const sales = useQuery({
    queryKey: ['analytics-sales'],
    queryFn: async () => (await apiClient<SalePoint[]>('/admin/dashboard/sales')).data || [],
  });
  const top = useQuery({
    queryKey: ['analytics-top'],
    queryFn: async () => (await apiClient<TopProduct[]>('/admin/dashboard/top-products')).data || [],
  });
  const margin = useQuery({
    queryKey: ['analytics-margin'],
    queryFn: async () => (await apiClient<MarginRow[]>('/admin/dashboard/margin')).data || [],
  });
  const slow = useQuery({
    queryKey: ['analytics-slow'],
    queryFn: async () => (await apiClient<any[]>('/admin/dashboard/slow-moving')).data || [],
  });
  const segments = useQuery({
    queryKey: ['analytics-seg'],
    queryFn: async () => (await apiClient<any[]>('/admin/dashboard/segmentation')).data || [],
  });
  const prices = useQuery({
    queryKey: ['analytics-price'],
    queryFn: async () => (await apiClient<any[]>('/admin/price-comparison')).data || [],
  });

  const error = sales.isError || top.isError || margin.isError;
  if (error) {
    return <ErrorState onRetry={() => { sales.refetch(); top.refetch(); margin.refetch(); }} />;
  }

  const salesChart = [...(sales.data || [])].reverse();
  const marginTop = (margin.data || []).slice(0, 10);
  const pieData = (top.data || []).slice(0, 6).map((p) => ({ name: p.name, value: p.revenue }));

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-800 mb-6">Analytics</h1>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <Card className="p-6">
          <h2 className="text-lg font-semibold mb-4">Omzet Harian</h2>
          {sales.isLoading ? <LoadingState /> : (
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={salesChart}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="date" tick={{ fontSize: 11 }} tickFormatter={(v) => String(v).slice(5)} />
                  <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} />
                  <Tooltip formatter={(v: number) => formatRp(v)} />
                  <Area type="monotone" dataKey="revenue" stroke="#065366" fill="#06536633" name="Omzet" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}
        </Card>

        <Card className="p-6">
          <h2 className="text-lg font-semibold mb-4">Kontribusi Produk Terlaris</h2>
          {top.isLoading ? <LoadingState /> : pieData.length === 0 ? (
            <p className="text-sm text-gray-400 py-8 text-center">Belum ada data.</p>
          ) : (
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={90} label={({ name }) => String(name).slice(0, 12)}>
                    {pieData.map((_, i) => (
                      <Cell key={i} fill={COLORS[i % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v: number) => formatRp(v)} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          )}
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <Card className="p-6">
          <h2 className="text-lg font-semibold mb-4">Qty Produk Terlaris</h2>
          {top.isLoading ? <LoadingState /> : (
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={top.data || []}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="name" tick={{ fontSize: 10 }} interval={0} angle={-25} textAnchor="end" height={70} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Bar dataKey="qty" fill="#a0ba3b" name="Qty" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </Card>

        <Card className="p-6">
          <h2 className="text-lg font-semibold mb-4">Margin Profit (Top 10)</h2>
          {margin.isLoading ? <LoadingState /> : (
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={marginTop}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="name" tick={{ fontSize: 10 }} interval={0} angle={-25} textAnchor="end" height={70} />
                  <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} />
                  <Tooltip formatter={(v: number) => formatRp(v)} />
                  <Bar dataKey="profit" fill="#065366" name="Profit" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </Card>
      </div>

      <Card className="overflow-hidden mb-6">
        <div className="p-4 border-b">
          <h2 className="text-lg font-semibold">Detail Margin Produk</h2>
        </div>
        {margin.isLoading ? <LoadingState /> : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="text-left p-3 font-medium">Produk</th>
                  <th className="text-right p-3 font-medium">Beli</th>
                  <th className="text-right p-3 font-medium">Jual</th>
                  <th className="text-right p-3 font-medium">Margin</th>
                  <th className="text-right p-3 font-medium">Margin %</th>
                  <th className="text-right p-3 font-medium">Profit</th>
                </tr>
              </thead>
              <tbody>
                {(margin.data || []).map((m, i) => (
                  <tr key={i} className="border-b last:border-0 hover:bg-gray-50">
                    <td className="p-3 font-medium">{m.name}</td>
                    <td className="p-3 text-right">{formatRp(m.buy)}</td>
                    <td className="p-3 text-right">{formatRp(m.sell)}</td>
                    <td className="p-3 text-right">{formatRp(m.margin)}</td>
                    <td className="p-3 text-right">{m.margin_pct?.toFixed(1)}%</td>
                    <td className="p-3 text-right font-semibold">{formatRp(m.profit)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <Card className="overflow-hidden">
          <div className="p-4 border-b font-semibold">Produk Lambat Bergerak</div>
          {slow.isLoading ? <LoadingState /> : (
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b"><tr>
                <th className="text-left p-3">Produk</th>
                <th className="text-right p-3">Stok</th>
                <th className="text-right p-3">Hari idle</th>
              </tr></thead>
              <tbody>
                {(slow.data || []).slice(0, 15).map((r: any, i: number) => (
                  <tr key={i} className="border-b">
                    <td className="p-3">{r.nama_produk}</td>
                    <td className="p-3 text-right">{r.stok}</td>
                    <td className="p-3 text-right text-red-600 font-medium">{r.hari_tanpa_penjualan}</td>
                  </tr>
                ))}
                {(slow.data || []).length === 0 && (
                  <tr><td colSpan={3} className="p-6 text-center text-gray-400">Tidak ada produk lambat.</td></tr>
                )}
              </tbody>
            </table>
          )}
        </Card>

        <Card className="overflow-hidden">
          <div className="p-4 border-b font-semibold">Segmentasi RFM</div>
          {segments.isLoading ? <LoadingState /> : (
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b"><tr>
                <th className="text-left p-3">Anggota</th>
                <th className="text-left p-3">Tier</th>
                <th className="text-right p-3">Moneter</th>
              </tr></thead>
              <tbody>
                {(segments.data || []).slice(0, 15).map((r: any, i: number) => (
                  <tr key={i} className="border-b">
                    <td className="p-3">{r.nama}</td>
                    <td className="p-3"><span className="text-xs px-2 py-0.5 bg-gray-100 rounded-full">{r.segmentasi}</span></td>
                    <td className="p-3 text-right">{formatRp(r.moneter || 0)}</td>
                  </tr>
                ))}
                {(segments.data || []).length === 0 && (
                  <tr><td colSpan={3} className="p-6 text-center text-gray-400">Belum ada segmentasi.</td></tr>
                )}
              </tbody>
            </table>
          )}
        </Card>
      </div>

      <Card className="overflow-hidden">
        <div className="p-4 border-b font-semibold">Perbandingan Harga Pasar</div>
        {prices.isLoading ? <LoadingState /> : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b"><tr>
              <th className="text-left p-3">Produk</th>
              <th className="text-right p-3">Harga kita</th>
              <th className="text-right p-3">Pasar</th>
              <th className="text-left p-3">Status</th>
            </tr></thead>
            <tbody>
              {(prices.data || []).slice(0, 20).map((r: any, i: number) => (
                <tr key={i} className="border-b">
                  <td className="p-3">{r.nama_produk || r.name}</td>
                  <td className="p-3 text-right">{formatRp(r.harga_kita || r.our_price || 0)}</td>
                  <td className="p-3 text-right">{formatRp(r.harga_pasar_rata || r.market_avg || 0)}</td>
                  <td className="p-3"><span className="text-xs px-2 py-0.5 bg-gray-100 rounded-full">{r.status_harga || r.status || '—'}</span></td>
                </tr>
              ))}
              {(prices.data || []).length === 0 && (
                <tr><td colSpan={4} className="p-6 text-center text-gray-400">Belum ada data harga pasar.</td></tr>
              )}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
