'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { apiClient } from '../../../lib/api';
import { Plus, Minus, ShoppingCart, Zap } from 'lucide-react';

interface InventoryItem {
  id: string;
  name: string;
  stock: number;
  barcode?: string;
}

interface CartLine {
  id: string;
  name: string;
  qty: number;
  stock: number;
}

export default function PosPage() {
  const [items, setItems] = useState<InventoryItem[]>([]);
  const [cart, setCart] = useState<CartLine[]>([]);
  const [customer, setCustomer] = useState('Umum');
  const [payment, setPayment] = useState('Cash');
  const [error, setError] = useState(false);
  const [note, setNote] = useState('');
  const [lastTx, setLastTx] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function loadInventory() {
    try {
      const r = await apiClient<InventoryItem[]>('/admin/inventory?per_page=100');
      if (r.success) {
        setItems(r.data || []);
        setError(false);
      } else setError(true);
    } catch {
      setError(true);
    }
  }

  useEffect(() => { loadInventory(); }, []);

  function addToCart(item: InventoryItem) {
    setCart((prev) => {
      const existing = prev.find((l) => l.id === item.id);
      if (existing) {
        if (existing.qty >= item.stock) return prev;
        return prev.map((l) => l.id === item.id ? { ...l, qty: l.qty + 1 } : l);
      }
      if (item.stock <= 0) return prev;
      return [...prev, { id: item.id, name: item.name, qty: 1, stock: item.stock }];
    });
  }

  function changeQty(id: string, delta: number) {
    setCart((prev) => prev
      .map((l) => l.id === id ? { ...l, qty: Math.max(0, Math.min(l.stock, l.qty + delta)) } : l)
      .filter((l) => l.qty > 0));
  }

  function buildWhatsAppDraft() {
    if (cart.length === 0) {
      setNote('Tambah produk ke keranjang dulu.');
      return;
    }
    const lines = cart.map((l) => `${l.qty} ${l.name}`).join(', ');
    const draft = `${customer} beli ${lines}, bayar ${payment.toLowerCase()}`;
    navigator.clipboard?.writeText(draft).catch(() => {});
    setNote(`Draft disalin: "${draft}" — kirim via WhatsApp, lalu balas YA.`);
  }

  async function commitSale(lines?: CartLine[], cust?: string, pay?: string) {
    const useCart = lines || cart;
    const useCustomer = cust ?? customer;
    const usePay = pay ?? payment;
    if (useCart.length === 0) {
      setNote('Keranjang kosong.');
      return;
    }
    setSaving(true);
    setNote('');
    setLastTx(null);
    try {
      const r = await apiClient<{ id?: string; transaksi_sample_id?: string }>('/admin/pos/transactions', {
        method: 'POST',
        body: JSON.stringify({
          customer_name: useCustomer || 'Umum',
          payment_method: usePay,
          line_items: useCart.map((l) => ({ produk_sample_id: l.id, quantity: l.qty })),
        }),
      });
      if (r.success) {
        const txId = (r.data as any)?.transaksi_sample_id || (r.data as any)?.id || 'OK';
        setCart([]);
        setLastTx(String(txId));
        setNote(`Transaksi tersimpan: ${txId}`);
        await loadInventory();
      } else {
        setNote('Gagal menyimpan transaksi.');
      }
    } catch (e: any) {
      setNote(e?.message || 'Gagal menyimpan transaksi.');
    } finally {
      setSaving(false);
    }
  }

  async function demoOneClick() {
    const first = items.find((i) => i.stock >= 1);
    if (!first) {
      setNote('Tidak ada produk berstok. Cek seed / inventaris.');
      return;
    }
    setCustomer('Demo Juri');
    setPayment('Cash');
    const line = [{ id: first.id, name: first.name, qty: 1, stock: first.stock }];
    setCart(line);
    await commitSale(line, 'Demo Juri', 'Cash');
  }

  return (
    <div>
      <div className="flex flex-wrap items-start justify-between gap-3 mb-2">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">POS Kasir</h1>
          <p className="text-sm text-gray-500 mt-1">
            Fallback demo tanpa WhatsApp — commit langsung ke ledger + stok.
          </p>
        </div>
        <button
          type="button"
          disabled={saving || items.length === 0}
          onClick={demoOneClick}
          className="flex items-center gap-2 px-4 py-2.5 bg-accent text-white rounded-lg text-sm font-semibold hover:opacity-90 disabled:opacity-50 shadow-sm"
          style={{ backgroundColor: '#a0ba3b' }}
        >
          <Zap size={16} />
          Demo 1-klik
        </button>
      </div>

      {error && (
        <p className="text-red-500 text-sm mb-4">
          Gagal memuat inventaris. Pastikan API hidup (`curl localhost:8000/health`).
        </p>
      )}

      {lastTx && (
        <div className="mb-4 p-4 rounded-xl border border-green-200 bg-green-50 text-sm">
          <p className="font-semibold text-green-800">Demo sale OK — {lastTx}</p>
          <p className="text-green-700 mt-1">Buka dashboard dan klik Refresh untuk lihat KPI &amp; transaksi terbaru.</p>
          <div className="flex flex-wrap gap-3 mt-3">
            <Link href="/" className="text-primary font-medium hover:underline">→ Dashboard</Link>
            <Link href="/transactions" className="text-primary font-medium hover:underline">→ Riwayat transaksi</Link>
            <Link href="/inventory" className="text-primary font-medium hover:underline">→ Inventaris</Link>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-white rounded-xl shadow-sm border overflow-hidden">
          <div className="p-4 border-b font-medium text-gray-800 flex justify-between">
            <span>Produk</span>
            <button type="button" onClick={loadInventory} className="text-xs text-primary hover:underline">Muat ulang</button>
          </div>
          <div className="divide-y max-h-[520px] overflow-auto">
            {items.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => addToCart(item)}
                disabled={item.stock <= 0}
                className="w-full text-left p-4 hover:bg-gray-50 disabled:opacity-40 flex items-center justify-between"
              >
                <div>
                  <p className="font-medium text-gray-800">{item.name}</p>
                  <p className="text-xs text-gray-400">{item.barcode || item.id}</p>
                </div>
                <span className={`text-sm font-semibold ${item.stock < 5 ? 'text-red-600' : 'text-gray-600'}`}>
                  Stok {item.stock}
                </span>
              </button>
            ))}
            {items.length === 0 && !error && (
              <p className="p-8 text-center text-gray-400">Loading produk…</p>
            )}
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm border p-4 h-fit">
          <div className="flex items-center gap-2 mb-4">
            <ShoppingCart size={18} className="text-primary" />
            <h2 className="font-semibold text-gray-800">Keranjang</h2>
          </div>

          <label className="block text-xs text-gray-500 mb-1">Pelanggan</label>
          <input
            value={customer}
            onChange={(e) => setCustomer(e.target.value)}
            className="w-full mb-3 px-3 py-2 border rounded-lg text-sm outline-none focus:ring-2 focus:ring-primary"
          />

          <label className="block text-xs text-gray-500 mb-1">Pembayaran</label>
          <select
            value={payment}
            onChange={(e) => setPayment(e.target.value)}
            className="w-full mb-4 px-3 py-2 border rounded-lg text-sm outline-none focus:ring-2 focus:ring-primary"
          >
            <option value="Cash">Tunai</option>
            <option value="Transfer">Transfer</option>
            <option value="Hutang">Hutang</option>
          </select>

          {cart.length === 0 ? (
            <p className="text-sm text-gray-400 mb-4">Keranjang kosong — atau pakai Demo 1-klik.</p>
          ) : (
            <div className="space-y-3 mb-4">
              {cart.map((l) => (
                <div key={l.id} className="flex items-center justify-between gap-2">
                  <div className="min-w-0">
                    <p className="text-sm font-medium truncate">{l.name}</p>
                    <p className="text-xs text-gray-400">max {l.stock}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <button type="button" onClick={() => changeQty(l.id, -1)} className="p-1 border rounded"><Minus size={14} /></button>
                    <span className="w-6 text-center text-sm font-semibold">{l.qty}</span>
                    <button type="button" onClick={() => changeQty(l.id, 1)} className="p-1 border rounded"><Plus size={14} /></button>
                  </div>
                </div>
              ))}
            </div>
          )}

          <button
            type="button"
            disabled={saving}
            onClick={() => commitSale()}
            className="w-full bg-primary text-white py-2.5 rounded-lg text-sm font-medium hover:opacity-90 disabled:opacity-50 mb-2"
          >
            {saving ? 'Menyimpan…' : 'Simpan transaksi'}
          </button>
          <button
            type="button"
            onClick={buildWhatsAppDraft}
            className="w-full border border-primary text-primary py-2.5 rounded-lg text-sm font-medium hover:bg-primary/5"
          >
            Salin draft WhatsApp
          </button>
          {note && !lastTx && <p className="mt-3 text-xs text-gray-600 bg-gray-50 p-3 rounded-lg">{note}</p>}
        </div>
      </div>
    </div>
  );
}
