'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../../lib/api';
import { Card, ErrorState, LoadingState, Badge, EmptyState } from '../../../components/ui';
import { Plus, Search, Truck } from 'lucide-react';

interface InventoryItem {
  id: string;
  name: string;
  stock: number;
  barcode?: string;
  lokasi_simpan?: string;
  low_stock?: boolean;
}

export default function InventoryPage() {
  const [search, setSearch] = useState('');
  const [q, setQ] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: '', barcode: '', stock: 0, buyPrice: 0, sellPrice: 0 });
  const [msg, setMsg] = useState('');
  const qc = useQueryClient();

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['inventory', q],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (q) params.set('q', q);
      const res = await apiClient<InventoryItem[]>(`/admin/inventory?${params}`);
      return res.data || [];
    },
  });

  const pipeline = useQuery({
    queryKey: ['ops-pipeline-inv'],
    queryFn: async () => (await apiClient<{ stages: { id: string; count: number }[] }>('/admin/ops/pipeline')).data!,
  });

  const draftPo = pipeline.data?.stages?.find((s) => s.id === 'draft_po')?.count || 0;
  const lowCount = (data || []).filter((i) => i.low_stock || i.stock < 5).length;

  const addMutation = useMutation({
    mutationFn: async () => {
      const res = await apiClient('/admin/inventory/add', {
        method: 'POST',
        body: JSON.stringify({
          nama_produk: form.name,
          kode_barcode: form.barcode || null,
          jumlah_masuk: form.stock,
          harga_beli: form.buyPrice,
          harga_jual: form.sellPrice,
        }),
      });
      if (!res.success) throw new Error('Gagal menambahkan');
      return res;
    },
    onSuccess: () => {
      setMsg('Produk ditambahkan!');
      setShowForm(false);
      setForm({ name: '', barcode: '', stock: 0, buyPrice: 0, sellPrice: 0 });
      qc.invalidateQueries({ queryKey: ['inventory'] });
    },
    onError: () => setMsg('Gagal menambahkan'),
  });

  if (isError) return <ErrorState onRetry={() => refetch()} />;

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Inventaris</h1>
          <p className="text-sm text-gray-500 mt-1">
            Stok turun setelah YA/POS; naik setelah PO diterima / restock.
          </p>
        </div>
        <div className="flex gap-2">
          <Link
            href="/supply"
            className="flex items-center gap-2 border px-4 py-2 rounded-lg text-sm hover:bg-gray-50"
          >
            <Truck size={16} /> Supply / PO
          </Link>
          <button
            onClick={() => setShowForm(!showForm)}
            className="flex items-center gap-2 bg-primary text-white px-4 py-2 rounded-lg hover:bg-primary/80"
          >
            <Plus size={18} /> Tambah Produk
          </button>
        </div>
      </div>

      {(lowCount > 0 || draftPo > 0) && (
        <Card className="p-4 mb-4 flex flex-wrap items-center justify-between gap-3 bg-amber-50/60 border-amber-100">
          <p className="text-sm text-amber-900">
            {lowCount > 0 && <span><strong>{lowCount}</strong> produk stok rendah. </span>}
            {draftPo > 0 && <span><strong>{draftPo}</strong> PO draft menunggu kirim/terima. </span>}
            Setelah PO ditandai diterima, cek detail produk untuk melihat pergerakan masuk.
          </p>
          <Link href="/supply" className="text-sm font-medium text-primary hover:underline">
            Buka rencana restock →
          </Link>
        </Card>
      )}

      {showForm && (
        <Card className="p-4 mb-4 grid grid-cols-2 md:grid-cols-5 gap-3">
          <input placeholder="Nama Produk *" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="px-3 py-2 border rounded text-sm" />
          <input placeholder="Barcode" value={form.barcode} onChange={(e) => setForm({ ...form, barcode: e.target.value })} className="px-3 py-2 border rounded text-sm" />
          <input type="number" placeholder="Stok Awal" value={form.stock || ''} onChange={(e) => setForm({ ...form, stock: +e.target.value })} className="px-3 py-2 border rounded text-sm" />
          <input type="number" placeholder="Harga Beli" value={form.buyPrice || ''} onChange={(e) => setForm({ ...form, buyPrice: +e.target.value })} className="px-3 py-2 border rounded text-sm" />
          <input type="number" placeholder="Harga Jual" value={form.sellPrice || ''} onChange={(e) => setForm({ ...form, sellPrice: +e.target.value })} className="px-3 py-2 border rounded text-sm" />
          <div className="col-span-full flex gap-2">
            <button onClick={() => { setMsg('Menambahkan...'); addMutation.mutate(); }} className="bg-primary text-white px-6 py-2 rounded-lg text-sm">Simpan</button>
            <button onClick={() => setShowForm(false)} className="px-4 py-2 border rounded-lg text-sm">Batal</button>
            {msg && <span className="text-sm self-center text-gray-500">{msg}</span>}
          </div>
        </Card>
      )}

      <Card className="overflow-hidden">
        <div className="p-3 border-b flex gap-2">
          <div className="relative flex-1">
            <Search size={16} className="absolute left-3 top-2.5 text-gray-400" />
            <input
              placeholder="Cari produk..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') setQ(search); }}
              className="w-full pl-10 pr-4 py-1.5 border rounded text-sm"
            />
          </div>
          <button onClick={() => setQ(search)} className="px-4 py-1.5 bg-primary text-white rounded text-sm">Cari</button>
        </div>
        {isLoading ? <LoadingState /> : (data || []).length === 0 ? (
          <EmptyState message="Belum ada produk di inventaris." />
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="text-left p-3 font-medium">Produk</th>
                <th className="text-right p-3 font-medium">Stok</th>
                <th className="text-left p-3 font-medium">Barcode</th>
                <th className="text-left p-3 font-medium">Lokasi</th>
                <th className="text-right p-3 font-medium">Aksi</th>
              </tr>
            </thead>
            <tbody>
              {(data || []).map((item) => (
                <tr key={item.id} className="border-b last:border-0 hover:bg-gray-50">
                  <td className="p-3 font-medium">
                    <Link href={`/inventory/${encodeURIComponent(item.id)}`} className="text-primary hover:underline">
                      {item.name}
                    </Link>
                    {item.low_stock && <span className="ml-2"><Badge tone="red">Stok rendah</Badge></span>}
                  </td>
                  <td className={`p-3 text-right ${item.stock < 5 ? 'text-red-600 font-bold' : ''}`}>{item.stock}</td>
                  <td className="p-3 text-gray-500 text-xs">{item.barcode || '—'}</td>
                  <td className="p-3 text-gray-500 text-xs">{item.lokasi_simpan || '—'}</td>
                  <td className="p-3 text-right">
                    <Link href={`/inventory/${encodeURIComponent(item.id)}`} className="text-primary text-xs hover:underline">Detail</Link>
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
