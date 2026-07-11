'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../../lib/api';
import { formatDate, formatRp } from '../../../lib/format';
import { Card, ErrorState, LoadingState, EmptyState, Tabs, Badge } from '../../../components/ui';
import { MessageSquare, RefreshCw } from 'lucide-react';

interface Transaction {
  id: string;
  customer: string;
  total: number;
  status: string;
  method: string;
  date: string;
}

interface InboxItem {
  pesan_id: string;
  input_type?: string;
  raw_text: string;
  message_status?: string;
  received_at?: string;
  sender_name?: string;
  sender_phone?: string;
  intent?: string;
  confidence?: number | null;
  parse_status?: string;
  stage?: string;
  payload?: Record<string, unknown>;
  validation_errors?: unknown[];
}

function stageBadge(stage?: string): { label: string; tone: 'green' | 'yellow' | 'red' | 'blue' | 'gray' } {
  switch (stage) {
    case 'awaiting_ya':
      return { label: 'Menunggu YA', tone: 'yellow' };
    case 'needs_review':
      return { label: 'Perlu review', tone: 'red' };
    case 'parsing':
      return { label: 'Parsing', tone: 'blue' };
    case 'done':
      return { label: 'Selesai', tone: 'green' };
    default:
      return { label: stage || 'Diterima', tone: 'gray' };
  }
}

function intentTone(intent?: string): 'green' | 'blue' | 'yellow' | 'gray' {
  const i = (intent || '').toUpperCase();
  if (i.includes('SALE') || i.includes('JUAL')) return 'green';
  if (i.includes('RECEIPT') || i.includes('PURCHASE') || i.includes('RESTOCK')) return 'blue';
  if (i.includes('KNOWLEDGE') || i.includes('ADJUST')) return 'yellow';
  return 'gray';
}

export default function TransactionsPage() {
  const [tab, setTab] = useState('sales');
  const [filter, setFilter] = useState('');

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const params = new URLSearchParams(window.location.search);
    if (params.get('tab') === 'inbox') setTab('inbox');
    const st = params.get('status');
    if (st) setFilter(st);
  }, []);

  const sales = useQuery({
    queryKey: ['transactions-list'],
    queryFn: async () => (await apiClient<Transaction[]>('/admin/transactions')).data || [],
    enabled: tab === 'sales',
  });

  const inbox = useQuery({
    queryKey: ['ops-inbox', filter],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filter) params.set('status', filter);
      return (await apiClient<InboxItem[]>(`/admin/ops/inbox?${params}`)).data || [];
    },
    enabled: tab === 'inbox',
    refetchInterval: 15000,
  });

  const filters = useMemo(
    () => [
      { id: '', label: 'Semua' },
      { id: 'VALID', label: 'Menunggu YA' },
      { id: 'NEEDS_REVIEW', label: 'Review' },
      { id: 'DRAFT', label: 'Draft' },
      { id: 'INVALID', label: 'Invalid' },
    ],
    [],
  );

  return (
    <div>
      <div className="flex flex-wrap items-start justify-between gap-3 mb-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Transaksi</h1>
          <p className="text-sm text-gray-500 mt-1">
            Penjualan ter-commit + inbox WhatsApp (parse → YA → commit).
          </p>
        </div>
        <div className="flex gap-2">
          <Link href="/chathub" className="inline-flex items-center gap-1.5 px-3 py-2 border rounded-lg text-sm hover:bg-gray-50">
            <MessageSquare size={14} /> ChatHub
          </Link>
          <button
            type="button"
            onClick={() => (tab === 'inbox' ? inbox.refetch() : sales.refetch())}
            className="inline-flex items-center gap-1.5 px-3 py-2 border rounded-lg text-sm hover:bg-gray-50"
          >
            <RefreshCw size={14} /> Refresh
          </button>
        </div>
      </div>

      <Tabs
        tabs={[
          { id: 'inbox', label: 'Inbox WhatsApp' },
          { id: 'sales', label: 'Penjualan' },
        ]}
        active={tab}
        onChange={setTab}
      />

      {tab === 'inbox' && (
        <>
          <div className="flex flex-wrap gap-2 mb-4">
            {filters.map((f) => (
              <button
                key={f.id || 'all'}
                type="button"
                onClick={() => setFilter(f.id)}
                className={`px-3 py-1.5 rounded-full text-xs border ${
                  filter === f.id ? 'bg-primary text-white border-primary' : 'bg-white text-gray-600 hover:bg-gray-50'
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>
          <Card className="overflow-hidden">
            <div className="px-4 py-3 border-b bg-gray-50 text-xs text-gray-500">
              Alur: pesan masuk → AI parse → VALID → anggota balas <strong>YA</strong> → transaksi &amp; stok ter-commit.
              Draft invalid masuk NEEDS_REVIEW.
            </div>
            {inbox.isError ? (
              <ErrorState onRetry={() => inbox.refetch()} />
            ) : inbox.isLoading ? (
              <LoadingState />
            ) : (inbox.data || []).length === 0 ? (
              <EmptyState message="Belum ada pesan WhatsApp. Kirim via ChatHub / Evolution webhook." />
            ) : (
              <div className="divide-y">
                {(inbox.data || []).map((m) => {
                  const st = stageBadge(m.stage);
                  const total = Number((m.payload as any)?.total || (m.payload as any)?.total_pembayaran || 0);
                  return (
                    <div key={m.pesan_id} className="p-4 hover:bg-gray-50">
                      <div className="flex flex-wrap items-start justify-between gap-2 mb-2">
                        <div>
                          <p className="font-medium text-gray-800">{m.sender_name}</p>
                          <p className="text-xs text-gray-400">{m.sender_phone || '—'} · {formatDate(m.received_at)}</p>
                        </div>
                        <div className="flex flex-wrap gap-1.5">
                          <Badge tone={st.tone}>{st.label}</Badge>
                          {m.intent && <Badge tone={intentTone(m.intent)}>{m.intent}</Badge>}
                          {m.parse_status && <Badge tone="gray">{m.parse_status}</Badge>}
                          {m.confidence != null && (
                            <Badge tone="blue">{(m.confidence * (m.confidence <= 1 ? 100 : 1)).toFixed(0)}%</Badge>
                          )}
                        </div>
                      </div>
                      <p className="text-sm text-gray-700 whitespace-pre-wrap bg-gray-50 border border-gray-100 rounded-lg p-3">
                        {m.raw_text || '—'}
                      </p>
                      <div className="flex flex-wrap gap-3 mt-2 text-xs text-gray-500">
                        <span>{m.input_type || 'text'}</span>
                        {total > 0 && <span>Estimasi: {formatRp(total)}</span>}
                        {Array.isArray(m.validation_errors) && m.validation_errors.length > 0 && (
                          <span className="text-red-600">{m.validation_errors.length} error validasi</span>
                        )}
                        {m.stage === 'awaiting_ya' && (
                          <span className="text-amber-700 font-medium">Balas YA di WhatsApp untuk commit</span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </Card>
        </>
      )}

      {tab === 'sales' && (
        <Card className="overflow-hidden">
          {sales.isError ? (
            <ErrorState onRetry={() => sales.refetch()} />
          ) : sales.isLoading ? (
            <LoadingState />
          ) : (sales.data || []).length === 0 ? (
            <EmptyState message="Belum ada transaksi. Catat via WhatsApp lalu balas YA, atau pakai POS." />
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="text-left p-3 font-medium">ID</th>
                  <th className="text-left p-3 font-medium">Pelanggan</th>
                  <th className="text-right p-3 font-medium">Total</th>
                  <th className="text-left p-3 font-medium">Bayar</th>
                  <th className="text-left p-3 font-medium">Status</th>
                  <th className="text-left p-3 font-medium">Tanggal</th>
                </tr>
              </thead>
              <tbody>
                {(sales.data || []).map((t) => (
                  <tr key={t.id} className="border-b last:border-0 hover:bg-gray-50">
                    <td className="p-3 text-xs text-gray-500 font-mono">{t.id}</td>
                    <td className="p-3 font-medium">{t.customer || 'Umum'}</td>
                    <td className="p-3 text-right font-semibold">{formatRp(t.total || 0)}</td>
                    <td className="p-3">{t.method}</td>
                    <td className="p-3">
                      <Badge tone={t.status === 'Paid' || t.status === 'Selesai' ? 'green' : 'yellow'}>
                        {t.status}
                      </Badge>
                    </td>
                    <td className="p-3 text-gray-500 text-xs">{formatDate(t.date)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      )}
    </div>
  );
}
