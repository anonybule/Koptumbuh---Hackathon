'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../../lib/api';
import { formatRp, formatDate } from '../../../lib/format';
import { Card, ErrorState, LoadingState, EmptyState, Tabs, Badge } from '../../../components/ui';
import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  BarChart, Bar, PieChart, Pie, Cell,
} from 'recharts';
import { Sparkles, RefreshCw, ArrowRight } from 'lucide-react';

interface SalePoint { date: string; revenue: number; count: number }
interface TopProduct { name: string; qty: number; revenue: number }
interface MarginRow {
  name: string; buy: number; sell: number; margin: number; margin_pct: number; profit: number;
}
interface InsightAction {
  priority: string; title: string; detail: string; href: string;
}
interface InsightPayload {
  metrics: Record<string, any>;
  insight: {
    headline: string;
    summary: string;
    actions: InsightAction[];
    risks: string[];
    source?: string;
  };
}

const COLORS = ['#065366', '#a0ba3b', '#0a6b80', '#7a9430', '#3d8a9a', '#c4d46a'];

function priorityTone(p: string): 'red' | 'yellow' | 'blue' | 'gray' {
  const u = (p || '').toUpperCase();
  if (u === 'HIGH') return 'red';
  if (u === 'MED') return 'yellow';
  if (u === 'LOW') return 'blue';
  return 'gray';
}

function reconTone(s: string): 'green' | 'red' | 'yellow' | 'gray' {
  if (s === 'MATCH') return 'green';
  if (s === 'MISMATCH') return 'red';
  if (s === 'SNAPSHOT_MISSING') return 'yellow';
  return 'gray';
}

export default function AnalyticsPage() {
  const [tab, setTab] = useState('omzet');

  const insights = useQuery({
    queryKey: ['analytics-insights'],
    queryFn: async () => (await apiClient<InsightPayload>('/admin/analytics/insights')).data!,
  });

  const sales = useQuery({
    queryKey: ['analytics-sales'],
    queryFn: async () => (await apiClient<SalePoint[]>('/admin/dashboard/sales')).data || [],
    enabled: tab === 'omzet',
  });
  const top = useQuery({
    queryKey: ['analytics-top'],
    queryFn: async () => (await apiClient<TopProduct[]>('/admin/dashboard/top-products')).data || [],
    enabled: tab === 'omzet',
  });
  const payment = useQuery({
    queryKey: ['analytics-payment'],
    queryFn: async () => (await apiClient<any[]>('/admin/analytics/payment-mix')).data || [],
    enabled: tab === 'omzet',
  });
  const margin = useQuery({
    queryKey: ['analytics-margin'],
    queryFn: async () => (await apiClient<MarginRow[]>('/admin/dashboard/margin')).data || [],
    enabled: tab === 'margin',
  });
  const slow = useQuery({
    queryKey: ['analytics-slow'],
    queryFn: async () => (await apiClient<any[]>('/admin/dashboard/slow-moving')).data || [],
    enabled: tab === 'stok' || tab === 'margin',
  });
  const recon = useQuery({
    queryKey: ['analytics-recon'],
    queryFn: async () => (await apiClient<any[]>('/admin/dashboard/stock-reconciliation')).data || [],
    enabled: tab === 'stok',
  });
  const members = useQuery({
    queryKey: ['analytics-members'],
    queryFn: async () => (await apiClient<any[]>('/admin/dashboard/active-members')).data || [],
    enabled: tab === 'anggota',
  });
  const segments = useQuery({
    queryKey: ['analytics-seg'],
    queryFn: async () => (await apiClient<any[]>('/admin/dashboard/segmentation')).data || [],
    enabled: tab === 'anggota',
  });
  const prices = useQuery({
    queryKey: ['analytics-price'],
    queryFn: async () => (await apiClient<any[]>('/admin/price-comparison')).data || [],
    enabled: tab === 'harga',
  });
  const shu = useQuery({
    queryKey: ['analytics-shu'],
    queryFn: async () => (await apiClient<any[]>('/admin/shu/monthly')).data || [],
    enabled: tab === 'shu',
  });
  const shuSummary = useQuery({
    queryKey: ['analytics-shu-summary'],
    queryFn: async () => (await apiClient<any>('/admin/shu/summary')).data,
    enabled: tab === 'shu',
  });

  const salesChart = [...(sales.data || [])].reverse();
  const marginTop = (margin.data || []).slice(0, 10);
  const pieData = (top.data || []).slice(0, 6).map((p) => ({ name: p.name, value: p.revenue }));
  const insight = insights.data?.insight;
  const m = insights.data?.metrics;

  return (
    <div>
      <div className="flex flex-wrap items-start justify-between gap-3 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Analytics</h1>
          <p className="text-sm text-gray-500 mt-1">
            Business intelligence: omzet, margin, stok, anggota, harga, SHU + AI insight.
          </p>
        </div>
        <button
          type="button"
          onClick={() => insights.refetch()}
          className="inline-flex items-center gap-2 px-3 py-2 border rounded-lg text-sm hover:bg-gray-50"
        >
          <RefreshCw size={14} className={insights.isFetching ? 'animate-spin' : ''} />
          Refresh insight
        </button>
      </div>

      {/* AI Insight panel */}
      <Card className="p-5 mb-6 border-l-4 border-l-primary bg-gradient-to-r from-[#06536608] to-transparent">
        <div className="flex items-center gap-2 mb-2">
          <Sparkles size={18} className="text-primary" />
          <h2 className="font-semibold text-gray-800">AI Analytics</h2>
          {insight?.source && (
            <Badge tone={insight.source === 'gemini' ? 'green' : 'gray'}>
              {insight.source === 'gemini' ? 'Gemini' : 'Rules'}
            </Badge>
          )}
        </div>
        {insights.isError ? (
          <ErrorState onRetry={() => insights.refetch()} />
        ) : insights.isLoading ? (
          <LoadingState label="Menyusun insight..." />
        ) : (
          <>
            <p className="text-lg font-semibold text-gray-800">{insight?.headline}</p>
            <p className="text-sm text-gray-600 mt-1 mb-4">{insight?.summary}</p>

            {m && (
              <div className="grid grid-cols-2 md:grid-cols-5 gap-2 mb-4">
                {[
                  ['Omzet hari ini', formatRp(m.omzet_hari_ini || 0)],
                  ['TX hari ini', String(m.tx_hari_ini || 0)],
                  ['Stok menipis', String(m.stok_menipis || 0)],
                  ['Anggota risiko', String(m.anggota_risiko || 0)],
                  ['SHU YTD', formatRp(m.shu_bersih_ytd || 0)],
                ].map(([label, val]) => (
                  <div key={label} className="bg-white/80 rounded-lg border border-gray-100 px-3 py-2">
                    <p className="text-[11px] text-gray-500">{label}</p>
                    <p className="text-sm font-bold text-gray-800">{val}</p>
                  </div>
                ))}
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3">
              {(insight?.actions || []).map((a, i) => (
                <Link
                  key={i}
                  href={a.href || '/'}
                  className="block p-3 rounded-lg border border-gray-100 bg-white hover:border-primary/40 transition"
                >
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <Badge tone={priorityTone(a.priority)}>{a.priority}</Badge>
                    <ArrowRight size={14} className="text-gray-400" />
                  </div>
                  <p className="text-sm font-semibold text-gray-800">{a.title}</p>
                  <p className="text-xs text-gray-500 mt-1">{a.detail}</p>
                </Link>
              ))}
            </div>

            {(insight?.risks || []).length > 0 && (
              <ul className="text-xs text-gray-500 space-y-1 list-disc pl-4">
                {insight!.risks.map((r, i) => (
                  <li key={i}>{r}</li>
                ))}
              </ul>
            )}
          </>
        )}
      </Card>

      <Tabs
        tabs={[
          { id: 'omzet', label: 'Omzet' },
          { id: 'margin', label: 'Margin' },
          { id: 'stok', label: 'Stok' },
          { id: 'anggota', label: 'Anggota' },
          { id: 'harga', label: 'Harga' },
          { id: 'shu', label: 'SHU' },
        ]}
        active={tab}
        onChange={setTab}
      />

      {tab === 'omzet' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card className="p-6">
              <h2 className="text-lg font-semibold mb-4">Omzet Harian</h2>
              {sales.isError ? <ErrorState onRetry={() => sales.refetch()} /> :
               sales.isLoading ? <LoadingState /> : salesChart.length === 0 ? (
                <EmptyState message="Belum ada omzet. Jalankan POS Demo atau pastikan seed transaksi terpasang." />
              ) : (
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
                <EmptyState message="Belum ada data." />
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

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
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

            <Card className="overflow-hidden">
              <div className="p-4 border-b font-semibold">Metode Pembayaran</div>
              {payment.isLoading ? <LoadingState /> : (payment.data || []).length === 0 ? (
                <EmptyState message="Belum ada data pembayaran." />
              ) : (
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 border-b"><tr>
                    <th className="text-left p-3">Metode</th>
                    <th className="text-right p-3">TX</th>
                    <th className="text-right p-3">Total</th>
                  </tr></thead>
                  <tbody>
                    {(payment.data || []).map((r: any, i: number) => (
                      <tr key={i} className="border-b last:border-0">
                        <td className="p-3 font-medium">{r.metode}</td>
                        <td className="p-3 text-right">{r.jumlah}</td>
                        <td className="p-3 text-right">{formatRp(r.total)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </Card>
          </div>
        </div>
      )}

      {tab === 'margin' && (
        <div className="space-y-6">
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

          <Card className="overflow-hidden">
            <div className="p-4 border-b"><h2 className="text-lg font-semibold">Detail Margin Produk</h2></div>
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
                    {(margin.data || []).map((row, i) => (
                      <tr key={i} className="border-b last:border-0 hover:bg-gray-50">
                        <td className="p-3 font-medium">{row.name}</td>
                        <td className="p-3 text-right">{formatRp(row.buy)}</td>
                        <td className="p-3 text-right">{formatRp(row.sell)}</td>
                        <td className="p-3 text-right">{formatRp(row.margin)}</td>
                        <td className="p-3 text-right">{row.margin_pct?.toFixed(1)}%</td>
                        <td className="p-3 text-right font-semibold">{formatRp(row.profit)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>

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
        </div>
      )}

      {tab === 'stok' && (
        <div className="space-y-6">
          <Card className="overflow-hidden">
            <div className="p-4 border-b font-semibold">Rekonsiliasi Stok</div>
            {recon.isLoading ? <LoadingState /> : recon.isError ? (
              <ErrorState onRetry={() => recon.refetch()} />
            ) : (recon.data || []).length === 0 ? (
              <EmptyState message="Belum ada data rekonsiliasi." />
            ) : (
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b"><tr>
                  <th className="text-left p-3">Produk</th>
                  <th className="text-right p-3">Terhitung</th>
                  <th className="text-right p-3">Snapshot</th>
                  <th className="text-right p-3">Selisih</th>
                  <th className="text-left p-3">Status</th>
                </tr></thead>
                <tbody>
                  {(recon.data || []).slice(0, 30).map((r: any, i: number) => (
                    <tr key={i} className="border-b last:border-0">
                      <td className="p-3 font-medium">{r.nama_produk}</td>
                      <td className="p-3 text-right">{r.stok_terhitung}</td>
                      <td className="p-3 text-right">{r.stok_snapshot ?? '—'}</td>
                      <td className="p-3 text-right">{r.selisih}</td>
                      <td className="p-3"><Badge tone={reconTone(r.status)}>{r.status}</Badge></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Card>

          <Card className="overflow-hidden">
            <div className="p-4 border-b font-semibold flex justify-between">
              <span>Produk Lambat Bergerak</span>
              <Link href="/inventory" className="text-xs text-primary hover:underline">Inventaris →</Link>
            </div>
            {slow.isLoading ? <LoadingState /> : (
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b"><tr>
                  <th className="text-left p-3">Produk</th>
                  <th className="text-right p-3">Stok</th>
                  <th className="text-right p-3">Hari idle</th>
                </tr></thead>
                <tbody>
                  {(slow.data || []).slice(0, 20).map((r: any, i: number) => (
                    <tr key={i} className="border-b">
                      <td className="p-3">{r.nama_produk}</td>
                      <td className="p-3 text-right">{r.stok}</td>
                      <td className="p-3 text-right text-red-600 font-medium">{r.hari_tanpa_penjualan}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Card>
        </div>
      )}

      {tab === 'anggota' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card className="overflow-hidden">
            <div className="p-4 border-b font-semibold">Anggota Aktif (ranking belanja)</div>
            {members.isLoading ? <LoadingState /> : (
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b"><tr>
                  <th className="text-left p-3">Nama</th>
                  <th className="text-right p-3">TX</th>
                  <th className="text-right p-3">Total</th>
                  <th className="text-left p-3">Status</th>
                </tr></thead>
                <tbody>
                  {(members.data || []).map((r: any, i: number) => (
                    <tr key={i} className="border-b last:border-0">
                      <td className="p-3 font-medium">{r.name}</td>
                      <td className="p-3 text-right">{r.tx_count}</td>
                      <td className="p-3 text-right">{formatRp(r.total)}</td>
                      <td className="p-3"><Badge>{r.status}</Badge></td>
                    </tr>
                  ))}
                  {(members.data || []).length === 0 && (
                    <tr><td colSpan={4} className="p-6 text-center text-gray-400">Belum ada data.</td></tr>
                  )}
                </tbody>
              </table>
            )}
          </Card>

          <Card className="overflow-hidden">
            <div className="p-4 border-b font-semibold flex items-center justify-between gap-2">
              <span>Segmentasi RFM</span>
              <Link href="/customer-relationship" className="text-xs text-primary hover:underline font-normal">
                Customer Relationship →
              </Link>
            </div>
            {segments.isLoading ? <LoadingState /> : (
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b"><tr>
                  <th className="text-left p-3">Anggota</th>
                  <th className="text-left p-3">Tier</th>
                  <th className="text-right p-3">Moneter</th>
                </tr></thead>
                <tbody>
                  {(segments.data || []).slice(0, 20).map((r: any, i: number) => (
                    <tr key={i} className="border-b">
                      <td className="p-3">{r.nama}</td>
                      <td className="p-3"><Badge>{r.segmentasi}</Badge></td>
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
      )}

      {tab === 'harga' && (
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
                {(prices.data || []).slice(0, 30).map((r: any, i: number) => (
                  <tr key={i} className="border-b">
                    <td className="p-3">{r.nama_produk || r.name}</td>
                    <td className="p-3 text-right">{formatRp(r.harga_kita || r.our_price || 0)}</td>
                    <td className="p-3 text-right">{formatRp(r.harga_pasar_rata || r.market_avg || 0)}</td>
                    <td className="p-3">
                      <Badge tone={
                        (r.status_harga || r.status) === 'TERMURAH' ? 'green' :
                        (r.status_harga || r.status) === 'LEBIH_MAHAL' ? 'red' : 'gray'
                      }>
                        {r.status_harga || r.status || '—'}
                      </Badge>
                    </td>
                  </tr>
                ))}
                {(prices.data || []).length === 0 && (
                  <tr><td colSpan={4} className="p-8 text-center text-gray-400">Belum ada data harga pasar.</td></tr>
                )}
              </tbody>
            </table>
          )}
        </Card>
      )}

      {tab === 'shu' && (
        <div className="space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex flex-wrap gap-3">
              <Card className="px-4 py-3">
                <p className="text-xs text-gray-500">SHU bersih YTD</p>
                <p className="text-lg font-bold text-primary">{formatRp(shuSummary.data?.shu_bersih || 0)}</p>
              </Card>
              <Card className="px-4 py-3">
                <p className="text-xs text-gray-500">Hasil</p>
                <div className="mt-1">
                  <Badge tone={shuSummary.data?.hasil === 'PROFIT' ? 'green' : 'red'}>
                    {shuSummary.data?.hasil || '—'}
                  </Badge>
                </div>
              </Card>
              <Card className="px-4 py-3">
                <p className="text-xs text-gray-500">Margin SHU</p>
                <p className="text-lg font-bold">{shuSummary.data?.margin_shu_pct ?? 0}%</p>
              </Card>
            </div>
            <Link href="/shu" className="text-sm text-primary hover:underline">Halaman SHU lengkap →</Link>
          </div>

          <Card className="p-6">
            <h2 className="text-lg font-semibold mb-4">Estimasi SHU bulanan</h2>
            {shu.isLoading ? <LoadingState /> : (shu.data || []).length === 0 ? (
              <EmptyState message="Belum ada data SHU bulanan." />
            ) : (
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={[...(shu.data || [])].reverse()}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis dataKey="bulan" tick={{ fontSize: 11 }} tickFormatter={(v) => String(v).slice(0, 7)} />
                    <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} />
                    <Tooltip formatter={(v: number) => formatRp(v)} />
                    <Bar dataKey="estimasi_shu" fill="#065366" name="SHU" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="total_omzet" fill="#a0ba3b55" name="Omzet" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </Card>

          <Card className="overflow-hidden">
            <div className="p-4 border-b font-semibold">Detail bulanan</div>
            {shu.isLoading ? <LoadingState /> : (
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b"><tr>
                  <th className="text-left p-3">Bulan</th>
                  <th className="text-right p-3">Omzet</th>
                  <th className="text-right p-3">HPP</th>
                  <th className="text-right p-3">TX</th>
                  <th className="text-right p-3">Estimasi SHU</th>
                </tr></thead>
                <tbody>
                  {(shu.data || []).map((r: any, i: number) => (
                    <tr key={i} className="border-b last:border-0">
                      <td className="p-3">{formatDate(r.bulan)}</td>
                      <td className="p-3 text-right">{formatRp(r.total_omzet)}</td>
                      <td className="p-3 text-right">{formatRp(r.hpp || 0)}</td>
                      <td className="p-3 text-right">{r.jumlah_transaksi}</td>
                      <td className="p-3 text-right font-semibold">{formatRp(r.estimasi_shu)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Card>
        </div>
      )}
    </div>
  );
}
