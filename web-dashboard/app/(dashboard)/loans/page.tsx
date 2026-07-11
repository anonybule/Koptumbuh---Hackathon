'use client';

import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../../lib/api';
import { formatRp } from '../../../lib/format';
import { Card, ErrorState, LoadingState } from '../../../components/ui';

interface Loan {
  id: string;
  anggota_ref: string;
  anggota_nama?: string;
  jumlah_pinjaman: number;
  tenor_bulan: number;
  bunga_persen: number;
  angsuran_per_bulan?: number;
  status: string;
  tanggal_mulai?: string;
  tanggal_jatuh_tempo?: string;
}

export default function LoansPage() {
  const qc = useQueryClient();
  const [anggota, setAnggota] = useState('');
  const [jumlah, setJumlah] = useState('');
  const [tenor, setTenor] = useState('6');
  const [bunga, setBunga] = useState('0');
  const [formError, setFormError] = useState('');

  const loans = useQuery({
    queryKey: ['loans'],
    queryFn: async () => (await apiClient<Loan[]>('/admin/loans')).data || [],
  });

  const create = useMutation({
    mutationFn: async () => {
      setFormError('');
      return apiClient('/admin/loans', {
        method: 'POST',
        body: JSON.stringify({
          anggota_ref: anggota.trim(),
          jumlah_pinjaman: Number(jumlah),
          tenor_bulan: Number(tenor),
          bunga_persen: Number(bunga) || 0,
        }),
      });
    },
    onSuccess: () => {
      setAnggota('');
      setJumlah('');
      qc.invalidateQueries({ queryKey: ['loans'] });
    },
    onError: (e: Error) => setFormError(e.message),
  });

  const patch = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      apiClient(`/admin/loans/${id}`, { method: 'PATCH', body: JSON.stringify({ status }) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['loans'] }),
  });

  const stats = useMemo(() => {
    const rows = loans.data || [];
    const aktif = rows.filter((l) => l.status === 'AKTIF');
    return {
      total: rows.length,
      aktif: aktif.length,
      outstanding: aktif.reduce((s, l) => s + (l.jumlah_pinjaman || 0), 0),
    };
  }, [loans.data]);

  if (loans.isError) {
    return <ErrorState onRetry={() => loans.refetch()} />;
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-800 mb-6">Pinjaman</h1>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <Card className="p-4"><p className="text-sm text-gray-500">Total Pinjaman</p><p className="text-xl font-bold">{stats.total}</p></Card>
        <Card className="p-4"><p className="text-sm text-gray-500">Aktif</p><p className="text-xl font-bold">{stats.aktif}</p></Card>
        <Card className="p-4"><p className="text-sm text-gray-500">Outstanding</p><p className="text-xl font-bold">{formatRp(stats.outstanding)}</p></Card>
      </div>

      <Card className="p-4 mb-6">
        <h2 className="font-semibold mb-3">Pinjaman Baru</h2>
        <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
          <input className="border rounded-lg px-3 py-2 text-sm" placeholder="anggota_ref" value={anggota} onChange={(e) => setAnggota(e.target.value)} />
          <input className="border rounded-lg px-3 py-2 text-sm" placeholder="Jumlah" type="number" value={jumlah} onChange={(e) => setJumlah(e.target.value)} />
          <input className="border rounded-lg px-3 py-2 text-sm" placeholder="Tenor (bulan)" type="number" value={tenor} onChange={(e) => setTenor(e.target.value)} />
          <input className="border rounded-lg px-3 py-2 text-sm" placeholder="Bunga %" type="number" value={bunga} onChange={(e) => setBunga(e.target.value)} />
          <button
            type="button"
            disabled={create.isPending || !anggota || !jumlah}
            onClick={() => create.mutate()}
            className="bg-primary text-white rounded-lg text-sm font-medium hover:opacity-90 disabled:opacity-50"
          >
            {create.isPending ? 'Menyimpan…' : 'Simpan'}
          </button>
        </div>
        {formError && <p className="text-sm text-red-600 mt-2">{formError}</p>}
      </Card>

      <Card className="overflow-hidden">
        {loans.isLoading ? <LoadingState /> : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="text-left p-3">Anggota</th>
                <th className="text-left p-3">Jumlah</th>
                <th className="text-left p-3">Tenor</th>
                <th className="text-left p-3">Status</th>
                <th className="text-left p-3">Aksi</th>
              </tr>
            </thead>
            <tbody>
              {(loans.data || []).map((l) => (
                <tr key={l.id} className="border-b">
                  <td className="p-3">{l.anggota_nama || l.anggota_ref}</td>
                  <td className="p-3">{formatRp(l.jumlah_pinjaman)}</td>
                  <td className="p-3">{l.tenor_bulan} bln</td>
                  <td className="p-3"><span className="px-2 py-0.5 rounded-full text-xs bg-gray-100">{l.status}</span></td>
                  <td className="p-3 space-x-2">
                    {l.status === 'AKTIF' && (
                      <>
                        <button type="button" className="text-primary text-xs" onClick={() => patch.mutate({ id: l.id, status: 'LUNAS' })}>Lunas</button>
                        <button type="button" className="text-red-600 text-xs" onClick={() => patch.mutate({ id: l.id, status: 'MACET' })}>Macet</button>
                      </>
                    )}
                  </td>
                </tr>
              ))}
              {(loans.data || []).length === 0 && (
                <tr><td colSpan={5} className="p-8 text-center text-gray-400">Belum ada pinjaman.</td></tr>
              )}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
