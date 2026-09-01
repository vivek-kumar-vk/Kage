'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect } from 'react';
import { useFinanceData } from '@/lib/api';
import type { DataHealthData } from '@/lib/types';

const tabs = [
  { name: 'Overview', href: '/finance' },
  { name: 'Investments', href: '/finance/investments' },
  { name: 'Debt', href: '/finance/debt' },
  { name: 'Tracker', href: '/finance/tracker' },
  { name: 'Learning', href: '/finance/learning' },
];

function isActive(pathname: string, href: string) {
  return href === '/finance' ? pathname === '/finance' : pathname.startsWith(href);
}

function syncedLabel(freshness?: { prices?: string | null }): string | null {
  const p = freshness?.prices;
  if (!p) return null;
  if (p === 'live') return 'just now';
  return p;
}

const Layout = ({ children }: { children: React.ReactNode }) => {
  const pathname = usePathname();
  const { data, refetch } = useFinanceData<DataHealthData>('/overview/data-health');

  // keep the LIVE pill honest — re-poll freshness every 60 s
  useEffect(() => {
    const id = setInterval(() => refetch(), 60_000);
    return () => clearInterval(id);
  }, [refetch]);

  const synced = syncedLabel(data?.freshness);
  const month = new Date()
    .toLocaleDateString('en-GB', { month: 'short', year: 'numeric' })
    .toUpperCase();

  return (
    <div className="flex min-h-screen flex-col aurum-page">
      <header className="relative z-10 flex h-[66px] items-center gap-10 border-b border-white/[.075] bg-gradient-to-b from-white/[.02] to-transparent px-8">
        <div className="flex items-baseline gap-2.5 font-serif text-[21px] font-medium tracking-wide text-aurum-gold-bright">
          Aurum <span className="font-mono text-[10px] tracking-[.28em] text-aurum-faint">FINANCE OS</span>
        </div>
        <nav className="flex h-[66px] gap-1">
          {tabs.map((tab) => (
            <Link
              key={tab.href}
              href={tab.href}
              className={`flex items-center border-b-2 px-[18px] text-[13px] font-medium tracking-wide ${
                isActive(pathname, tab.href)
                  ? 'border-aurum-gold text-aurum-gold-bright'
                  : 'border-transparent text-aurum-muted hover:text-aurum-text'
              }`}
            >
              {tab.name}
            </Link>
          ))}
        </nav>
        <div className="ml-auto flex items-center gap-3.5">
          <div className="pill">
            <span className="dot" />
            {synced ? `LIVE · synced ${synced}` : 'LIVE · awaiting first sync'}
          </div>
          <div className="pill">{month}</div>
          <Link
            href="/finance/settings"
            className="chip hover:border-aurum-gold/40 hover:text-aurum-gold"
          >
            SETTINGS
          </Link>
          <div className="avatar">VK</div>
        </div>
      </header>
      <main className="relative z-[1] flex-1">
        <div className="p-8 pt-[22px]">{children}</div>
      </main>
    </div>
  );
};

export default Layout;
