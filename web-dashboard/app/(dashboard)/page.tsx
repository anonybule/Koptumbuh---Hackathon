'use client';

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../lib/api';
import { formatRp } from '../../lib/format';
import { Card, ErrorState, LoadingState, Badge } from '../../components/ui';
import {
  TrendingUp, ShoppingCart, AlertTriangle, Users, Lightbulb, RefreshCw,
  MessageSquare, Package, Bot, ArrowRight,
} from 'lucide-react';
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
interface PipelineStage {
  id: string;
  label: string;
  count: number;
  href: string;
  tone: string;
}

function stageTone(tone: string): 'green' | 'yellow' | 'red' | 'blue' | 'gray' {
  if (tone === 'green' || tone === 'yellow' || tone === 'red' || tone === 'blue') return tone;
  return 'gray';
}

export default function DashboardPage() {
  const kpi = useQuery({
    queryKey: ['kpi'],
    queryFn: async () => (await apiClient<KpiData>('/admin/dashboard/kpi')).data!,
    refetchOnWindowFocus: true,
  });
  const pipeline = useQuery({
    queryKey: ['ops-pipeline'],
    queryFn: async () => (await apiClient<{ stages: PipelineStage[] }>('/admin/ops/pipeline')).data!,
    refetchInterval: 20000,
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

  const refreshAll = () => {
    kpi.refetch();
    pipeline.refetch();
    sales.refetch();
    top.refetch();
    tx.refetch();
    recs.refetch();
  };

  if (error) {
    return <ErrorState onRetry={refreshAll} />;
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Dashboard</h1>
          <p className="text-xs text-gray-400 mt-1">
            Loop operasional: WhatsApp → YA → stok → restock/PO → notifikasi.
          </p>
          <p className="inline-flex mt-2 text-xs font-medium text-emerald-800 bg-emerald-50 border border-emerald-100 rounded-full px-2.5 py-1">
            No AI Math — harga &amp; total selalu dari database
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link
            href="/automations"
            className="hidden sm:inline-flex items-center gap-1.5 px-3 py-2 text-sm border rounded-lg hover:bg-gray-50"
          >
            <Bot size={14} /> Automasi
          </Link>
          <Link
            href="/pos"
            className="hidden sm:inline-flex px-3 py-2 text-sm border rounded-lg hover:bg-gray-50 text-primary font-medium"
          >
            POS demo
          </Link>
          <button
            onClick={refreshAll}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-2 text-sm border rounded-lg hover:bg-gray-50 disabled:opacity-50"
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>
      </div>

      <Card className="p-4 mb-6">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-gray-800">Pipeline operasional</h2>
          <Link href="/transactions?tab=inbox" className="text-xs text-primary hover:underline inline-flex items-center gap-1">
            Inbox WA <ArrowRight size={12} />
          </Link>
        </div>
        {pipeline.isLoading ? (
          <LoadingState />
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-8 gap-2">
            {(pipeline.data?.stages || []).map((s) => (
              <Link
                key={s.id}
                href={s.href}
                className="rounded-lg border border-gray-100 bg-gray-50/80 hover:border-primary/40 hover:bg-primary/5 p-3 transition"
              >
                <p className="text-[11px] text-gray-500 leading-tight mb-1">{s.label}</p>
                <div className="flex items-center justify-between gap-1">
                  <p className="text-xl font-bold text-gray-800">{s.count}</p>
                  <Badge tone={stageTone(s.tone)}>{s.count > 0 ? 'live' : '—'}</Badge>
                </div>
              </Link>
            ))}
          </div>
        )}
      </Card>

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
            { label: 'Inbox WA', href: '/transactions?tab=inbox', desc: 'Draft & YA', icon: MessageSquare },
            { label: 'POS Kasir', href: '/pos', desc: 'Kasir di tempat', icon: ShoppingCart },
            { label: 'Supply / PO', href: '/supply', desc: 'Restock otomatis', icon: Package },
            { label: 'ChatHub', href: '/chathub', desc: 'WhatsApp live', icon: MessageSquare },
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
