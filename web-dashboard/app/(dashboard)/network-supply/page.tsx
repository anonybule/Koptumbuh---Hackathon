'use client';

import { useMemo, useState } from 'react';
import Link from 'next/link';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../../lib/api';
import { Card, ErrorState, LoadingState, EmptyState, Tabs, Badge } from '../../../components/ui';
import { Network, Play, RefreshCw, MapPin } from 'lucide-react';

type Scope = 'kecamatan' | 'kab_kota' | 'provinsi';

interface StoreRow {
  koperasi_ref: string;
  nama_koperasi: string;
  desa?: string;
  kecamatan?: string;
  kab_kota?: string;
  low_stock_count: number;
  sku_count: number;
  draft_po_count: number;
  is_home?: boolean;
}

interface Overview {
  scope: string;
  home_wilayah?: { kecamatan?: string; kab_kota?: string; desa_kelurahan?: string; kode_wilayah?: string };
  store_count: number;
  stores_needing_restock: number;
  total_low_stock_skus: number;
  total_draft_pos: number;
  stores: StoreRow[];
}

interface NeedsData {
  by_store: {
    koperasi_ref: string;
    nama_koperasi: string;
    desa?: string;
    item_count: number;
    items: {
      nama_produk: string;
      stock: number;
      ads: number;
      days_remaining: number | null;
      suggested_qty: number;
    }[];
  }[];
  consolidated: {
    nama_produk: string;
    total_suggested_qty: number;
    stores_needing: number;
    min_days_remaining: number | null;
    store_breakdown: {
      nama_koperasi: string;
      desa?: string;
      stock: number;
      suggested_qty: number;
      days_remaining: number | null;
    }[];
  }[];
  stores_with_needs: number;
}

interface MatrixData {
  stores: { koperasi_ref: string; nama_koperasi: string; desa?: string; short_name: string }[];
  products: { key: string; nama_produk: string }[];
  cells: {
    koperasi_ref: string;
    product_key: string;
    stock: number;
    needs_restock: boolean;
    critical: boolean;
  }[];
}

export default function NetworkSupplyPage() {
  const [scope, setScope] = useState<Scope>('kecamatan');
  const [tab, setTab] = useState('stores');
  const [selected, setSelected] = useState<string[]>([]);
  const qc = useQueryClient();

  const overview = useQuery({
    queryKey: ['network-overview', scope],
    queryFn: async () =>
      (await apiClient<Overview>(`/admin/network-supply/overview?scope=${scope}`)).data!,
  });

  const needs = useQuery({
    queryKey: ['network-needs', scope],
    queryFn: async () =>
      (await apiClient<NeedsData>(`/admin/network-supply/needs?scope=${scope}`)).data!,
    enabled: tab === 'needs' || tab === 'consolidated',
  });

  const matrix = useQuery({
    queryKey: ['network-matrix', scope],
    queryFn: async () =>
      (await apiClient<MatrixData>(`/admin/network-supply/matrix?scope=${scope}`)).data!,
    enabled: tab === 'matrix',
  });

  const batchPo = useMutation({
    mutationFn: () =>
      apiClient('/admin/network-supply/batch-po', {
        method: 'POST',
        body: JSON.stringify({
          scope,
          koperasi_refs: selected.length ? selected : undefined,
          only_with_needs: true,
        }),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['network-overview'] });
      qc.invalidateQueries({ queryKey: ['purchase-orders'] });
    },
  });

  const cellMap = useMemo(() => {
    const m = new Map<string, MatrixData['cells'][0]>();
    for (const c of matrix.data?.cells || []) {
      m.set(`${c.product_key}::${c.koperasi_ref}`, c);
    }
    return m;
  }, [matrix.data]);

  const toggleStore = (ref: string) => {
    setSelected((prev) => (prev.includes(ref) ? prev.filter((x) => x !== ref) : [...prev, ref]));
  };

  const selectAllNeeding = () => {
    const refs = (overview.data?.stores || [])
      .filter((s) => s.low_stock_count > 0)
      .map((s) => s.koperasi_ref);
    setSelected(refs);
  };

  const home = overview.data?.home_wilayah;
  const rangeLabel =
    scope === 'kecamatan'
      ? home?.kecamatan || 'Kecamatan'
      : scope === 'kab_kota'
        ? home?.kab_kota || 'Kabupaten'
        : home?.kab_kota
          ? `Provinsi (${home?.kab_kota})`
          : 'Provinsi';

  return (
    <div>
      <div className="flex flex-wrap items-start justify-between gap-3 mb-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-800 flex items-center gap-2">
            <Network size={26} className="text-primary" />
            Network Supply
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Multi-Kopdes stok, kebutuhan restock, dan PO batch dalam satu wilayah untuk efisiensi logistik.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link href="/supply" className="px-3 py-2 border rounded-lg text-sm hover:bg-gray-50">
            Supply toko ini
          </Link>
          <button
            type="button"
            onClick={() => {
              overview.refetch();
              needs.refetch();
              matrix.refetch();
            }}
            className="inline-flex items-center gap-1.5 px-3 py-2 border rounded-lg text-sm hover:bg-gray-50"
          >
            <RefreshCw size={14} /> Refresh
          </button>
          <button
            type="button"
            disabled={batchPo.isPending}
            onClick={() => batchPo.mutate()}
            className="inline-flex items-center gap-1.5 px-3 py-2 bg-primary text-white rounded-lg text-sm disabled:opacity-50"
          >
            <Play size={14} />
            {batchPo.isPending ? 'Membuat PO…' : 'Batch PO draft'}
          </button>
        </div>
      </div>

      <Card className="p-4 mb-4">
        <div className="flex flex-wrap items-center gap-3">
          <MapPin size={16} className="text-primary" />
          <span className="text-sm text-gray-600">Jangkauan wilayah:</span>
          {(['kecamatan', 'kab_kota', 'provinsi'] as Scope[]).map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => {
                setScope(s);
                setSelected([]);
              }}
              className={`px-3 py-1.5 rounded-full text-xs border ${
                scope === s ? 'bg-primary text-white border-primary' : 'bg-white text-gray-600'
              }`}
            >
              {s === 'kecamatan' ? 'Kecamatan' : s === 'kab_kota' ? 'Kabupaten' : 'Provinsi'}
            </button>
          ))}
          <span className="text-xs text-gray-400 ml-auto">
            Aktif: <strong className="text-gray-600">{rangeLabel}</strong>
            {home?.kode_wilayah ? ` · ${home.kode_wilayah}` : ''}
          </span>
        </div>
      </Card>

      {overview.isError ? (
        <ErrorState onRetry={() => overview.refetch()} />
      ) : overview.isLoading ? (
        <LoadingState />
      ) : (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
            {[
              { label: 'Kopdes dalam jangkauan', value: overview.data?.store_count },
              { label: 'Toko perlu restock', value: overview.data?.stores_needing_restock },
              { label: 'SKU stok rendah', value: overview.data?.total_low_stock_skus },
              { label: 'PO draft aktif', value: overview.data?.total_draft_pos },
            ].map((c) => (
              <Card key={c.label} className="p-4">
                <p className="text-xs text-gray-500">{c.label}</p>
                <p className="text-2xl font-bold text-primary mt-1">{c.value ?? 0}</p>
              </Card>
            ))}
          </div>

          {batchPo.isSuccess && (
            <p className="text-sm text-green-600 mb-3">
              Batch PO selesai — {(batchPo.data as any)?.data?.pos_created ?? 0} PO dibuat di{' '}
              {(batchPo.data as any)?.data?.targets ?? 0} toko. Cek tab Supply → Purchase Order per toko.
            </p>
          )}
          {batchPo.isError && (
            <p className="text-sm text-red-600 mb-3">
              {(batchPo.error as Error)?.message || 'Gagal batch PO.'}
            </p>
          )}

          <Tabs
            tabs={[
              { id: 'stores', label: 'Toko / Kopdes' },
              { id: 'needs', label: 'Kebutuhan per toko' },
              { id: 'consolidated', label: 'Konsolidasi SKU' },
              { id: 'matrix', label: 'Matriks stok' },
            ]}
            active={tab}
            onChange={setTab}
          />

          {tab === 'stores' && (
            <Card className="overflow-hidden">
              <div className="px-4 py-3 border-b bg-gray-50 flex flex-wrap items-center justify-between gap-2 text-xs text-gray-500">
                <span>Centang toko untuk batch PO (kosong = semua yang punya kebutuhan).</span>
                <button type="button" onClick={selectAllNeeding} className="text-primary hover:underline">
                  Pilih semua yang stok rendah
                </button>
              </div>
              {(overview.data?.stores || []).length === 0 ? (
                <EmptyState message="Tidak ada Kopdes di jangkauan. Perluas ke Kabupaten atau jalankan seed network." />
              ) : (
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 border-b">
                    <tr>
                      <th className="p-3 w-10" />
                      <th className="text-left p-3">Kopdes</th>
                      <th className="text-left p-3">Desa</th>
                      <th className="text-right p-3">SKU</th>
                      <th className="text-right p-3">Stok rendah</th>
                      <th className="text-right p-3">PO draft</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(overview.data?.stores || []).map((s) => (
                      <tr key={s.koperasi_ref} className="border-b last:border-0 hover:bg-gray-50">
                        <td className="p-3">
                          <input
                            type="checkbox"
                            checked={selected.includes(s.koperasi_ref)}
                            onChange={() => toggleStore(s.koperasi_ref)}
                          />
                        </td>
                        <td className="p-3">
                          <p className="font-medium">{s.nama_koperasi}</p>
                          <p className="text-[11px] text-gray-400 font-mono">{s.koperasi_ref}</p>
                          {s.is_home && <Badge tone="blue">Toko Anda</Badge>}
                        </td>
                        <td className="p-3">{s.desa || '—'}</td>
                        <td className="p-3 text-right">{s.sku_count}</td>
                        <td className={`p-3 text-right font-semibold ${s.low_stock_count > 0 ? 'text-red-600' : ''}`}>
                          {s.low_stock_count}
                        </td>
                        <td className="p-3 text-right">{s.draft_po_count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </Card>
          )}

          {tab === 'needs' && (
            <Card className="overflow-hidden">
              {needs.isLoading ? (
                <LoadingState />
              ) : needs.isError ? (
                <ErrorState onRetry={() => needs.refetch()} />
              ) : (needs.data?.by_store || []).every((b) => b.item_count === 0) ? (
                <EmptyState message="Tidak ada kebutuhan restock di jangkauan ini." />
              ) : (
                <div className="divide-y">
                  {(needs.data?.by_store || [])
                    .filter((b) => b.item_count > 0)
                    .map((b) => (
                      <div key={b.koperasi_ref} className="p-4">
                        <div className="flex justify-between gap-2 mb-2">
                          <div>
                            <p className="font-medium text-gray-800">{b.nama_koperasi}</p>
                            <p className="text-xs text-gray-400">{b.desa || b.koperasi_ref}</p>
                          </div>
                          <Badge tone="yellow">{b.item_count} item</Badge>
                        </div>
                        <table className="w-full text-xs">
                          <thead>
                            <tr className="text-gray-500">
                              <th className="text-left py-1">Produk</th>
                              <th className="text-right py-1">Stok</th>
                              <th className="text-right py-1">ADS</th>
                              <th className="text-right py-1">Sisa hari</th>
                              <th className="text-right py-1">Saran</th>
                            </tr>
                          </thead>
                          <tbody>
                            {b.items.map((it) => (
                              <tr key={it.nama_produk}>
                                <td className="py-1">{it.nama_produk}</td>
                                <td className="py-1 text-right text-red-600 font-medium">{it.stock}</td>
                                <td className="py-1 text-right">{it.ads?.toFixed(1)}</td>
                                <td className="py-1 text-right">
                                  {it.days_remaining == null ? '—' : it.days_remaining.toFixed(1)}
                                </td>
                                <td className="py-1 text-right font-semibold">{Math.ceil(it.suggested_qty)}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ))}
                </div>
              )}
            </Card>
          )}

          {tab === 'consolidated' && (
            <Card className="overflow-hidden">
              <div className="px-4 py-3 border-b bg-gray-50 text-xs text-gray-500">
                SKU yang dibutuhkan banyak toko sekaligus — kandidat pengiriman gabungan ke satu pemasok regional.
              </div>
              {needs.isLoading ? (
                <LoadingState />
              ) : (needs.data?.consolidated || []).length === 0 ? (
                <EmptyState message="Belum ada konsolidasi kebutuhan." />
              ) : (
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 border-b">
                    <tr>
                      <th className="text-left p-3">Produk</th>
                      <th className="text-right p-3">Toko butuh</th>
                      <th className="text-right p-3">Total saran qty</th>
                      <th className="text-right p-3">Min sisa hari</th>
                      <th className="text-left p-3">Breakdown</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(needs.data?.consolidated || []).map((c) => (
                      <tr key={c.nama_produk} className="border-b last:border-0 align-top">
                        <td className="p-3 font-medium">{c.nama_produk}</td>
                        <td className="p-3 text-right">
                          <Badge tone={c.stores_needing >= 2 ? 'red' : 'yellow'}>{c.stores_needing}</Badge>
                        </td>
                        <td className="p-3 text-right font-semibold">{Math.ceil(c.total_suggested_qty)}</td>
                        <td className="p-3 text-right">
                          {c.min_days_remaining == null ? '—' : c.min_days_remaining.toFixed(1)}
                        </td>
                        <td className="p-3 text-xs text-gray-500">
                          {c.store_breakdown
                            .map((s) => `${s.desa || s.nama_koperasi}: ${Math.ceil(s.suggested_qty)}`)
                            .join(' · ')}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </Card>
          )}

          {tab === 'matrix' && (
            <Card className="overflow-auto">
              {matrix.isLoading ? (
                <LoadingState />
              ) : matrix.isError ? (
                <ErrorState onRetry={() => matrix.refetch()} />
              ) : (matrix.data?.products || []).length === 0 ? (
                <EmptyState message="Belum ada data stok jaringan." />
              ) : (
                <table className="w-full text-xs min-w-[640px]">
                  <thead className="bg-gray-50 border-b sticky top-0">
                    <tr>
                      <th className="text-left p-2 font-medium">Produk</th>
                      {(matrix.data?.stores || []).map((s) => (
                        <th key={s.koperasi_ref} className="text-center p-2 font-medium max-w-[100px]">
                          {s.short_name || s.desa || s.nama_koperasi}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {(matrix.data?.products || []).map((p) => (
                      <tr key={p.key} className="border-b last:border-0">
                        <td className="p-2 font-medium whitespace-nowrap">{p.nama_produk}</td>
                        {(matrix.data?.stores || []).map((s) => {
                          const cell = cellMap.get(`${p.key}::${s.koperasi_ref}`);
                          if (!cell) {
                            return (
                              <td key={s.koperasi_ref} className="p-2 text-center text-gray-300">
                                —
                              </td>
                            );
                          }
                          return (
                            <td
                              key={s.koperasi_ref}
                              className={`p-2 text-center font-semibold ${
                                cell.critical || cell.needs_restock
                                  ? 'bg-red-50 text-red-700'
                                  : 'text-gray-700'
                              }`}
                            >
                              {cell.stock}
                              {cell.needs_restock ? '!' : ''}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </Card>
          )}
        </>
      )}
    </div>
  );
}
