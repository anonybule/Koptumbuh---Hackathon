'use client';
import { useEffect, useState } from 'react';
import { apiClient } from '../../../lib/api';

interface Transaction {
  id: string;
  customer: string;
  total: number;
  status: string;
  method: string;
  date: string;
  sumber?: string | null;
}

export default function TransactionsPage() {
  const [items, setItems] = useState<Transaction[]>([]);
  const [error, setError] = useState(false);

  useEffect(() => {
    apiClient<Transaction[]>('/admin/transactions')
      .then((r) => { if (r.success) setItems(r.data || []); })
      .catch(() => setError(true));
  }, []);

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-800 mb-2">Transaksi</h1>
      <p className="text-sm text-gray-500 mb-6">
        Riwayat penjualan (WhatsApp YA / sistem). Gunakan setelah demo untuk membuktikan commit.
      </p>
      {error && <p className="text-red-500 text-sm mb-4">Gagal memuat transaksi.</p>}
      <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="text-left p-3 font-medium">ID</th>
              <th className="text-left p-3 font-medium">Pelanggan</th>
              <th className="text-right p-3 font-medium">Total</th>
                <th className="text-left p-3 font-medium">Bayar</th>
                <th className="text-left p-3 font-medium">Sumber</th>
                <th className="text-left p-3 font-medium">Status</th>
                <th className="text-left p-3 font-medium">Tanggal</th>
            </tr>
          </thead>
          <tbody>
            {items.map((t) => (
              <tr key={t.id} className="border-b last:border-0 hover:bg-gray-50">
                <td className="p-3 text-xs text-gray-500 font-mono">{t.id}</td>
                <td className="p-3 font-medium">{t.customer || 'Umum'}</td>
                <td className="p-3 text-right font-semibold">Rp {(t.total || 0).toLocaleString('id-ID')}</td>
                <td className="p-3">{t.method}</td>
                <td className="p-3 text-xs text-gray-600">{t.sumber || '—'}</td>
                <td className="p-3">
                  <span className={`px-2 py-1 rounded-full text-xs ${
                    t.status === 'Paid' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'
                  }`}>{t.status}</span>
                </td>
                <td className="p-3 text-gray-500 text-xs">{t.date}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {items.length === 0 && !error && (
          <p className="p-8 text-center text-gray-400">Belum ada transaksi.</p>
        )}
      </div>
    </div>
  );
}
