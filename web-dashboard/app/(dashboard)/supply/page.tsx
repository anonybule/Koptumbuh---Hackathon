'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../../lib/api';
import { formatRp, formatDate } from '../../../lib/format';
import { Card, ErrorState, LoadingState, Tabs, Badge, EmptyState } from '../../../components/ui';

interface Supplier {
  id: string;
  name: string;
  phone?: string;
  alamat?: string;
  lead_time: number;
  payment?: string;
  status_aktif?: boolean;
}

interface RestockItem {
  produk_sample_id: string;
  nama_produk: string;
  stock: number;
  ads: number;
  days_remaining: number | null;
  lead_time: number;
  suggested_qty: number;
  supplier?: string;
}

interface Purchase {
  barang_masuk_ref: string;
  nama_produk: string;
  qty: number;
  harga_beli: number;
  total: number;
  date?: string;
  status?: string;
  supplier?: string;
}

export default function SupplyPage() {
  const [tab, setTab] = useState('suppliers');

  const suppliers = useQuery({
    queryKey: ['suppliers'],
    queryFn: async () => (await apiClient<Supplier[]>('/admin/suppliers?active_only=false')).data || [],
    enabled: tab === 'suppliers',
  });

  const restock = useQuery({
    queryKey: ['restock-plan'],
    queryFn: async () => (await apiClient<RestockItem[]>('/admin/restock-plan')).data || [],
    enabled: tab === 'restock',
  });

  const purchases = useQuery({
    queryKey: ['purchase-history'],
    queryFn: async () => (await apiClient<Purchase[]>('/admin/purchase-history')).data || [],
    enabled: tab === 'history',
  });

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-800 mb-6">Supply</h1>
      <Tabs
        tabs={[
          { id: 'suppliers', label: 'Pemasok' },
          { id: 'restock', label: 'Rencana Restock' },
          { id: 'history', label: 'Riwayat Pembelian' },
        ]}
        active={tab}
        onChange={setTab}
      />

      {tab === 'suppliers' && (
        <Card className="overflow-hidden">
          {suppliers.isError ? (
            <ErrorState onRetry={() => suppliers.refetch()} />
          ) : suppliers.isLoading ? (
            <LoadingState />
          ) : (suppliers.data || []).length === 0 ? (
            <EmptyState message="Belum ada pemasok." />
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="text-left p-3 font-medium">Pemasok</th>
                  <th className="text-left p-3 font-medium">Kontak</th>
                  <th className="text-right p-3 font-medium">Lead Time</th>
                  <th className="text-left p-3 font-medium">Pembayaran</th>
                  <th className="text-left p-3 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {(suppliers.data || []).map((s) => (
                  <tr key={s.id} className="border-b last:border-0 hover:bg-gray-50">
                    <td className="p-3 font-medium">{s.name}</td>
                    <td className="p-3">{s.phone || '—'}</td>
                    <td className="p-3 text-right">{s.lead_time} hari</td>
                    <td className="p-3">{s.payment || '—'}</td>
                    <td className="p-3">
                      <Badge tone={s.status_aktif ? 'green' : 'gray'}>
                        {s.status_aktif ? 'Aktif' : 'Nonaktif'}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      )}

      {tab === 'restock' && (
        <Card className="overflow-hidden">
          {restock.isError ? (
            <ErrorState onRetry={() => restock.refetch()} />
          ) : restock.isLoading ? (
            <LoadingState />
          ) : (restock.data || []).length === 0 ? (
            <EmptyState message="Tidak ada produk yang perlu di-restock." />
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="text-left p-3 font-medium">Produk</th>
                  <th className="text-right p-3 font-medium">Stok</th>
                  <th className="text-right p-3 font-medium">ADS</th>
                  <th className="text-right p-3 font-medium">Sisa Hari</th>
                  <th className="text-right p-3 font-medium">Saran Qty</th>
                  <th className="text-left p-3 font-medium">Pemasok</th>
                </tr>
              </thead>
              <tbody>
                {(restock.data || []).map((r) => (
                  <tr key={r.produk_sample_id} className="border-b last:border-0 hover:bg-gray-50">
                    <td className="p-3 font-medium">{r.nama_produk}</td>
                    <td className={`p-3 text-right ${r.stock < 5 ? 'text-red-600 font-bold' : ''}`}>{r.stock}</td>
                    <td className="p-3 text-right">{r.ads?.toFixed(1)}</td>
                    <td className="p-3 text-right">
                      {r.days_remaining == null ? '—' : r.days_remaining.toFixed(1)}
                    </td>
                    <td className="p-3 text-right font-semibold">{Math.ceil(r.suggested_qty)}</td>
                    <td className="p-3">{r.supplier || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      )}

      {tab === 'history' && (
        <Card className="overflow-hidden">
          {purchases.isError ? (
            <ErrorState onRetry={() => purchases.refetch()} />
          ) : purchases.isLoading ? (
            <LoadingState />
          ) : (purchases.data || []).length === 0 ? (
            <EmptyState message="Belum ada riwayat pembelian." />
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="text-left p-3 font-medium">Tanggal</th>
                  <th className="text-left p-3 font-medium">Produk</th>
                  <th className="text-left p-3 font-medium">Pemasok</th>
                  <th className="text-right p-3 font-medium">Qty</th>
                  <th className="text-right p-3 font-medium">Total</th>
                  <th className="text-left p-3 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {(purchases.data || []).map((p) => (
                  <tr key={p.barang_masuk_ref} className="border-b last:border-0 hover:bg-gray-50">
                    <td className="p-3 text-xs text-gray-500">{formatDate(p.date)}</td>
                    <td className="p-3 font-medium">{p.nama_produk}</td>
                    <td className="p-3">{p.supplier || '—'}</td>
                    <td className="p-3 text-right">{p.qty}</td>
                    <td className="p-3 text-right font-semibold">{formatRp(p.total)}</td>
                    <td className="p-3"><Badge tone="green">{p.status || '—'}</Badge></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      )}
    </div>
  );
}
