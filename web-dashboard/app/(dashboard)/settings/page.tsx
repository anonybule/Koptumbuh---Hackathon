'use client';

import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { apiClient, clearTokens, getAccessToken } from '../../../lib/api';
import { Card, LoadingState } from '../../../components/ui';

function decodeJwtPayload(token: string | null): Record<string, unknown> | null {
  if (!token) return null;
  try {
    const part = token.split('.')[1];
    if (!part) return null;
    const json = atob(part.replace(/-/g, '+').replace(/_/g, '/'));
    return JSON.parse(json);
  } catch {
    return null;
  }
}

export default function SettingsPage() {
  const router = useRouter();
  const claims = useMemo(() => decodeJwtPayload(getAccessToken()), []);

  const profile = useQuery({
    queryKey: ['settings-users'],
    queryFn: async () => (await apiClient<any[]>('/admin/users')).data || [],
    retry: false,
  });

  const sub = typeof claims?.sub === 'string' ? claims.sub : null;
  const meFromList = (profile.data || []).find((u: any) => String(u.id || u.pengguna_id) === sub);
  const nama = meFromList?.nama || meFromList?.name || 'Operator';
  const role = (meFromList?.role as string) || (claims?.role as string) || 'OPERATOR';
  const koperasi =
    (meFromList?.koperasi_ref as string) ||
    (claims?.koperasi_ref as string) ||
    'KOP-JasaAI-A1B2C3D4E5F6';

  const handleLogout = () => {
    clearTokens();
    router.push('/login');
  };

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-800 mb-6">Settings</h1>
      <Card className="divide-y">
        <div className="p-4 flex justify-between items-center">
          <div>
            <p className="font-medium">Profil</p>
            {profile.isLoading && !claims ? (
              <LoadingState />
            ) : (
              <p className="text-sm text-gray-400">
                {nama} • {role}
              </p>
            )}
          </div>
        </div>
        <div className="p-4 flex justify-between items-center">
          <div>
            <p className="font-medium">Koperasi</p>
            <p className="text-sm text-gray-400">{koperasi}</p>
          </div>
        </div>
        <div className="p-4 flex justify-between items-center">
          <div>
            <p className="font-medium">Printer</p>
            <p className="text-sm text-gray-400">Thermal receipt — setup di perangkat lokal</p>
          </div>
        </div>
        <div className="p-4">
          <button onClick={handleLogout} className="w-full py-3 bg-red-500 text-white rounded-lg font-semibold hover:bg-red-600">
            Keluar
          </button>
        </div>
      </Card>
    </div>
  );
}
