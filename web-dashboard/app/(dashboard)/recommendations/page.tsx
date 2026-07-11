'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../../lib/api';
import { formatDate } from '../../../lib/format';
import { Card, ErrorState, LoadingState, EmptyState, Badge } from '../../../components/ui';
import { Lightbulb, RefreshCw } from 'lucide-react';

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

  if (list.isError) return <ErrorState onRetry={() => list.refetch()} />;

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div className="flex items-center gap-2">
          <Lightbulb size={22} className="text-yellow-500" />
          <h1 className="text-2xl font-bold text-gray-800">Rekomendasi</h1>
        </div>
        <button
          disabled={generate.isPending}
          onClick={() => generate.mutate()}
          className="flex items-center gap-2 bg-primary text-white px-4 py-2 rounded-lg text-sm disabled:opacity-50"
        >
          <RefreshCw size={14} className={generate.isPending ? 'animate-spin' : ''} />
          {generate.isPending ? 'Mengantri...' : 'Generate'}
        </button>
      </div>

      {generate.isSuccess && (
        <p className="text-sm text-green-600 mb-4">Job generate diantrikan. Refresh sebentar lagi.</p>
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
            <p className="text-xs text-gray-400 mt-3">
              Atau pastikan seed demo sudah memuat rekomendasi awal.
            </p>
          </div>
        ) : (
          <div className="divide-y">
            {(list.data || []).map((r: any) => (
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
                <div className="flex gap-3 mt-2 text-xs text-gray-400">
                  <span>{r.jenis}</span>
                  <span>{formatDate(r.generated_at)}</span>
                  {r.alasan && <span className="truncate max-w-md">{r.alasan}</span>}
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
