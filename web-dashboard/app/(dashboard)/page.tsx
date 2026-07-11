'use client';

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../lib/api';
import { formatRp } from '../../lib/format';
import { Card, ErrorState, LoadingState, Badge } from '../../components/ui';
import { TrendingUp, ShoppingCart, AlertTriangle, Users, Lightbulb, RefreshCw } from 'lucide-react';
import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  BarChart, Bar,
} from 'recharts';
import Link from 'next/link';

interface KpiData {
  total_revenue: number;
  total_transactions: number;
  low_stock: number;
  total_members: number;
}

interface SalePoint { date: string; revenue: number; count: number }
interface TopProduct { name: string; qty: number; revenue: number }
interface Transaction { id: string; customer: string; total: number; status: string; method: string; date: string }
interface Recommendation { id: string; jenis: string; judul: string; isi: string; priority: string; status: string }

export default function DashboardPage() {
  const kpi = useQuery({
    queryKey: ['kpi'],
    queryFn: async () => (await apiClient<KpiData>('/admin/dashboard/kpi')).data!,
    refetchOnWindowFocus: true,
  });
  const sales = useQuery({
    queryKey: ['sales'],
    queryFn: async () => (await apiClient<SalePoint[]>('/admin/dashboard/sales')).data || [],
    refetchOnWindowFocus: true,
  });
  const top = useQuery({
    queryKey: ['top-products'],
    queryFn: async () => (await apiClient<TopProduct[]>('/admin/dashboard/top-products')).data || [],
  });
  const tx = useQuery({
    queryKey: ['transactions-preview'],
    queryFn: async () => ((await apiClient<Transaction[]>('/admin/transactions')).data || []).slice(0, 8),
    refetchOnWindowFocus: true,
  });
  const recs = useQuery({
    queryKey: ['recs-preview'],
    queryFn: async () => ((await apiClient<Recommendation[]>('/admin/recommendations')).data || []).slice(0, 5),
  });

  const loading = kpi.isLoading;
  const error = kpi.isError;

  const cards = [
    { label: 'Total Revenue', value: formatRp(kpi.data?.total_revenue), icon: TrendingUp, color: 'bg-green-500' },
    { label: 'Total Transaksi', value: `${kpi.data?.total_transactions || 0}`, icon: ShoppingCart, color: 'bg-blue-500' },
    { label: 'Low Stock', value: `${kpi.data?.low_stock || 0} produk`, icon: AlertTriangle, color: 'bg-yellow-500' },
    { label: 'Total Anggota', value: `${kpi.data?.total_members || 0}`, icon: Users, color: 'bg-purple-500' },
  ];

  const salesChart = [...(sales.data || [])].reverse();

  if (error) {
    return <ErrorState onRetry={() => { kpi.refetch(); sales.refetch(); top.refetch(); tx.refetch(); recs.refetch(); }} />;
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Dashboard</h1>
          <p className="text-xs text-gray-400 mt-1">Setelah POS/WhatsApp YA — klik Refresh (atau kembali ke tab ini).</p>
        </div>
        <div className="flex items-center gap-2">
          <Link
            href="/pos"
            className="hidden sm:inline-flex px-3 py-2 text-sm border rounded-lg hover:bg-gray-50 text-primary font-medium"
          >
            POS demo
          </Link>
          <button
            onClick={() => { kpi.refetch(); sales.refetch(); top.refetch(); tx.refetch(); recs.refetch(); }}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-2 text-sm border rounded-lg hover:bg-gray-50 disabled:opacity-50"
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {cards.map((card) => (
          <Card key={card.label} className="p-5">
            <div className="flex items-center gap-3">
              <div className={`${card.color} p-3 rounded-lg text-white`}>
                <card.icon size={20} />
              </div>
              <div>
                <p className="text-sm text-gray-500">{card.label}</p>
                <p className="text-xl font-bold text-gray-800">{loading ? '…' : card.value}</p>
              </div>
            </div>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <Card className="p-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">Tren Penjualan (30 hari)</h2>
          {sales.isLoading ? <LoadingState /> : salesChart.length === 0 ? (
            <p className="text-sm text-gray-400">Belum ada data penjualan.</p>
          ) : (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={salesChart}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="date" tick={{ fontSize: 11 }} tickFormatter={(v) => String(v).slice(5)} />
                  <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} />
                  <Tooltip formatter={(v: number) => formatRp(v)} labelFormatter={(l) => `Tanggal: ${l}`} />
                  <Area type="monotone" dataKey="revenue" stroke="#065366" fill="#06536633" name="Omzet" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}
        </Card>

        <Card className="p-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">Produk Terlaris</h2>
          {top.isLoading ? <LoadingState /> : (top.data || []).length === 0 ? (
            <p className="text-sm text-gray-400">Belum ada data produk.</p>
          ) : (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={top.data} layout="vertical" margin={{ left: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis type="number" tick={{ fontSize: 11 }} />
                  <YAxis type="category" dataKey="name" width={100} tick={{ fontSize: 10 }} />
                  <Tooltip />
                  <Bar dataKey="qty" fill="#a0ba3b" name="Qty" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <Card className="p-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">Transaksi Terbaru</h2>
          {tx.isLoading ? <LoadingState /> : (tx.data || []).length === 0 ? (
            <p className="text-sm text-gray-400">Belum ada transaksi. Catat via WhatsApp lalu balas YA.</p>
          ) : (
            <div className="space-y-3">
              {(tx.data || []).map((t) => (
                <div key={t.id} className="flex items-center justify-between border-b border-gray-50 pb-3 last:border-0">
                  <div>
                    <p className="text-sm font-medium text-gray-800">{t.customer || 'Umum'}</p>
                    <p className="text-xs text-gray-400">{t.id} · {t.method}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-semibold text-gray-800">{formatRp(t.total)}</p>
                    <p className="text-xs text-green-600">{t.status}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
          <Link href="/transactions" className="inline-block mt-4 text-sm text-primary font-medium hover:underline">
            Lihat semua →
          </Link>
        </Card>

        <Card className="p-6">
          <div className="flex items-center gap-2 mb-4">
            <Lightbulb size={18} className="text-yellow-500" />
            <h2 className="text-lg font-semibold text-gray-800">Rekomendasi</h2>
          </div>
          {recs.isLoading ? <LoadingState /> : (recs.data || []).length === 0 ? (
            <p className="text-sm text-gray-400">Tidak ada rekomendasi aktif.</p>
          ) : (
            <div className="space-y-3">
              {(recs.data || []).map((r) => (
                <div key={r.id} className="p-3 rounded-lg bg-gray-50 border border-gray-100">
                  <div className="flex items-center justify-between mb-1 gap-2">
                    <p className="text-sm font-medium text-gray-800">{r.judul}</p>
                    <Badge tone={r.priority === 'HIGH' || r.priority === 'CRITICAL' ? 'red' : r.priority === 'MEDIUM' ? 'yellow' : 'gray'}>
                      {r.priority}
                    </Badge>
                  </div>
                  <p className="text-xs text-gray-500">{r.isi}</p>
                </div>
              ))}
            </div>
          )}
          <Link href="/recommendations" className="inline-block mt-4 text-sm text-primary font-medium hover:underline">
            Lihat semua →
          </Link>
        </Card>
      </div>

      <Card className="p-6">
        <h2 className="text-lg font-semibold text-gray-800 mb-4">Aksi Cepat</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { label: 'POS Kasir', href: '/pos', desc: 'Kasir di tempat' },
            { label: 'Transaksi', href: '/transactions', desc: 'Riwayat penjualan' },
            { label: 'Inventaris', href: '/inventory', desc: 'Stok & gudang' },
            { label: 'Anggota', href: '/members', desc: 'Daftar anggota' },
          ].map((action) => (
            <Link
              key={action.href}
              href={action.href}
              className="p-4 border border-gray-200 rounded-lg text-center hover:border-primary hover:bg-primary/5 transition"
            >
              <p className="font-medium text-gray-800">{action.label}</p>
              <p className="text-xs text-gray-400 mt-1">{action.desc}</p>
            </Link>
          ))}
        </div>
      </Card>
    </div>
  );
}
