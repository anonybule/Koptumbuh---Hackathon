'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../../lib/api';
import { formatDate } from '../../../lib/format';
import { Card, ErrorState, LoadingState, EmptyState, Badge } from '../../../components/ui';
import { Search } from 'lucide-react';

interface Member {
  id: string;
  name: string;
  gender?: string;
  status?: string;
  registered?: string;
  nik?: string;
  pekerjaan?: string;
}

export default function MembersPage() {
  const [search, setSearch] = useState('');
  const [q, setQ] = useState('');

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['members', q],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (q) params.set('q', q);
      return (await apiClient<Member[]>(`/admin/members?${params}`)).data || [];
    },
  });

  if (isError) return <ErrorState onRetry={() => refetch()} />;

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-800 mb-6">Anggota</h1>
      <Card className="overflow-hidden">
        <div className="p-3 border-b flex gap-2">
          <div className="relative flex-1">
            <Search size={16} className="absolute left-3 top-2.5 text-gray-400" />
            <input
              placeholder="Cari nama / NIK..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') setQ(search); }}
              className="w-full pl-10 pr-4 py-1.5 border rounded text-sm"
            />
          </div>
          <button onClick={() => setQ(search)} className="px-4 py-1.5 bg-primary text-white rounded text-sm">Cari</button>
        </div>
        {isLoading ? <LoadingState /> : (data || []).length === 0 ? (
          <EmptyState message="Belum ada anggota." />
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="text-left p-3 font-medium">Nama</th>
                <th className="text-left p-3 font-medium">JK</th>
                <th className="text-left p-3 font-medium">Pekerjaan</th>
                <th className="text-left p-3 font-medium">Status</th>
                <th className="text-left p-3 font-medium">Terdaftar</th>
              </tr>
            </thead>
            <tbody>
              {(data || []).map((m) => (
                <tr key={m.id} className="border-b last:border-0 hover:bg-gray-50">
                  <td className="p-3">
                    <Link href={`/members/${encodeURIComponent(m.id)}`} className="font-medium text-primary hover:underline">
                      {m.name}
                    </Link>
                  </td>
                  <td className="p-3">{m.gender || '—'}</td>
                  <td className="p-3 text-gray-500">{m.pekerjaan || '—'}</td>
                  <td className="p-3">
                    <Badge tone={m.status === 'Approved' ? 'green' : 'gray'}>{m.status || '—'}</Badge>
                  </td>
                  <td className="p-3 text-gray-500 text-xs">{formatDate(m.registered)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
