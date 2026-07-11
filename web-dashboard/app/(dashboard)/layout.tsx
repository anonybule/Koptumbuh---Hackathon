'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard, ShoppingCart, Package, Truck, Users, Building2,
  Landmark, BarChart3, LogOut, Menu, BookOpen, Bell,
  Lightbulb, Download, UserCog, MapPin, Receipt, Wallet, FileText, Settings,
  PanelLeftClose, PanelLeftOpen, X, HeartHandshake, MessageSquare, Bot,
} from 'lucide-react';
import { clearTokens } from '../../lib/api';

const navItems = [
  { href: '/', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/analytics', label: 'Analytics', icon: BarChart3 },
  { href: '/customer-relationship', label: 'Customer Relationship', icon: HeartHandshake },
  { href: '/chathub', label: 'ChatHub', icon: MessageSquare },
  { href: '/automations', label: 'Automasi', icon: Bot },
  { href: '/pos', label: 'POS Kasir', icon: ShoppingCart },
  { href: '/transactions', label: 'Transaksi', icon: Receipt },
  { href: '/inventory', label: 'Inventaris', icon: Package },
  { href: '/supply', label: 'Supply', icon: Truck },
  { href: '/members', label: 'Anggota', icon: Users },
  { href: '/loans', label: 'Pinjaman', icon: Wallet },
  { href: '/cooperatives', label: 'Koperasi', icon: Building2 },
  { href: '/rat', label: 'RAT', icon: FileText },
  { href: '/finance', label: 'Keuangan', icon: Landmark },
  { href: '/village', label: 'Desa', icon: MapPin },
  { href: '/knowledge', label: 'Pengetahuan', icon: BookOpen },
  { href: '/recommendations', label: 'Rekomendasi', icon: Lightbulb },
  { href: '/notifications', label: 'Notifikasi', icon: Bell },
  { href: '/export', label: 'Ekspor', icon: Download },
  { href: '/users', label: 'Pengguna', icon: UserCog },
  { href: '/settings', label: 'Settings', icon: Settings },
];

function isActive(pathname: string, href: string) {
  if (href === '/') return pathname === '/';
  return pathname === href || pathname.startsWith(`${href}/`);
}

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const pathname = usePathname();

  // Mobile starts closed; desktop starts open
  useEffect(() => {
    const mq = window.matchMedia('(min-width: 1024px)');
    const sync = () => setSidebarOpen(mq.matches);
    sync();
    mq.addEventListener('change', sync);
    return () => mq.removeEventListener('change', sync);
  }, []);

  return (
    <div className="flex h-screen bg-gray-50 overflow-hidden">
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
          aria-hidden
        />
      )}

      <aside
        className={`fixed lg:static inset-y-0 left-0 z-50 bg-primary text-white
          flex flex-col shrink-0 overflow-hidden
          transition-all duration-300 ease-in-out
          ${sidebarOpen
            ? 'translate-x-0 w-64'
            : '-translate-x-full w-64 lg:translate-x-0 lg:w-0'}`}
        aria-hidden={!sidebarOpen}
      >
        <div className="flex flex-col h-full w-64 min-w-[16rem]">
          <div className="p-4 border-b border-white/10 shrink-0 flex items-start justify-between gap-2">
            <div>
              <h1 className="text-xl font-bold">KopTumbuh</h1>
              <p className="text-xs text-white/60">JasaAI — Cooperative Platform</p>
            </div>
            <button
              type="button"
              onClick={() => setSidebarOpen(false)}
              className="p-1.5 rounded-lg hover:bg-white/10 transition shrink-0"
              aria-label="Tutup sidebar"
              title="Tutup sidebar"
            >
              <PanelLeftClose size={18} className="hidden lg:block" />
              <X size={18} className="lg:hidden" />
            </button>
          </div>

          <nav className="p-2 space-y-0.5 overflow-y-auto flex-1 scrollbar-hide">
            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => {
                  if (window.matchMedia('(max-width: 1023px)').matches) {
                    setSidebarOpen(false);
                  }
                }}
                className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition
                  ${isActive(pathname, item.href) ? 'bg-white/20 font-medium' : 'hover:bg-white/10'}`}
              >
                <item.icon size={18} className="shrink-0" />
                {item.label}
              </Link>
            ))}
            <button
              type="button"
              onClick={() => {
                clearTokens();
                window.location.href = '/login';
              }}
              className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm w-full hover:bg-red-500/20 transition mt-4"
            >
              <LogOut size={18} className="shrink-0" />
              Keluar
            </button>
          </nav>
        </div>
      </aside>

      <div className="flex-1 flex flex-col min-w-0">
        <header className="bg-white border-b px-4 py-3 flex items-center gap-3 shrink-0">
          <button
            type="button"
            onClick={() => setSidebarOpen((o) => !o)}
            className="p-1.5 rounded-lg hover:bg-gray-100 transition text-primary"
            aria-label={sidebarOpen ? 'Tutup sidebar' : 'Buka sidebar'}
            title={sidebarOpen ? 'Tutup sidebar' : 'Buka sidebar'}
          >
            {sidebarOpen ? (
              <PanelLeftClose size={22} className="hidden lg:block" />
            ) : (
              <PanelLeftOpen size={22} className="hidden lg:block" />
            )}
            <Menu size={22} className="lg:hidden" />
          </button>
          <h1 className="font-bold text-primary">KopTumbuh</h1>
        </header>
        <main className="flex-1 overflow-auto p-6">{children}</main>
      </div>
    </div>
  );
}
