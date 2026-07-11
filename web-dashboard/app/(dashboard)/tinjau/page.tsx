'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../../lib/api';
import { formatDate, formatRp } from '../../../lib/format';
import { Card, ErrorState, LoadingState, EmptyState, Badge } from '../../../components/ui';

type PendingItem = {
  pesan_id: string;
  input_type: string;
  raw_text: string | null;
  status: string;
  received_at: string | null;
  intent: string | null;
  confidence: number | null;
  line_count: number;
  unmatched_count: number;
  calculated_total: number | null;
  can_approve: boolean;
  operator_name: string | null;
  payload: {
    customer_name?: string;
    resolved_items?: Array<{ nama_produk?: string; quantity?: number; subtotal?: number }>;
    unmatched?: unknown[];
  };
};

export default function TinjauPage() {
  const qc = useQueryClient();
  const pending = useQuery({
    queryKey: ['review-pending'],
    queryFn: async () => (await apiClient<PendingItem[]>('/admin/review/pending')).data || [],
  });

  const approve = useMutation({
    mutationFn: (id: string) =>
      apiClient(`/admin/review/${id}/approve`, { method: 'POST', body: '{}' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['review-pending'] }),
  });

  const reject = useMutation({
    mutationFn: (id: string) =>
      apiClient(`/admin/review/${id}/reject`, { method: 'POST', body: '{}' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['review-pending'] }),
  });

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-800 mb-2">Tinjau Pesan</h1>
      <p className="text-sm text-gray-500 mb-6 max-w-2xl">
        Setujui draf WhatsApp (foto notebook / teks) yang menunggu YA, atau batalkan.
        Satu foto bisa berisi banyak baris — harga &amp; total dari DB (No AI Math).
      </p>

      {pending.isError ? (
        <ErrorState onRetry={() => pending.refetch()} />
      ) : pending.isLoading ? (
        <LoadingState />
      ) : (pending.data || []).length === 0 ? (
        <EmptyState message="Tidak ada pesan menunggu tinjauan. Kirim foto daftar atau teks via WhatsApp untuk mengisi antrian." />
      ) : (
        <div className="space-y-4">
          {(pending.data || []).map((item) => (
            <Card key={item.pesan_id} className="p-5">
              <div className="flex flex-wrap items-start justify-between gap-3 mb-3">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <Badge tone={item.status === 'NEEDS_REVIEW' ? 'yellow' : 'green'}>
                      {item.status}
                    </Badge>
                    <span className="text-xs text-gray-500">{item.input_type}</span>
                    {item.intent && (
                      <span className="text-xs text-gray-500">{item.intent}</span>
                    )}
                  </div>
                  <p className="text-sm font-medium text-gray-800">
                    {item.payload?.customer_name || item.operator_name || 'Tanpa nama'}
                  </p>
                  <p className="text-xs text-gray-500 mt-0.5">{formatDate(item.received_at)}</p>
                </div>
                <div className="text-right">
                  <p className="text-lg font-semibold text-gray-800">
                    {item.calculated_total != null
                      ? formatRp(item.calculated_total)
                      : '—'}
                  </p>
                  <p className="text-xs text-gray-500">
                    {item.line_count} item
                    {item.unmatched_count > 0 ? ` · ${item.unmatched_count} unmatched` : ''}
                    {item.confidence != null
                      ? ` · conf ${(item.confidence * 100).toFixed(0)}%`
                      : ''}
                  </p>
                </div>
              </div>

              {item.raw_text && (
                <p className="text-sm text-gray-600 bg-gray-50 rounded-lg p-3 mb-3 whitespace-pre-wrap">
                  {item.raw_text}
                </p>
              )}

              {(item.payload?.resolved_items || []).length > 0 && (
                <ul className="text-sm mb-4 space-y-1">
                  {(item.payload.resolved_items || []).map((li, i) => (
                    <li key={i} className="flex justify-between gap-4 border-b border-gray-100 py-1">
                      <span>
                        {li.nama_produk || 'Produk'} × {li.quantity ?? '?'}
                      </span>
                      <span className="text-gray-600">
                        {li.subtotal != null ? formatRp(li.subtotal) : ''}
                      </span>
                    </li>
                  ))}
                </ul>
              )}

              <div className="flex gap-2">
                <button
                  type="button"
                  disabled={!item.can_approve || approve.isPending}
                  onClick={() => approve.mutate(item.pesan_id)}
                  className="px-4 py-2 text-sm rounded-lg bg-primary text-white disabled:opacity-40"
                >
                  Setujui → Ledger
                </button>
                <button
                  type="button"
                  disabled={reject.isPending}
                  onClick={() => reject.mutate(item.pesan_id)}
                  className="px-4 py-2 text-sm rounded-lg border border-gray-300 text-gray-700"
                >
                  Batalkan
                </button>
              </div>
              {approve.isError && approve.variables === item.pesan_id && (
                <p className="text-xs text-red-600 mt-2">{(approve.error as Error)?.message}</p>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
