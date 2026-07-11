'use client';

import Link from 'next/link';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../../lib/api';
import { formatDate } from '../../../lib/format';
import { Card, ErrorState, LoadingState, EmptyState, Badge } from '../../../components/ui';
import { Lightbulb, RefreshCw, Truck, Check, X } from 'lucide-react';

export default function RecommendationsPage() {
  const qc = useQueryClient();

  const list = useQuery({
    queryKey: ['recommendations-list'],
    queryFn: async () => (await apiClient<any[]>('/admin/recommendations')).data || [],
  });

  const generate = useMutation({
    mutationFn: () => apiClient('/admin/recommendations/generate', { method: 'POST' }),
    onSuccess: () => {
      setTimeout(() => qc.invalidateQueries({ queryKey: ['recommendations-list'] }), 1500);
    },
  });

  const generatePo = useMutation({
    mutationFn: () =>
      apiClient('/admin/automations/auto-generate-purchase-orders/run', { method: 'POST' }),
  });

  const setStatus = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      apiClient(`/admin/ops/recommendations/${id}`, {
        method: 'PATCH',
        body: JSON.stringify({ status }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['recommendations-list'] }),
  });

  if (list.isError) return <ErrorState onRetry={() => list.refetch()} />;

  return (
    <div>
      <div className="flex flex-wrap justify-between items-center gap-3 mb-6">
        <div className="flex items-center gap-2">
          <Lightbulb size={22} className="text-yellow-500" />
          <div>
            <h1 className="text-2xl font-bold text-gray-800">Rekomendasi</h1>
            <p className="text-sm text-gray-500">Dari ADS/automasi — tindak lanjut ke Supply atau tandai selesai.</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Link href="/supply" className="inline-flex items-center gap-1.5 px-3 py-2 border rounded-lg text-sm hover:bg-gray-50">
            <Truck size={14} /> Supply
          </Link>
          <button
            disabled={generate.isPending}
            onClick={() => generate.mutate()}
            className="flex items-center gap-2 bg-primary text-white px-4 py-2 rounded-lg text-sm disabled:opacity-50"
          >
            <RefreshCw size={14} className={generate.isPending ? 'animate-spin' : ''} />
            {generate.isPending ? 'Mengantri...' : 'Generate'}
          </button>
        </div>
      </div>

      {generate.isSuccess && (
        <p className="text-sm text-green-600 mb-4">Job generate diantrikan. Refresh sebentar lagi.</p>
      )}
      {generatePo.isSuccess && (
        <p className="text-sm text-green-600 mb-4">PO draft diantrikan — buka Supply → Purchase Order.</p>
      )}

      <Card className="overflow-hidden">
        {list.isLoading ? (
          <LoadingState />
        ) : (list.data || []).length === 0 ? (
          <div className="p-10 text-center">
            <p className="text-gray-500 mb-4">Belum ada rekomendasi di database.</p>
            <button
              type="button"
              disabled={generate.isPending}
              onClick={() => generate.mutate()}
              className="inline-flex items-center gap-2 bg-primary text-white px-4 py-2 rounded-lg text-sm disabled:opacity-50"
            >
              <RefreshCw size={14} />
              Generate sekarang
            </button>
          </div>
        ) : (
          <div className="divide-y">
            {(list.data || []).map((r: any) => {
              const isRestock = String(r.jenis || '').toUpperCase().includes('RESTOCK')
                || String(r.jenis || '').toUpperCase().includes('STOCK');
              return (
                <div key={r.id} className="p-4 hover:bg-gray-50">
                  <div className="flex items-start justify-between gap-3 mb-1">
                    <h3 className="font-medium text-gray-800">{r.judul}</h3>
                    <div className="flex gap-2 shrink-0">
                      <Badge
                        tone={
                          r.priority === 'HIGH' || r.priority === 'CRITICAL'
                            ? 'red'
                            : r.priority === 'MEDIUM'
                              ? 'yellow'
                              : 'gray'
                        }
                      >
                        {r.priority}
                      </Badge>
                      <Badge tone="blue">{r.status}</Badge>
                    </div>
                  </div>
                  <p className="text-sm text-gray-600">{r.isi}</p>
                  <div className="flex flex-wrap gap-3 mt-2 text-xs text-gray-400">
                    <span>{r.jenis}</span>
                    <span>{formatDate(r.generated_at)}</span>
                    {r.alasan && <span className="truncate max-w-md">{r.alasan}</span>}
                  </div>
                  <div className="flex flex-wrap gap-2 mt-3">
                    {isRestock && (
                      <button
                        type="button"
                        disabled={generatePo.isPending}
                        onClick={() => generatePo.mutate()}
                        className="inline-flex items-center gap-1 px-3 py-1.5 text-xs bg-primary text-white rounded-lg disabled:opacity-50"
                      >
                        <Truck size={12} /> Buat PO draft
                      </button>
                    )}
                    {r.produk_sample_id && (
                      <Link
                        href={`/inventory/${encodeURIComponent(r.produk_sample_id)}`}
                        className="inline-flex items-center px-3 py-1.5 text-xs border rounded-lg hover:bg-gray-50"
                      >
                        Lihat stok
                      </Link>
                    )}
                    {r.status !== 'COMPLETED' && (
                      <button
                        type="button"
                        onClick={() => setStatus.mutate({ id: r.id, status: 'COMPLETED' })}
                        className="inline-flex items-center gap-1 px-3 py-1.5 text-xs border rounded-lg hover:bg-gray-50"
                      >
                        <Check size={12} /> Selesai
                      </button>
                    )}
                    {r.status !== 'REJECTED' && (
                      <button
                        type="button"
                        onClick={() => setStatus.mutate({ id: r.id, status: 'REJECTED' })}
                        className="inline-flex items-center gap-1 px-3 py-1.5 text-xs border rounded-lg hover:bg-gray-50 text-gray-500"
                      >
                        <X size={12} /> Abaikan
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </Card>
    </div>
  );
}
