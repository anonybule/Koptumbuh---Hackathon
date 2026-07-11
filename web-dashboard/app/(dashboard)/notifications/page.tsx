'use client';

import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { apiClient } from '../../../lib/api';
import { formatDate } from '../../../lib/format';
import { Card, ErrorState, LoadingState, EmptyState, Badge } from '../../../components/ui';
import { RefreshCw } from 'lucide-react';
import Link from 'next/link';

function truncate(text: string | undefined, max = 180) {
  if (!text) return '';
  const clean = text.replace(/\s+/g, ' ').trim();
  return clean.length > max ? `${clean.slice(0, max)}…` : clean;
}

const TYPE_FILTERS = [
  { id: '', label: 'Semua' },
  { id: 'CONFIRMATION', label: 'Konfirmasi YA' },
  { id: 'BROADCAST', label: 'Broadcast' },
  { id: 'BRIEFING', label: 'Briefing' },
  { id: 'WINBACK', label: 'Win-back' },
  { id: 'ONBOARDING', label: 'Onboarding' },
  { id: 'MILESTONE', label: 'Milestone' },
  { id: 'ALERT', label: 'Alert' },
];

export default function NotificationsPage() {
  const [type, setType] = useState('');

  const { data, isLoading, isError, refetch, isFetching } = useQuery({
    queryKey: ['notifications', type],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (type) params.set('message_type', type);
      return (await apiClient<any[]>(`/admin/notifications?${params}`)).data || [];
    },
  });

  if (isError) return <ErrorState onRetry={() => refetch()} />;

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Notifikasi</h1>
          <p className="text-sm text-gray-500 mt-1">
            Hasil automasi & konfirmasi WhatsApp — filter per jenis kampanye.
          </p>
        </div>
        <div className="flex gap-2">
          <Link href="/automations" className="text-sm border rounded-lg px-3 py-2 hover:bg-gray-50">
            Automasi
          </Link>
          <button
            type="button"
            onClick={() => refetch()}
            className="inline-flex items-center gap-2 text-sm border rounded-lg px-3 py-2 hover:bg-gray-50"
          >
            <RefreshCw size={14} className={isFetching ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>
      </div>

      <div className="flex flex-wrap gap-2 mb-4">
        {TYPE_FILTERS.map((f) => (
          <button
            key={f.id || 'all'}
            type="button"
            onClick={() => setType(f.id)}
            className={`px-3 py-1.5 rounded-full text-xs border ${
              type === f.id ? 'bg-primary text-white border-primary' : 'bg-white text-gray-600 hover:bg-gray-50'
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      <Card className="overflow-hidden">
        {isLoading ? <LoadingState /> : (data || []).length === 0 ? (
          <EmptyState message="Belum ada notifikasi untuk filter ini. Jalankan automasi atau konfirmasi WhatsApp." />
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
