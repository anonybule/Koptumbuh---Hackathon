'use client';

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../../lib/api';
import { formatDate } from '../../../lib/format';
import { Card, ErrorState, LoadingState, EmptyState, Badge } from '../../../components/ui';
import { RefreshCw } from 'lucide-react';

function truncate(text: string | undefined, max = 180) {
  if (!text) return '';
  const clean = text.replace(/\s+/g, ' ').trim();
  return clean.length > max ? `${clean.slice(0, max)}…` : clean;
}

export default function NotificationsPage() {
  const { data, isLoading, isError, refetch, isFetching } = useQuery({
    queryKey: ['notifications'],
    queryFn: async () => (await apiClient<any[]>('/admin/notifications')).data || [],
  });

  if (isError) return <ErrorState onRetry={() => refetch()} />;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-800">Notifikasi</h1>
        <button
          type="button"
          onClick={() => refetch()}
          className="inline-flex items-center gap-2 text-sm border rounded-lg px-3 py-2 hover:bg-gray-50"
        >
          <RefreshCw size={14} className={isFetching ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>
      <Card className="overflow-hidden">
        {isLoading ? <LoadingState /> : (data || []).length === 0 ? (
          <EmptyState message="Belum ada notifikasi. Konfirmasi WhatsApp akan muncul di sini." />
        ) : (
          <div className="divide-y">
            {(data || []).map((n) => (
              <div key={n.id} className="p-4 hover:bg-gray-50">
                <div className="flex items-start justify-between gap-3 mb-1">
                  <h3 className="font-medium text-gray-800">{n.title || n.message_type}</h3>
                  <div className="flex gap-2 shrink-0">
                    <Badge tone="blue">{n.channel}</Badge>
                    <Badge tone={n.status === 'SENT' || n.status === 'READ' ? 'green' : 'gray'}>
                      {n.status}
                    </Badge>
                  </div>
                </div>
                <p className="text-sm text-gray-600 whitespace-pre-wrap">{truncate(n.content)}</p>
                <p className="text-xs text-gray-400 mt-2">
                  {n.message_type} · {formatDate(n.created_at || n.sent_at)}
                </p>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
