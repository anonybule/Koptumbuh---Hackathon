'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../../lib/api';
import { Card, ErrorState, LoadingState, EmptyState, Badge } from '../../../components/ui';
import { Search } from 'lucide-react';

interface Cooperative {
  koperasi_ref: string;
  nama_koperasi: string;
  status_registrasi?: string;
  bentuk_koperasi?: string;
  kategori_usaha?: string;
  nik_koperasi?: string;
  alamat?: string;
  kode_wilayah?: string;
}

export default function CooperativesPage() {
  const [search, setSearch] = useState('');
  const [q, setQ] = useState('');

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['cooperatives', q],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (q) params.set('q', q);
      return (await apiClient<Cooperative[]>(`/admin/cooperatives?${params}`)).data || [];
    },
  });

  if (isError) return <ErrorState onRetry={() => refetch()} />;

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-800 mb-6">Koperasi</h1>
      <Card className="overflow-hidden">
        <div className="p-3 border-b flex gap-2">
          <div className="relative flex-1">
            <Search size={16} className="absolute left-3 top-2.5 text-gray-400" />
            <input
              placeholder="Cari nama / NIK / ref..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') setQ(search); }}
              className="w-full pl-10 pr-4 py-1.5 border rounded text-sm"
            />
          </div>
          <button onClick={() => setQ(search)} className="px-4 py-1.5 bg-primary text-white rounded text-sm">Cari</button>
        </div>
        {isLoading ? <LoadingState /> : (data || []).length === 0 ? (
          <EmptyState message="Tidak ada data koperasi." />
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="text-left p-3 font-medium">Nama</th>
                <th className="text-left p-3 font-medium">Bentuk</th>
                <th className="text-left p-3 font-medium">Kategori</th>
                <th className="text-left p-3 font-medium">Status</th>
                <th className="text-left p-3 font-medium">Alamat</th>
              </tr>
            </thead>
            <tbody>
              {(data || []).map((c) => (
                <tr key={c.koperasi_ref} className="border-b last:border-0 hover:bg-gray-50">
                  <td className="p-3">
                    <Link
                      href={`/cooperatives/${encodeURIComponent(c.koperasi_ref)}`}
                      className="font-medium text-primary hover:underline"
                    >
                      {c.nama_koperasi}
                    </Link>
                    <p className="text-xs text-gray-400 font-mono">{c.koperasi_ref}</p>
                  </td>
                  <td className="p-3">{c.bentuk_koperasi || '—'}</td>
                  <td className="p-3">{c.kategori_usaha || '—'}</td>
                  <td className="p-3">
                    <Badge tone={c.status_registrasi === 'Approved' ? 'green' : 'gray'}>
                      {c.status_registrasi || '—'}
                    </Badge>
                  </td>
                  <td className="p-3 text-xs text-gray-500 max-w-xs truncate">{c.alamat || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
