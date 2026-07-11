'use client';

import { useMemo, useState } from 'react';
import Link from 'next/link';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../../lib/api';
import { formatRp, formatDate } from '../../../lib/format';
import { Card, ErrorState, LoadingState, EmptyState, Tabs, Badge } from '../../../components/ui';
import { HeartHandshake, MessageCircle, Play } from 'lucide-react';

interface SegmentRow {
  anggota_ref: string;
  nama: string;
  frekuensi: number;
  moneter: number;
  resensi_hari: number;
  segmentasi: string;
  status_retensi: string;
}

interface RetentionData {
  counts: Record<string, number>;
  members: SegmentRow[];
}

interface CampaignData {
  campaigns: { id: string; title: string; message_type: string; count: number; last_at?: string | null }[];
  at_risk_members: number;
  recent: { id: string; message_type?: string; title?: string; content?: string; status?: string; at?: string }[];
}

function tierTone(tier: string): 'green' | 'blue' | 'yellow' | 'gray' | 'red' {
  const t = (tier || '').toUpperCase();
  if (t === 'DIAMOND' || t === 'EMAS') return 'green';
  if (t === 'PERAK') return 'blue';
  if (t === 'PERUNGGU') return 'yellow';
  if (t.includes('HILANG') || t.includes('RISIKO')) return 'red';
  return 'gray';
}

const JOB_BY_CAMPAIGN: Record<string, string> = {
  winback: 'winback-campaign',
  onboarding: 'onboarding-check',
  milestone: 'member-milestone-check',
  broadcast: 'morning-price-broadcast',
};

export default function CustomerRelationshipPage() {
  const [tab, setTab] = useState('segmentation');
  const qc = useQueryClient();

  const segments = useQuery({
    queryKey: ['cr-segmentation'],
    queryFn: async () => (await apiClient<SegmentRow[]>('/admin/dashboard/segmentation')).data || [],
  });
  const retention = useQuery({
    queryKey: ['cr-retention'],
    queryFn: async () =>
      (await apiClient<RetentionData>('/admin/dashboard/retention')).data || { counts: {}, members: [] },
  });
  const campaigns = useQuery({
    queryKey: ['cr-campaigns'],
    queryFn: async () => (await apiClient<CampaignData>('/admin/ops/campaigns')).data!,
    enabled: tab === 'campaigns',
  });

  const runJob = useMutation({
    mutationFn: (jobId: string) =>
      apiClient(`/admin/automations/${jobId}/run`, { method: 'POST' }),
    onSuccess: () => {
      setTimeout(() => qc.invalidateQueries({ queryKey: ['cr-campaigns'] }), 1500);
    },
  });

  const tierCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const r of segments.data || []) {
      const k = r.segmentasi || 'UNKNOWN';
      counts[k] = (counts[k] || 0) + 1;
    }
    return counts;
  }, [segments.data]);

  if (segments.isError && retention.isError) {
    return <ErrorState onRetry={() => { segments.refetch(); retention.refetch(); }} />;
  }

  const rows = tab === 'retention' ? retention.data?.members || [] : segments.data || [];

  return (
    <div>
      <div className="flex flex-wrap items-start justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800 flex items-center gap-2">
            <HeartHandshake size={26} className="text-primary" />
            Customer Relationship
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Segmentasi RFM, retensi, dan hasil kampanye WhatsApp otomatis.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link
            href="/automations"
            className="inline-flex items-center gap-2 px-4 py-2 border rounded-lg text-sm hover:bg-gray-50"
          >
            Automasi hubungan
          </Link>
          <Link
            href="/chathub"
            className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg text-sm"
          >
            <MessageCircle size={16} />
            Buka ChatHub
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
        {Object.entries(tierCounts).length === 0 && segments.isLoading ? (
          <Card className="p-4 col-span-full"><LoadingState /></Card>
        ) : (
          (Object.keys(tierCounts).length
            ? Object.entries(tierCounts)
            : [['DIAMOND', 0], ['EMAS', 0], ['PERAK', 0], ['PERUNGGU', 0], ['TIDAK_AKTIF', 0]]
          ).map(([tier, count]) => (
            <Card key={tier} className="p-4">
              <p className="text-xs text-gray-500 uppercase tracking-wide">{tier}</p>
              <p className="text-2xl font-bold text-primary mt-1">{count as number}</p>
            </Card>
          ))
        )}
      </div>

      {retention.data?.counts && Object.keys(retention.data.counts).length > 0 && (
        <Card className="p-4 mb-6">
          <h2 className="text-sm font-semibold text-gray-700 mb-3">Status retensi</h2>
          <div className="flex flex-wrap gap-2">
            {Object.entries(retention.data.counts).map(([status, count]) => (
              <span key={status} className="text-xs px-3 py-1.5 bg-gray-100 rounded-full text-gray-700">
                {status.replaceAll('_', ' ')}: <strong>{count}</strong>
              </span>
            ))}
          </div>
        </Card>
      )}

      <Card className="overflow-hidden">
        <div className="px-4 pt-3">
          <Tabs
            tabs={[
              { id: 'segmentation', label: 'Segmentasi RFM' },
              { id: 'retention', label: 'Retensi' },
              { id: 'campaigns', label: 'Kampanye' },
            ]}
            active={tab}
            onChange={setTab}
          />
        </div>

        {tab === 'campaigns' ? (
          campaigns.isError ? (
            <ErrorState onRetry={() => campaigns.refetch()} />
          ) : campaigns.isLoading ? (
            <LoadingState />
          ) : (
            <div className="p-4 space-y-4">
              <p className="text-sm text-gray-600">
                Anggota berisiko hilang (&gt;60 hari):{' '}
                <strong>{campaigns.data?.at_risk_members ?? 0}</strong>
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {(campaigns.data?.campaigns || []).map((c) => (
                  <div key={c.id} className="border rounded-lg p-4">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <p className="font-medium text-gray-800">{c.title}</p>
                        <p className="text-xs text-gray-400 mt-1">
                          {c.count} notifikasi · terakhir {c.last_at ? formatDate(c.last_at) : '—'}
                        </p>
                      </div>
                      {JOB_BY_CAMPAIGN[c.id] && (
                        <button
                          type="button"
                          disabled={runJob.isPending}
                          onClick={() => runJob.mutate(JOB_BY_CAMPAIGN[c.id])}
                          className="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs bg-primary text-white rounded-lg disabled:opacity-50"
                        >
                          <Play size={12} /> Jalankan
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
              <div>
                <h3 className="text-sm font-semibold text-gray-700 mb-2">Aktivitas terbaru</h3>
                {(campaigns.data?.recent || []).length === 0 ? (
                  <EmptyState message="Belum ada log kampanye. Jalankan automasi di atas." />
                ) : (
                  <div className="divide-y border rounded-lg">
                    {(campaigns.data?.recent || []).slice(0, 10).map((n) => (
                      <div key={n.id} className="p-3">
                        <div className="flex justify-between gap-2">
                          <p className="text-sm font-medium">{n.title || n.message_type}</p>
                          <Badge tone="gray">{n.status || '—'}</Badge>
                        </div>
                        <p className="text-xs text-gray-500 mt-1">{n.content}</p>
                        <p className="text-[11px] text-gray-400 mt-1">{formatDate(n.at)}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )
        ) : (tab === 'segmentation' ? segments.isLoading : retention.isLoading) ? (
          <LoadingState />
        ) : rows.length === 0 ? (
          <EmptyState message="Belum ada data hubungan pelanggan." />
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="text-left p-3 font-medium">Anggota</th>
                <th className="text-left p-3 font-medium">Tier</th>
                <th className="text-left p-3 font-medium">Retensi</th>
                <th className="text-right p-3 font-medium">Frekuensi</th>
                <th className="text-right p-3 font-medium">Moneter</th>
                <th className="text-right p-3 font-medium">Resensi (hari)</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.anggota_ref} className="border-b last:border-0 hover:bg-gray-50">
                  <td className="p-3 font-medium">{r.nama}</td>
                  <td className="p-3">
                    <Badge tone={tierTone(r.segmentasi)}>{r.segmentasi}</Badge>
                  </td>
                  <td className="p-3">
                    <Badge tone={tierTone(r.status_retensi)}>
                      {(r.status_retensi || '—').replaceAll('_', ' ')}
                    </Badge>
                  </td>
                  <td className="p-3 text-right">{r.frekuensi}</td>
                  <td className="p-3 text-right">{formatRp(r.moneter || 0)}</td>
                  <td className="p-3 text-right">{r.resensi_hari}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
