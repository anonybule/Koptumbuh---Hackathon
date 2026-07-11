'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../../lib/api';
import { Card, ErrorState, LoadingState, EmptyState, Badge } from '../../../components/ui';
import { MessageSquare, RefreshCw, Send, Wifi, WifiOff, QrCode } from 'lucide-react';

interface HubStatus {
  instance: string;
  state: string;
  connected: boolean;
  evolution_ok: boolean;
  error?: string;
}

interface ChatItem {
  id: string;
  remote_jid: string;
  phone: string;
  name: string;
  preview: string;
  updated_at?: string | null;
  source: string;
  unread?: number;
}

interface ChatMessage {
  id: string;
  remote_jid: string;
  from_me: boolean;
  text: string;
  timestamp?: string | null;
  source: string;
}

function formatTime(value?: string | null) {
  if (!value) return '';
  const n = Number(value);
  const d = Number.isFinite(n) && String(value).length <= 13
    ? new Date(n < 1e12 ? n * 1000 : n)
    : new Date(value);
  if (Number.isNaN(d.getTime())) return String(value).slice(0, 16);
  return d.toLocaleString('id-ID', {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export default function ChatHubPage() {
  const qc = useQueryClient();
  const [selected, setSelected] = useState<ChatItem | null>(null);
  const [draft, setDraft] = useState('');
  const [filter, setFilter] = useState('');
  const [showQr, setShowQr] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  const status = useQuery({
    queryKey: ['chathub-status'],
    queryFn: async () => (await apiClient<HubStatus>('/admin/chathub/status')).data!,
    refetchInterval: 15000,
  });

  const chats = useQuery({
    queryKey: ['chathub-chats'],
    queryFn: async () => {
      const res = await apiClient<{ chats: ChatItem[]; evolution_ok: boolean; evolution_error?: string }>(
        '/admin/chathub/chats',
      );
      return res.data!;
    },
    refetchInterval: 20000,
  });

  const messages = useQuery({
    queryKey: ['chathub-messages', selected?.remote_jid, selected?.phone],
    enabled: !!selected,
    queryFn: async () => {
      const params = new URLSearchParams();
      if (selected?.remote_jid) params.set('remote_jid', selected.remote_jid);
      if (selected?.phone) params.set('phone', selected.phone);
      params.set('limit', '80');
      const res = await apiClient<{ messages: ChatMessage[] }>(`/admin/chathub/messages?${params}`);
      return res.data?.messages || [];
    },
    refetchInterval: selected ? 10000 : false,
  });

  const inboxHint = useQuery({
    queryKey: ['chathub-inbox-hint', selected?.phone],
    enabled: !!selected?.phone,
    queryFn: async () => {
      const res = await apiClient<any[]>('/admin/ops/inbox?per_page=20');
      const phone = selected?.phone || '';
      return (res.data || []).filter(
        (m) => String(m.sender_phone || '').includes(phone) || phone.includes(String(m.sender_phone || '').replace(/\D/g, '')),
      ).slice(0, 3);
    },
  });

  const qr = useQuery({
    queryKey: ['chathub-qr'],
    enabled: showQr,
    queryFn: async () => (await apiClient<{ qr?: string; pairing_code?: string }>('/admin/chathub/qr')).data!,
  });

  const send = useMutation({
    mutationFn: async () => {
      if (!selected?.phone || !draft.trim()) throw new Error('Pilih chat dan tulis pesan');
      return apiClient('/admin/chathub/send', {
        method: 'POST',
        body: JSON.stringify({ number: selected.phone, text: draft.trim() }),
      });
    },
    onSuccess: () => {
      setDraft('');
      qc.invalidateQueries({ queryKey: ['chathub-messages'] });
      qc.invalidateQueries({ queryKey: ['chathub-chats'] });
    },
  });

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages.data]);

  const filtered = useMemo(() => {
    const q = filter.trim().toLowerCase();
    const list = chats.data?.chats || [];
    if (!q) return list;
    return list.filter(
      (c) =>
        c.name.toLowerCase().includes(q) ||
        c.phone.includes(q) ||
        (c.preview || '').toLowerCase().includes(q),
    );
  }, [chats.data, filter]);

  const connected = status.data?.connected;

  return (
    <div className="h-[calc(100vh-7rem)] min-h-[520px] flex flex-col">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-800 flex items-center gap-2">
            <MessageSquare size={26} className="text-primary" />
            ChatHub
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Inbox WhatsApp via Evolution API — instance{' '}
            <span className="font-medium text-gray-700">{status.data?.instance || '…'}</span>
            {' · '}
            <a href="/transactions?tab=inbox" className="text-primary hover:underline">
              lihat parsing / YA
            </a>
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge tone={connected ? 'green' : status.data?.evolution_ok === false ? 'red' : 'yellow'}>
            <span className="inline-flex items-center gap-1">
              {connected ? <Wifi size={12} /> : <WifiOff size={12} />}
              {status.data?.state || 'memuat…'}
            </span>
          </Badge>
          {!connected && (
            <button
              type="button"
              onClick={() => setShowQr((v) => !v)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 border rounded-lg text-sm hover:bg-gray-50"
            >
              <QrCode size={14} />
              {showQr ? 'Tutup QR' : 'Scan QR'}
            </button>
          )}
          <button
            type="button"
            onClick={() => {
              status.refetch();
              chats.refetch();
              if (selected) messages.refetch();
            }}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-primary text-white rounded-lg text-sm"
          >
            <RefreshCw size={14} />
            Refresh
          </button>
        </div>
      </div>

      {showQr && (
        <Card className="p-4 mb-4">
          <p className="text-sm text-gray-600 mb-3">
            Scan QR dengan WhatsApp → Linked devices untuk menghubungkan instance Evolution.
          </p>
          {qr.isLoading ? (
            <LoadingState label="Memuat QR…" />
          ) : qr.isError ? (
            <ErrorState message="Gagal memuat QR dari Evolution API." onRetry={() => qr.refetch()} />
          ) : qr.data?.qr ? (
            <img
              src={
                String(qr.data.qr).startsWith('data:')
                  ? String(qr.data.qr)
                  : `data:image/png;base64,${String(qr.data.qr).replace(/^data:image\/\w+;base64,/, '')}`
              }
              alt="Evolution QR"
              className="w-56 h-56 object-contain mx-auto border rounded-lg bg-white"
            />
          ) : (
            <p className="text-sm text-gray-500">
              QR tidak tersedia{qr.data?.pairing_code ? ` — pairing code: ${qr.data.pairing_code}` : '.'}
            </p>
          )}
        </Card>
      )}

      <Card className="flex-1 min-h-0 overflow-hidden grid grid-cols-1 md:grid-cols-[280px_1fr]">
        <aside className="border-r border-gray-100 flex flex-col min-h-0">
          <div className="p-3 border-b">
            <input
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              placeholder="Cari nama / nomor…"
              className="w-full px-3 py-1.5 border rounded text-sm"
            />
          </div>
          <div className="flex-1 overflow-y-auto">
            {chats.isLoading ? (
              <LoadingState />
            ) : chats.isError ? (
              <ErrorState onRetry={() => chats.refetch()} />
            ) : filtered.length === 0 ? (
              <EmptyState message="Belum ada chat." />
            ) : (
              filtered.map((c) => (
                <button
                  key={c.id || c.phone}
                  type="button"
                  onClick={() => setSelected(c)}
                  className={`w-full text-left px-3 py-3 border-b last:border-0 hover:bg-gray-50 transition ${
                    selected?.phone === c.phone ? 'bg-primary/5' : ''
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <p className="font-medium text-sm text-gray-800 truncate">{c.name}</p>
                    <span className="text-[10px] text-gray-400 shrink-0">{c.source === 'evolution' ? 'WA' : 'DB'}</span>
                  </div>
                  <p className="text-xs text-gray-500 mt-0.5">{c.phone}</p>
                  {c.preview && (
                    <p className="text-xs text-gray-400 mt-1 truncate">{c.preview}</p>
                  )}
                </button>
              ))
            )}
          </div>
        </aside>

        <section className="flex flex-col min-h-0 bg-gray-50/50">
          {!selected ? (
            <div className="flex-1 flex items-center justify-center text-sm text-gray-400 p-8 text-center">
              Pilih percakapan di kiri, atau hubungkan WhatsApp lewat Scan QR.
            </div>
          ) : (
            <>
              <div className="px-4 py-3 border-b bg-white flex items-center justify-between">
                <div>
                  <p className="font-semibold text-gray-800">{selected.name}</p>
                  <p className="text-xs text-gray-500">{selected.phone}</p>
                </div>
              </div>

              {(inboxHint.data || []).length > 0 && (
                <div className="px-3 py-2 border-b bg-amber-50/80 text-xs space-y-1">
                  <p className="font-medium text-amber-900">Bot / parsing terkait kontak ini</p>
                  {(inboxHint.data || []).map((m: any) => (
                    <div key={m.pesan_id} className="flex flex-wrap gap-2 text-amber-800">
                      <Badge tone="yellow">{m.stage || m.parse_status}</Badge>
                      {m.intent && <Badge tone="blue">{m.intent}</Badge>}
                      <span className="truncate max-w-[220px]">{m.raw_text}</span>
                    </div>
                  ))}
                  <a href="/transactions?tab=inbox" className="text-primary hover:underline">Buka inbox lengkap →</a>
                </div>
              )}

              <div className="flex-1 overflow-y-auto p-4 space-y-2">
                {messages.isLoading ? (
                  <LoadingState />
                ) : messages.isError ? (
                  <ErrorState onRetry={() => messages.refetch()} />
                ) : (messages.data || []).length === 0 ? (
                  <EmptyState message="Belum ada pesan. Kirim pesan pertama di bawah." />
                ) : (
                  (messages.data || []).map((m, i) => (
                    <div
                      key={m.id || `${m.timestamp}-${i}`}
                      className={`flex ${m.from_me ? 'justify-end' : 'justify-start'}`}
                    >
                      <div
                        className={`max-w-[75%] rounded-2xl px-3 py-2 text-sm shadow-sm ${
                          m.from_me
                            ? 'bg-primary text-white rounded-br-md'
                            : 'bg-white text-gray-800 rounded-bl-md border border-gray-100'
                        }`}
                      >
                        <p className="whitespace-pre-wrap break-words">{m.text || '—'}</p>
                        <p className={`text-[10px] mt-1 ${m.from_me ? 'text-white/70' : 'text-gray-400'}`}>
                          {formatTime(m.timestamp)}
                          {m.source === 'database' ? ' · lokal' : ''}
                        </p>
                      </div>
                    </div>
                  ))
                )}
                <div ref={bottomRef} />
              </div>

              <form
                className="p-3 border-t bg-white flex gap-2"
                onSubmit={(e) => {
                  e.preventDefault();
                  if (!draft.trim() || send.isPending) return;
                  send.mutate();
                }}
              >
                <input
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  placeholder="Tulis pesan WhatsApp…"
                  className="flex-1 px-3 py-2 border rounded-lg text-sm"
                  disabled={!selected.phone}
                />
                <button
                  type="submit"
                  disabled={!draft.trim() || send.isPending || !selected.phone}
                  className="inline-flex items-center gap-1.5 px-4 py-2 bg-primary text-white rounded-lg text-sm disabled:opacity-50"
                >
                  <Send size={14} />
                  Kirim
                </button>
              </form>
              {send.isError && (
                <p className="px-3 pb-2 text-xs text-red-600">
                  {(send.error as Error)?.message || 'Gagal mengirim. Pastikan Evolution terhubung.'}
                </p>
              )}
            </>
          )}
        </section>
      </Card>
    </div>
  );
}
