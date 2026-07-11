'use client';

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../../lib/api';
import { formatDate } from '../../../lib/format';
import { Card, ErrorState, LoadingState, EmptyState, Badge } from '../../../components/ui';

export default function NotificationsPage() {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['notifications'],
    queryFn: async () => (await apiClient<any[]>('/admin/notifications')).data || [],
  });

  if (isError) return <ErrorState onRetry={() => refetch()} />;

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-800 mb-6">Notifikasi</h1>
      <Card className="overflow-hidden">
        {isLoading ? <LoadingState /> : (data || []).length === 0 ? (
          <EmptyState message="Belum ada notifikasi." />
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
                <p className="text-sm text-gray-600">{n.content}</p>
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
