'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../../lib/api';
import { formatDate } from '../../../lib/format';
import { Card, ErrorState, LoadingState, EmptyState, Badge } from '../../../components/ui';
import { Plus, Pencil, Trash2, Search } from 'lucide-react';

const CATEGORIES = ['SOP', 'FAQ', 'TIPS', 'BIMBINGAN_USAHA'];

export default function KnowledgePage() {
  const qc = useQueryClient();
  const [search, setSearch] = useState('');
  const [q, setQ] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<any>(null);
  const [form, setForm] = useState({ judul: '', isi: '', kategori: 'FAQ', sumber: '', tags: '' });
  const [msg, setMsg] = useState('');

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['knowledge', q],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (q) params.set('q', q);
      return (await apiClient<any[]>(`/admin/knowledge?${params}`)).data || [];
    },
  });

  const save = useMutation({
    mutationFn: async () => {
      const body = {
        judul: form.judul,
        isi: form.isi,
        kategori: form.kategori,
        sumber: form.sumber || null,
        tags: form.tags ? form.tags.split(',').map((t) => t.trim()).filter(Boolean) : null,
      };
      if (editing) {
        return apiClient(`/admin/knowledge/${editing.id}`, { method: 'PATCH', body: JSON.stringify(body) });
      }
      return apiClient('/admin/knowledge', { method: 'POST', body: JSON.stringify(body) });
    },
    onSuccess: () => {
      setMsg(editing ? 'Artikel diperbarui' : 'Artikel dibuat');
      setShowForm(false);
      setEditing(null);
      setForm({ judul: '', isi: '', kategori: 'FAQ', sumber: '', tags: '' });
      qc.invalidateQueries({ queryKey: ['knowledge'] });
    },
    onError: (e: any) => setMsg(e.message || 'Gagal menyimpan'),
  });

  const remove = useMutation({
    mutationFn: (id: string) => apiClient(`/admin/knowledge/${id}`, { method: 'DELETE' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['knowledge'] }),
  });

  function openCreate() {
    setEditing(null);
    setForm({ judul: '', isi: '', kategori: 'FAQ', sumber: '', tags: '' });
    setShowForm(true);
    setMsg('');
  }

  function openEdit(a: any) {
    setEditing(a);
    setForm({
      judul: a.judul || '',
      isi: a.preview || '',
      kategori: a.kategori || 'FAQ',
      sumber: a.sumber || '',
      tags: Array.isArray(a.tags) ? a.tags.join(', ') : (a.tags || ''),
    });
    setShowForm(true);
    setMsg('');
  }

  if (isError) return <ErrorState onRetry={() => refetch()} />;

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl font-bold text-gray-800">Pengetahuan</h1>
        <button onClick={openCreate} className="flex items-center gap-2 bg-primary text-white px-4 py-2 rounded-lg text-sm">
          <Plus size={16} /> Artikel Baru
        </button>
      </div>

      {showForm && (
        <Card className="p-4 mb-4 space-y-3">
          <input
            placeholder="Judul *"
            value={form.judul}
            onChange={(e) => setForm({ ...form, judul: e.target.value })}
            className="w-full px-3 py-2 border rounded text-sm"
          />
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <select
              value={form.kategori}
              onChange={(e) => setForm({ ...form, kategori: e.target.value })}
              className="px-3 py-2 border rounded text-sm"
            >
              {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
            <input
              placeholder="Sumber"
              value={form.sumber}
              onChange={(e) => setForm({ ...form, sumber: e.target.value })}
              className="px-3 py-2 border rounded text-sm"
            />
            <input
              placeholder="Tags (pisah koma)"
              value={form.tags}
              onChange={(e) => setForm({ ...form, tags: e.target.value })}
              className="px-3 py-2 border rounded text-sm"
            />
          </div>
          <textarea
            placeholder="Isi artikel *"
            value={form.isi}
            onChange={(e) => setForm({ ...form, isi: e.target.value })}
            rows={5}
            className="w-full px-3 py-2 border rounded text-sm"
          />
          <div className="flex gap-2">
            <button
              disabled={!form.judul || !form.isi || save.isPending}
              onClick={() => save.mutate()}
              className="bg-primary text-white px-6 py-2 rounded-lg text-sm disabled:opacity-50"
            >
              {save.isPending ? 'Menyimpan...' : 'Simpan'}
            </button>
            <button onClick={() => setShowForm(false)} className="px-4 py-2 border rounded-lg text-sm">Batal</button>
            {msg && <span className="text-sm self-center text-gray-500">{msg}</span>}
          </div>
          {editing && (
            <p className="text-xs text-amber-600">
              Catatan: form edit memakai preview; isi ulang konten lengkap jika perlu.
            </p>
          )}
        </Card>
      )}

      <Card className="overflow-hidden">
        <div className="p-3 border-b flex gap-2">
          <div className="relative flex-1">
            <Search size={16} className="absolute left-3 top-2.5 text-gray-400" />
            <input
              placeholder="Cari artikel..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') setQ(search); }}
              className="w-full pl-10 pr-4 py-1.5 border rounded text-sm"
            />
          </div>
          <button onClick={() => setQ(search)} className="px-4 py-1.5 bg-primary text-white rounded text-sm">Cari</button>
        </div>
        {isLoading ? <LoadingState /> : (data || []).length === 0 ? (
          <EmptyState message="Belum ada artikel." />
        ) : (
          <div className="divide-y">
            {(data || []).map((a) => (
              <div key={a.id} className="p-4 hover:bg-gray-50 flex gap-4 justify-between">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="font-medium text-gray-800">{a.judul}</h3>
                    <Badge tone="blue">{a.kategori || '—'}</Badge>
                    {!a.status_aktif && <Badge tone="gray">Nonaktif</Badge>}
                  </div>
                  <p className="text-sm text-gray-500 line-clamp-2">{a.preview}</p>
                  <p className="text-xs text-gray-400 mt-1">{formatDate(a.created_at)}</p>
                </div>
                <div className="flex gap-2 shrink-0">
                  <button onClick={() => openEdit(a)} className="p-2 border rounded hover:bg-white" title="Edit">
                    <Pencil size={14} />
                  </button>
                  <button
                    onClick={() => { if (confirm('Hapus artikel ini?')) remove.mutate(a.id); }}
                    className="p-2 border rounded hover:bg-red-50 text-red-600"
                    title="Hapus"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
