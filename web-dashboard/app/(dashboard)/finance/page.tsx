'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../../lib/api';
import { formatRp, formatDate } from '../../../lib/format';
import { Card, ErrorState, LoadingState, Tabs, EmptyState, Badge } from '../../../components/ui';

export default function FinancePage() {
  const [tab, setTab] = useState('shu');
  const year = new Date().getFullYear();

  const shu = useQuery({
    queryKey: ['finance-shu', year],
    queryFn: async () => (await apiClient<any>(`/admin/shu/summary?year=${year}`)).data,
    enabled: tab === 'shu',
  });

  const bank = useQuery({
    queryKey: ['finance-bank'],
    queryFn: async () => (await apiClient<any[]>('/admin/finance/bank-accounts')).data || [],
    enabled: tab === 'bank',
  });
  const capital = useQuery({
    queryKey: ['finance-capital'],
    queryFn: async () => (await apiClient<any[]>('/admin/finance/capital')).data || [],
    enabled: tab === 'capital',
  });
  const appsBank = useQuery({
    queryKey: ['apps-bank'],
    queryFn: async () => (await apiClient<any[]>('/admin/applications/bank-account')).data || [],
    enabled: tab === 'apps',
  });
  const appsFin = useQuery({
    queryKey: ['apps-fin'],
    queryFn: async () => (await apiClient<any[]>('/admin/applications/financing')).data || [],
    enabled: tab === 'apps',
  });
  const appsPart = useQuery({
    queryKey: ['apps-part'],
    queryFn: async () => (await apiClient<any[]>('/admin/applications/partnership')).data || [],
    enabled: tab === 'apps',
  });
  const appsDom = useQuery({
    queryKey: ['apps-dom'],
    queryFn: async () => (await apiClient<any[]>('/admin/applications/domain')).data || [],
    enabled: tab === 'apps',
  });

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
        <h1 className="text-2xl font-bold text-gray-800">Keuangan</h1>
        <Link href="/shu" className="text-sm text-primary hover:underline">Buka halaman SHU lengkap →</Link>
      </div>
      <Tabs
        tabs={[
          { id: 'shu', label: 'SHU' },
          { id: 'bank', label: 'Rekening Bank' },
          { id: 'capital', label: 'Modal' },
          { id: 'apps', label: 'Pengajuan' },
        ]}
        active={tab}
        onChange={setTab}
      />

      {tab === 'shu' && (
        <Card className="p-5">
          {shu.isError ? <ErrorState onRetry={() => shu.refetch()} /> :
           shu.isLoading ? <LoadingState /> : (
            <div>
              <div className="flex flex-wrap items-center gap-2 mb-4">
                <Badge tone={shu.data?.hasil === 'PROFIT' ? 'green' : 'red'}>{shu.data?.hasil}</Badge>
                <span className="text-sm text-gray-500">Tahun {shu.data?.tahun}</span>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
                <div>
                  <p className="text-xs text-gray-500">Pendapatan</p>
                  <p className="font-bold">{formatRp(shu.data?.pendapatan || 0)}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">HPP</p>
                  <p className="font-bold">{formatRp(shu.data?.hpp || 0)}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">SHU bersih</p>
                  <p className="font-bold text-primary">{formatRp(shu.data?.shu_bersih || 0)}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Margin</p>
                  <p className="font-bold">{shu.data?.margin_shu_pct ?? 0}%</p>
                </div>
              </div>
              <p className="text-sm text-gray-600 mb-3">
                Alokasi: jasa anggota {formatRp(shu.data?.pools?.jasa_anggota || 0)} · jasa modal{' '}
                {formatRp(shu.data?.pools?.jasa_modal || 0)} · cadangan{' '}
                {formatRp(shu.data?.pools?.dana_cadangan || 0)} · sosial{' '}
                {formatRp(shu.data?.pools?.dana_sosial || 0)}
              </p>
              <Link href="/shu" className="text-sm font-medium text-primary hover:underline">
                Lihat breakdown bulanan & per anggota →
              </Link>
            </div>
           )}
        </Card>
      )}

      {tab === 'bank' && (
        <Card className="overflow-hidden">
          {bank.isError ? <ErrorState onRetry={() => bank.refetch()} /> :
           bank.isLoading ? <LoadingState /> :
           (bank.data || []).length === 0 ? <EmptyState message="Belum ada rekening bank." /> : (
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b"><tr>
                <th className="text-left p-3 font-medium">Bank</th>
                <th className="text-left p-3 font-medium">Nama Rekening</th>
                <th className="text-left p-3 font-medium">Dibuat</th>
              </tr></thead>
              <tbody>
                {(bank.data || []).map((r) => (
                  <tr key={r.akun_bank_ref} className="border-b last:border-0">
                    <td className="p-3 font-medium">{r.nama_bank}</td>
                    <td className="p-3">{r.nama_rekening}</td>
                    <td className="p-3 text-xs text-gray-500">{formatDate(r.created)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      )}

      {tab === 'capital' && (
        <Card className="overflow-hidden">
          {capital.isError ? <ErrorState onRetry={() => capital.refetch()} /> :
           capital.isLoading ? <LoadingState /> :
           (capital.data || []).length === 0 ? <EmptyState message="Belum ada data modal." /> : (
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b"><tr>
                <th className="text-left p-3 font-medium">Sumber</th>
                <th className="text-left p-3 font-medium">Tipe</th>
                <th className="text-right p-3 font-medium">Jumlah</th>
                <th className="text-left p-3 font-medium">Tanggal</th>
              </tr></thead>
              <tbody>
                {(capital.data || []).map((r) => (
                  <tr key={r.modal_ref} className="border-b last:border-0">
                    <td className="p-3 font-medium">{r.nama_sumber || r.tipe_sumber}</td>
                    <td className="p-3">{r.tipe_modal || '—'}</td>
                    <td className="p-3 text-right font-semibold">{formatRp(r.jumlah)}</td>
                    <td className="p-3 text-xs">{formatDate(r.tanggal_diterima)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      )}

      {tab === 'apps' && (
        <div className="space-y-6">
          {[
            { title: 'Pengajuan Rekening Bank', q: appsBank, cols: ['penanggung_jawab', 'nama_bank', 'status'] },
            { title: 'Pengajuan Pembiayaan', q: appsFin, cols: ['penanggung_jawab', 'nominal', 'status'] },
            { title: 'Pengajuan Kemitraan', q: appsPart, cols: ['penanggung_jawab', 'tipe_kemitraan', 'status'] },
            { title: 'Pengajuan Domain', q: appsDom, cols: ['domain', 'status_verifikasi', 'status_domain'] },
          ].map((section) => (
            <Card key={section.title} className="overflow-hidden">
              <div className="p-4 border-b"><h2 className="font-semibold">{section.title}</h2></div>
              {section.q.isError ? <ErrorState onRetry={() => section.q.refetch()} /> :
               section.q.isLoading ? <LoadingState /> :
               (section.q.data || []).length === 0 ? <EmptyState message="Tidak ada pengajuan." /> : (
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 border-b">
                    <tr>
                      {section.cols.map((c) => (
                        <th key={c} className="text-left p-3 font-medium capitalize">{c.replace(/_/g, ' ')}</th>
                      ))}
                      <th className="text-left p-3 font-medium">Dibuat</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(section.q.data || []).map((r: any) => (
                      <tr key={r.id} className="border-b last:border-0">
                        {section.cols.map((c) => (
                          <td key={c} className="p-3">
                            {c === 'nominal' ? formatRp(r[c]) :
                             c.includes('status') ? <Badge>{r[c] || '—'}</Badge> :
                             r[c] || '—'}
                          </td>
                        ))}
                        <td className="p-3 text-xs text-gray-500">{formatDate(r.created)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
