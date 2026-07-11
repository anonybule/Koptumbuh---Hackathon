'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../../lib/api';
import { formatRp, formatDate } from '../../../lib/format';
import { Card, ErrorState, LoadingState, EmptyState, Tabs, Badge } from '../../../components/ui';
import { Calculator } from 'lucide-react';

interface ShuSummary {
  tahun: number;
  pendapatan: number;
  hpp: number;
  laba_kotor: number;
  beban_operasional: number;
  shu_kotor: number;
  pajak_estimasi: number;
  shu_bersih: number;
  margin_kotor_pct: number;
  margin_shu_pct: number;
  jumlah_transaksi: number;
  hasil: string;
  pools: {
    jasa_anggota: number;
    jasa_modal: number;
    dana_cadangan: number;
    dana_sosial: number;
  };
  formula?: Record<string, string>;
}

interface MonthlyRow {
  bulan?: string;
  total_omzet: number;
  jumlah_transaksi: number;
  hpp?: number;
  beban_operasional?: number;
  estimasi_shu: number;
}

interface MemberShu {
  anggota_ref: string;
  nama: string;
  belanja_ytd: number;
  simpanan_ytd: number;
  jasa_anggota: number;
  jasa_modal: number;
  estimasi_shu: number;
  share_belanja_pct: number;
}

export default function ShuPage() {
  const year = new Date().getFullYear();
  const [tab, setTab] = useState('ringkasan');

  const summary = useQuery({
    queryKey: ['shu-summary', year],
    queryFn: async () => (await apiClient<ShuSummary>(`/admin/shu/summary?year=${year}`)).data!,
  });
  const monthly = useQuery({
    queryKey: ['shu-monthly', year],
    queryFn: async () => (await apiClient<MonthlyRow[]>(`/admin/shu/monthly?year=${year}`)).data || [],
    enabled: tab === 'bulanan',
  });
  const members = useQuery({
    queryKey: ['shu-members', year],
    queryFn: async () =>
      (await apiClient<{ members: MemberShu[]; pools: ShuSummary['pools']; total_allocated: number }>(
        `/admin/shu/members?year=${year}`,
      )).data!,
    enabled: tab === 'anggota',
  });

  if (summary.isError) return <ErrorState onRetry={() => summary.refetch()} />;

  const s = summary.data;
  const hasilTone = s?.hasil === 'PROFIT' ? 'green' : s?.hasil === 'LOSS' ? 'red' : 'yellow';

  return (
    <div>
      <div className="flex flex-wrap items-start justify-between gap-3 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800 flex items-center gap-2">
            <Calculator size={26} className="text-primary" />
            SHU — Sisa Hasil Usaha
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Estimasi real-time tahun {year}: pendapatan − HPP − beban → alokasi ke anggota.
          </p>
        </div>
        <div className="flex gap-2">
          <Link href="/finance" className="px-3 py-2 border rounded-lg text-sm hover:bg-gray-50">Keuangan</Link>
          <Link href="/rat" className="px-3 py-2 border rounded-lg text-sm hover:bg-gray-50">RAT</Link>
        </div>
      </div>

      {summary.isLoading ? (
        <LoadingState />
      ) : (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
            <Card className="p-4">
              <p className="text-xs text-gray-500">Pendapatan YTD</p>
              <p className="text-xl font-bold text-gray-800 mt-1">{formatRp(s?.pendapatan || 0)}</p>
            </Card>
            <Card className="p-4">
              <p className="text-xs text-gray-500">HPP</p>
              <p className="text-xl font-bold text-gray-800 mt-1">{formatRp(s?.hpp || 0)}</p>
            </Card>
            <Card className="p-4">
              <p className="text-xs text-gray-500">SHU bersih</p>
              <p className="text-xl font-bold text-primary mt-1">{formatRp(s?.shu_bersih || 0)}</p>
            </Card>
            <Card className="p-4">
              <p className="text-xs text-gray-500">Hasil</p>
              <div className="mt-2"><Badge tone={hasilTone}>{s?.hasil || '—'}</Badge></div>
              <p className="text-xs text-gray-400 mt-1">Margin {s?.margin_shu_pct ?? 0}%</p>
            </Card>
          </div>

          <Card className="p-4 mb-4">
            <h2 className="text-sm font-semibold text-gray-700 mb-3">Breakdown</h2>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-sm">
              {[
                ['Pendapatan', s?.pendapatan],
                ['− HPP', s?.hpp],
                ['= Laba kotor', s?.laba_kotor],
                ['− Beban ops (8%)', s?.beban_operasional],
                ['= SHU kotor', s?.shu_kotor],
                ['− Pajak est. (2%)', s?.pajak_estimasi],
              ].map(([label, val]) => (
                <div key={String(label)} className="flex justify-between border-b border-gray-50 py-1.5">
                  <span className="text-gray-500">{label}</span>
                  <span className="font-medium">{formatRp(Number(val) || 0)}</span>
                </div>
              ))}
            </div>
            <p className="text-xs text-gray-400 mt-3">
              {s?.jumlah_transaksi || 0} transaksi · margin kotor {s?.margin_kotor_pct ?? 0}%
            </p>
          </Card>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
            {[
              { label: 'Jasa anggota (40%)', value: s?.pools?.jasa_anggota },
              { label: 'Jasa modal (30%)', value: s?.pools?.jasa_modal },
              { label: 'Dana cadangan (20%)', value: s?.pools?.dana_cadangan },
              { label: 'Dana sosial (10%)', value: s?.pools?.dana_sosial },
            ].map((p) => (
              <Card key={p.label} className="p-4">
                <p className="text-xs text-gray-500">{p.label}</p>
                <p className="text-lg font-bold text-gray-800 mt-1">{formatRp(p.value || 0)}</p>
              </Card>
            ))}
          </div>
        </>
      )}

      <Tabs
        tabs={[
          { id: 'ringkasan', label: 'Formula' },
          { id: 'bulanan', label: 'Bulanan' },
          { id: 'anggota', label: 'Per anggota' },
        ]}
        active={tab}
        onChange={setTab}
      />

      {tab === 'ringkasan' && (
        <Card className="p-5">
          <h2 className="font-semibold text-gray-800 mb-2">Cara hitung</h2>
          <ul className="text-sm text-gray-600 space-y-1.5 list-disc pl-5">
            <li>{s?.formula?.pendapatan || 'Pendapatan = omzet penjualan YTD'}</li>
            <li>{s?.formula?.hpp || 'HPP = qty keluar × harga beli terakhir'}</li>
            <li>{s?.formula?.beban || 'Beban operasional estimasi'}</li>
            <li>{s?.formula?.pajak || 'Pajak estimasi'}</li>
            <li>{s?.formula?.alokasi || 'Alokasi ke anggota / modal / cadangan / sosial'}</li>
          </ul>
          <p className="text-xs text-gray-400 mt-4">
            Ini estimasi operasional harian — angka resmi tetap dari laporan RAT tahunan.
          </p>
        </Card>
      )}

      {tab === 'bulanan' && (
        <Card className="overflow-hidden">
          {monthly.isLoading ? <LoadingState /> : monthly.isError ? (
            <ErrorState onRetry={() => monthly.refetch()} />
          ) : (monthly.data || []).length === 0 ? (
            <EmptyState message="Belum ada data bulanan." />
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="text-left p-3">Bulan</th>
                  <th className="text-right p-3">Omzet</th>
                  <th className="text-right p-3">HPP</th>
                  <th className="text-right p-3">Beban</th>
                  <th className="text-right p-3">TX</th>
                  <th className="text-right p-3">Estimasi SHU</th>
                </tr>
              </thead>
              <tbody>
                {(monthly.data || []).map((r, i) => (
                  <tr key={i} className="border-b last:border-0">
                    <td className="p-3">{formatDate(r.bulan)}</td>
                    <td className="p-3 text-right">{formatRp(r.total_omzet)}</td>
                    <td className="p-3 text-right">{formatRp(r.hpp || 0)}</td>
                    <td className="p-3 text-right">{formatRp(r.beban_operasional || 0)}</td>
                    <td className="p-3 text-right">{r.jumlah_transaksi}</td>
                    <td className="p-3 text-right font-semibold">{formatRp(r.estimasi_shu)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      )}

      {tab === 'anggota' && (
        <Card className="overflow-hidden">
          {members.isLoading ? <LoadingState /> : members.isError ? (
            <ErrorState onRetry={() => members.refetch()} />
          ) : (members.data?.members || []).length === 0 ? (
            <EmptyState message="Belum ada alokasi anggota." />
          ) : (
            <>
              <div className="px-4 py-3 border-b bg-gray-50 text-xs text-gray-500">
                Alokasi dari pool jasa anggota + jasa modal. Total dialokasikan:{' '}
                <strong>{formatRp(members.data?.total_allocated || 0)}</strong>
              </div>
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b">
                  <tr>
                    <th className="text-left p-3">Anggota</th>
                    <th className="text-right p-3">Belanja YTD</th>
                    <th className="text-right p-3">Simpanan</th>
                    <th className="text-right p-3">Jasa belanja</th>
                    <th className="text-right p-3">Jasa modal</th>
                    <th className="text-right p-3">Estimasi SHU</th>
                  </tr>
                </thead>
                <tbody>
                  {(members.data?.members || []).map((m) => (
                    <tr key={m.anggota_ref} className="border-b last:border-0 hover:bg-gray-50">
                      <td className="p-3 font-medium">
                        {m.nama}
                        <span className="block text-[11px] text-gray-400">{m.share_belanja_pct}% belanja</span>
                      </td>
                      <td className="p-3 text-right">{formatRp(m.belanja_ytd)}</td>
                      <td className="p-3 text-right">{formatRp(m.simpanan_ytd)}</td>
                      <td className="p-3 text-right">{formatRp(m.jasa_anggota)}</td>
                      <td className="p-3 text-right">{formatRp(m.jasa_modal)}</td>
                      <td className="p-3 text-right font-semibold text-primary">{formatRp(m.estimasi_shu)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
        </Card>
      )}
    </div>
  );
}
