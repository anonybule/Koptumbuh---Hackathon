'use client';

import { useQuery } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { apiClient, clearTokens } from '../../../lib/api';
import { Card, LoadingState } from '../../../components/ui';

export default function SettingsPage() {
  const router = useRouter();
  const profile = useQuery({
    queryKey: ['settings-users'],
    queryFn: async () => (await apiClient<any[]>('/admin/users')).data || [],
    retry: false,
  });

  const me = (profile.data || [])[0];

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
            {profile.isLoading ? <LoadingState /> : (
              <p className="text-sm text-gray-400">
                {me?.nama || me?.name || 'Operator'} • {me?.role || 'OPERATOR'}
              </p>
            )}
          </div>
        </div>
        <div className="p-4 flex justify-between items-center">
          <div>
            <p className="font-medium">Koperasi</p>
            <p className="text-sm text-gray-400">{me?.koperasi_ref || 'KOP-JasaAI-A1B2C3D4E5F6'}</p>
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
