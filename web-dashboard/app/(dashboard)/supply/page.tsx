'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../../lib/api';
import { formatRp, formatDate } from '../../../lib/format';
import { Card, ErrorState, LoadingState, Tabs, Badge, EmptyState } from '../../../components/ui';
import { Bot, Play, ChevronDown, ChevronUp } from 'lucide-react';

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

interface PurchaseOrder {
  po_id: string;
  status: string;
  tanggal_order?: string;
  tanggal_estimasi?: string;
  catatan?: string;
  created_at?: string;
  supplier?: string;
  item_count: number;
  total_estimasi: number;
}

interface PoDetail {
  po_id: string;
  status: string;
  supplier?: string;
  catatan?: string;
  items: {
    poi_id: string;
    nama_produk: string;
    jumlah_dipesan: number;
    harga_per_unit?: number | null;
  }[];
}

function poTone(status: string): 'green' | 'yellow' | 'gray' | 'red' | 'blue' {
  if (status === 'DITERIMA') return 'green';
  if (status === 'DRAFT') return 'yellow';
  if (status === 'DIKIRIM' || status === 'DITERIMA_SEBAGIAN') return 'blue';
  if (status === 'DIBATALKAN') return 'red';
  return 'gray';
}

export default function SupplyPage() {
  const [tab, setTab] = useState('restock');
  const [expanded, setExpanded] = useState<string | null>(null);
  const qc = useQueryClient();

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

  const orders = useQuery({
    queryKey: ['purchase-orders'],
    queryFn: async () => (await apiClient<PurchaseOrder[]>('/admin/purchase-orders')).data || [],
    enabled: tab === 'orders',
  });

  const detail = useQuery({
    queryKey: ['purchase-order', expanded],
    enabled: !!expanded,
    queryFn: async () =>
      (await apiClient<PoDetail>(`/admin/purchase-orders/${expanded}`)).data!,
  });

  const generatePo = useMutation({
    mutationFn: () =>
      apiClient('/admin/automations/auto-generate-purchase-orders/run', { method: 'POST' }),
    onSuccess: () => {
      setTimeout(() => {
        qc.invalidateQueries({ queryKey: ['purchase-orders'] });
        qc.invalidateQueries({ queryKey: ['restock-plan'] });
      }, 1000);
    },
  });

  const updatePo = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      apiClient(`/admin/purchase-orders/${id}`, {
        method: 'PATCH',
        body: JSON.stringify({ status }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['purchase-orders'] }),
  });

  return (
    <div>
      <div className="flex flex-wrap items-start justify-between gap-3 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Supply</h1>
          <p className="text-sm text-gray-500 mt-1">
            Rencana restock ADS + purchase order otomatis dari engine supply chain.
          </p>
        </div>
        <div className="flex gap-2">
          <Link
            href="/automations"
            className="inline-flex items-center gap-1.5 px-3 py-2 border rounded-lg text-sm hover:bg-gray-50"
          >
            <Bot size={14} />
            Semua automasi
          </Link>
          <button
            type="button"
            disabled={generatePo.isPending}
            onClick={() => {
              setTab('orders');
              generatePo.mutate();
            }}
            className="inline-flex items-center gap-1.5 px-3 py-2 bg-primary text-white rounded-lg text-sm disabled:opacity-50"
          >
            <Play size={14} />
            {generatePo.isPending ? 'Membuat PO…' : 'Generate PO draft'}
          </button>
        </div>
      </div>

      {generatePo.isSuccess && (
        <p className="text-sm text-green-600 mb-3">Job auto-PO dijalankan. Cek tab Purchase Order.</p>
      )}
      {generatePo.isError && (
        <p className="text-sm text-red-600 mb-3">
          {(generatePo.error as Error)?.message || 'Gagal generate PO.'}
        </p>
      )}

      <Tabs
        tabs={[
          { id: 'restock', label: 'Rencana Restock' },
          { id: 'orders', label: 'Purchase Order' },
          { id: 'suppliers', label: 'Pemasok' },
          { id: 'history', label: 'Riwayat Pembelian' },
        ]}
        active={tab}
        onChange={setTab}
      />

      {tab === 'restock' && (
        <Card className="overflow-hidden">
          <div className="px-4 py-3 border-b bg-gray-50 text-xs text-gray-500">
            Automasi: stok ÷ ADS (14 hari). Flag jika sisa hari ≤ lead time + 2, atau stok &lt; 5.
            Celery 07:30 mengubah ini menjadi PO DRAFT.
          </div>
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

      {tab === 'orders' && (
        <Card className="overflow-hidden">
          <div className="px-4 py-3 border-b bg-gray-50 text-xs text-gray-500">
            Hasil automasi <code>auto_generate_po</code> — status DRAFT sampai operator kirim / terima / batalkan.
          </div>
          {orders.isError ? (
            <ErrorState onRetry={() => orders.refetch()} />
          ) : orders.isLoading ? (
            <LoadingState />
          ) : (orders.data || []).length === 0 ? (
            <EmptyState message="Belum ada purchase order. Klik Generate PO draft di atas." />
          ) : (
            <div className="divide-y">
              {(orders.data || []).map((po) => (
                <div key={po.po_id} className="p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <button
                      type="button"
                      className="text-left flex-1 min-w-0"
                      onClick={() => setExpanded(expanded === po.po_id ? null : po.po_id)}
                    >
                      <div className="flex items-center gap-2">
                        <p className="font-medium text-gray-800">{po.supplier || 'Pemasok'}</p>
                        <Badge tone={poTone(po.status)}>{po.status}</Badge>
                        {expanded === po.po_id ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                      </div>
                      <p className="text-xs text-gray-500 mt-1">
                        {po.item_count} item · {formatRp(po.total_estimasi)} · {formatDate(po.tanggal_order || po.created_at)}
                      </p>
                      {po.catatan && <p className="text-xs text-gray-400 mt-1">{po.catatan}</p>}
                    </button>
                    {po.status === 'DRAFT' && (
                      <div className="flex gap-2">
                        <button
                          type="button"
                          className="px-3 py-1.5 text-xs bg-primary text-white rounded-lg"
                          onClick={() => updatePo.mutate({ id: po.po_id, status: 'DIKIRIM' })}
                        >
                          Kirim
                        </button>
                        <button
                          type="button"
                          className="px-3 py-1.5 text-xs border rounded-lg"
                          onClick={() => updatePo.mutate({ id: po.po_id, status: 'DIBATALKAN' })}
                        >
                          Batalkan
                        </button>
                      </div>
                    )}
                    {po.status === 'DIKIRIM' && (
                      <button
                        type="button"
                        className="px-3 py-1.5 text-xs bg-green-600 text-white rounded-lg"
                        onClick={() => updatePo.mutate({ id: po.po_id, status: 'DITERIMA' })}
                      >
                        Tandai diterima
                      </button>
                    )}
                  </div>
                  {expanded === po.po_id && (
                    <div className="mt-3 ml-1 border-l-2 border-primary/20 pl-3">
                      {detail.isLoading ? (
                        <LoadingState label="Memuat item…" />
                      ) : (
                        <table className="w-full text-xs">
                          <thead>
                            <tr className="text-gray-500">
                              <th className="text-left py-1">Produk</th>
                              <th className="text-right py-1">Qty</th>
                              <th className="text-right py-1">Harga</th>
                            </tr>
                          </thead>
                          <tbody>
                            {(detail.data?.items || []).map((it) => (
                              <tr key={it.poi_id}>
                                <td className="py-1">{it.nama_produk}</td>
                                <td className="py-1 text-right">{it.jumlah_dipesan}</td>
                                <td className="py-1 text-right">{formatRp(it.harga_per_unit || 0)}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </Card>
      )}

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
