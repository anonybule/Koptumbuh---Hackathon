'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../../lib/api';
import { formatDate } from '../../../lib/format';
import { Card, ErrorState, LoadingState, EmptyState, Badge } from '../../../components/ui';
import { Plus } from 'lucide-react';

const ROLES = ['OPERATOR', 'KETUA', 'BENDAHARA', 'PEMBINA', 'ADMIN', 'ANGGOTA'];

export default function UsersPage() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    nama: '',
    nomor_whatsapp: '',
    role: 'OPERATOR',
    pengurus_ref: '',
    karyawan_ref: '',
  });
  const [msg, setMsg] = useState('');

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['users'],
    queryFn: async () => (await apiClient<any[]>('/admin/users')).data || [],
  });

  const create = useMutation({
    mutationFn: async () => {
      const body: any = {
        nama: form.nama,
        nomor_whatsapp: form.nomor_whatsapp,
        role: form.role,
      };
      if (form.pengurus_ref) body.pengurus_ref = form.pengurus_ref;
      if (form.karyawan_ref) body.karyawan_ref = form.karyawan_ref;
      return apiClient('/admin/users', { method: 'POST', body: JSON.stringify(body) });
    },
    onSuccess: () => {
      setMsg('Pengguna dibuat');
      setShowForm(false);
      setForm({ nama: '', nomor_whatsapp: '', role: 'OPERATOR', pengurus_ref: '', karyawan_ref: '' });
      qc.invalidateQueries({ queryKey: ['users'] });
    },
    onError: (e: any) => setMsg(e.message || 'Gagal membuat pengguna'),
  });

  const patch = useMutation({
    mutationFn: async ({ id, body }: { id: string; body: any }) =>
      apiClient(`/admin/users/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['users'] }),
  });

  if (isError) return <ErrorState onRetry={() => refetch()} />;

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl font-bold text-gray-800">Pengguna</h1>
        <button
          onClick={() => { setShowForm(!showForm); setMsg(''); }}
          className="flex items-center gap-2 bg-primary text-white px-4 py-2 rounded-lg text-sm"
        >
          <Plus size={16} /> Tambah Pengguna
        </button>
      </div>

      {showForm && (
        <Card className="p-4 mb-4 grid grid-cols-1 md:grid-cols-3 gap-3">
          <input
            placeholder="Nama *"
            value={form.nama}
            onChange={(e) => setForm({ ...form, nama: e.target.value })}
            className="px-3 py-2 border rounded text-sm"
          />
          <input
            placeholder="Nomor WhatsApp *"
            value={form.nomor_whatsapp}
            onChange={(e) => setForm({ ...form, nomor_whatsapp: e.target.value })}
            className="px-3 py-2 border rounded text-sm"
          />
          <select
            value={form.role}
            onChange={(e) => setForm({ ...form, role: e.target.value })}
            className="px-3 py-2 border rounded text-sm"
          >
            {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
          <input
            placeholder="pengurus_ref (opsional)"
            value={form.pengurus_ref}
            onChange={(e) => setForm({ ...form, pengurus_ref: e.target.value })}
            className="px-3 py-2 border rounded text-sm"
          />
          <input
            placeholder="karyawan_ref (opsional)"
            value={form.karyawan_ref}
            onChange={(e) => setForm({ ...form, karyawan_ref: e.target.value })}
            className="px-3 py-2 border rounded text-sm"
          />
          <div className="flex gap-2 items-center">
            <button
              disabled={!form.nama || !form.nomor_whatsapp || create.isPending}
              onClick={() => create.mutate()}
              className="bg-primary text-white px-6 py-2 rounded-lg text-sm disabled:opacity-50"
            >
              Simpan
            </button>
            {msg && <span className="text-sm text-gray-500">{msg}</span>}
          </div>
        </Card>
      )}

      <Card className="overflow-hidden">
        {isLoading ? <LoadingState /> : (data || []).length === 0 ? (
          <EmptyState message="Belum ada pengguna." />
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="text-left p-3 font-medium">Nama</th>
                <th className="text-left p-3 font-medium">WhatsApp</th>
                <th className="text-left p-3 font-medium">Role</th>
                <th className="text-left p-3 font-medium">Status</th>
                <th className="text-left p-3 font-medium">Dibuat</th>
                <th className="text-right p-3 font-medium">Aksi</th>
              </tr>
            </thead>
            <tbody>
              {(data || []).map((u) => (
                <tr key={u.id} className="border-b last:border-0 hover:bg-gray-50">
                  <td className="p-3 font-medium">{u.nama}</td>
                  <td className="p-3">{u.nomor_whatsapp}</td>
                  <td className="p-3">
                    <select
                      value={u.role}
                      onChange={(e) => patch.mutate({ id: u.id, body: { role: e.target.value } })}
                      className="px-2 py-1 border rounded text-xs"
                    >
                      {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
                    </select>
                  </td>
                  <td className="p-3">
                    <Badge tone={u.status_aktif ? 'green' : 'red'}>
                      {u.status_aktif ? 'Aktif' : 'Nonaktif'}
                    </Badge>
                  </td>
                  <td className="p-3 text-xs text-gray-500">{formatDate(u.created_at)}</td>
                  <td className="p-3 text-right">
                    <button
                      onClick={() =>
                        patch.mutate({ id: u.id, body: { status_aktif: !u.status_aktif } })
                      }
                      className="text-xs text-primary hover:underline"
                    >
                      {u.status_aktif ? 'Nonaktifkan' : 'Aktifkan'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
