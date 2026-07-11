'use client';

import Link from 'next/link';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../../lib/api';
import { Card, ErrorState, LoadingState, Badge } from '../../../components/ui';
import {
  Bot, Play, Package, Lightbulb, Bell, HeartHandshake, ExternalLink,
} from 'lucide-react';

interface AutomationJob {
  id: string;
  title: string;
  description: string;
  schedule: string;
  category: string;
  result_href: string;
}

interface AutomationData {
  jobs: AutomationJob[];
  stats: {
    restock_items: number;
    draft_pos: number;
    open_recommendations: number;
    notifications_today: number;
    at_risk_members: number;
  };
}

const categoryTone: Record<string, 'green' | 'blue' | 'yellow' | 'gray' | 'red'> = {
  supply: 'green',
  relationship: 'blue',
  whatsapp: 'yellow',
  bi: 'gray',
  ops: 'gray',
};

export default function AutomationsPage() {
  const qc = useQueryClient();

  const data = useQuery({
    queryKey: ['automations'],
    queryFn: async () => (await apiClient<AutomationData>('/admin/automations')).data!,
  });

  const run = useMutation({
    mutationFn: (jobId: string) =>
      apiClient(`/admin/automations/${jobId}/run`, { method: 'POST' }),
    onSuccess: () => {
      setTimeout(() => qc.invalidateQueries({ queryKey: ['automations'] }), 1200);
      qc.invalidateQueries({ queryKey: ['purchase-orders'] });
      qc.invalidateQueries({ queryKey: ['restock-plan'] });
      qc.invalidateQueries({ queryKey: ['recommendations-list'] });
      qc.invalidateQueries({ queryKey: ['notifications'] });
    },
  });

  if (data.isError) return <ErrorState onRetry={() => data.refetch()} />;

  const stats = data.data?.stats;
  const jobs = data.data?.jobs || [];

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-800 flex items-center gap-2">
          <Bot size={26} className="text-primary" />
          Automasi
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          Jadwal Celery yang berjalan di belakang layar — lihat hasilnya dan jalankan manual untuk demo.
        </p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3 mb-6">
        {[
          { label: 'Perlu restock', value: stats?.restock_items, href: '/supply', icon: Package },
          { label: 'PO draft', value: stats?.draft_pos, href: '/supply', icon: Package },
          { label: 'Rekomendasi', value: stats?.open_recommendations, href: '/recommendations', icon: Lightbulb },
          { label: 'Notif hari ini', value: stats?.notifications_today, href: '/notifications', icon: Bell },
          { label: 'Anggota risiko', value: stats?.at_risk_members, href: '/customer-relationship', icon: HeartHandshake },
        ].map((s) => (
          <Link key={s.label} href={s.href}>
            <Card className="p-4 hover:border-primary/30 transition h-full">
              <div className="flex items-center gap-2 text-xs text-gray-500 mb-1">
                <s.icon size={14} />
                {s.label}
              </div>
              <p className="text-2xl font-bold text-primary">
                {data.isLoading ? '…' : s.value ?? 0}
              </p>
            </Card>
          </Link>
        ))}
      </div>

      {data.isLoading ? (
        <LoadingState />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {jobs.map((job) => (
            <Card key={job.id} className="p-5 flex flex-col">
              <div className="flex items-start justify-between gap-3 mb-2">
                <h2 className="font-semibold text-gray-800">{job.title}</h2>
                <Badge tone={categoryTone[job.category] || 'gray'}>{job.category}</Badge>
              </div>
              <p className="text-sm text-gray-600 flex-1">{job.description}</p>
              <p className="text-xs text-gray-400 mt-3 mb-4">Jadwal: {job.schedule}</p>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  disabled={run.isPending}
                  onClick={() => run.mutate(job.id)}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-primary text-white rounded-lg text-sm disabled:opacity-50"
                >
                  <Play size={14} />
                  Jalankan sekarang
                </button>
                <Link
                  href={job.result_href}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 border rounded-lg text-sm hover:bg-gray-50"
                >
                  <ExternalLink size={14} />
                  Lihat hasil
                </Link>
              </div>
              {run.isSuccess && run.variables === job.id && (
                <p className="text-xs text-green-600 mt-2">Job diantrikan / dijalankan.</p>
              )}
              {run.isError && run.variables === job.id && (
                <p className="text-xs text-red-600 mt-2">
                  {(run.error as Error)?.message || 'Gagal menjalankan. Pastikan Celery/Redis aktif.'}
                </p>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
