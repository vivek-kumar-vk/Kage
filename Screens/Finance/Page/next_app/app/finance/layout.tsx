'use client';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { Suspense, useEffect, type MouseEvent } from 'react';
import { useFinanceData } from '@/lib/api';
import type { DataHealthData, NetWorthData } from '@/lib/types';
import MonthSelector from '@/components/finance/MonthSelector';

const OVERVIEW = '/finance';

const tabs = [
  { name: 'Overview', href: '/finance' },
  { name: 'Investments', href: '/finance/investments' },
  { name: 'Analysis', href: '/finance/analysis' },
  { name: 'Trade Desk', href: '/finance/tradedesk' },
  { name: 'Debt', href: '/finance/debt' },
  { name: 'Tracker', href: '/finance/tracker' },
];

function isActive(pathname: string, href: string) {
  return href === '/finance' ? pathname === '/finance' : pathname.startsWith(href);
}

/**
 * Tab clicks that keep browser history shallow. The stack for this
 * screen never grows past [main menu, Overview, current tab], so one
 * Back press from any tab lands on Overview and one more lands on the
 * main menu — instead of walking back through every tab visited.
 *
 *   -> Overview      : step back (Overview is always the entry just
 *                      below a tab, so there is nothing to add)
 *   Overview -> tab  : push (the single entry above Overview)
 *   tab -> tab       : replace (swap that single entry)
 *
 * Keeps <Link> for prefetch + real href (middle-click, right-click);
 * only the plain left-click is intercepted.
 */
function useShallowTabNav() {
  const router = useRouter();
  const pathname = usePathname();
  return (event: MouseEvent, href: string) => {
    if (
      event.defaultPrevented ||
      event.button !== 0 ||
      event.metaKey ||
      event.ctrlKey ||
      event.shiftKey ||
      event.altKey
    ) {
      return;
    }
    event.preventDefault();
    if (href === pathname) return;
    if (href === OVERVIEW) router.back();
    else if (pathname === OVERVIEW) router.push(href);
    else router.replace(href);
  };
}

function syncedLabel(freshness?: { prices?: string | null }): string | null {
  const p = freshness?.prices;
  if (!p) return null;
  if (p === 'live') return 'just now';
  return p;
}

const Layout = ({ children }: { children: React.ReactNode }) => {
  const pathname = usePathname();
  const onTabClick = useShallowTabNav();
  const { data, refetch } = useFinanceData<DataHealthData>('/overview/data-health');
  // The month list comes from the same trend the Overview cards already use —
  // no arithmetic range, so a month with no snapshot is never offered (D28).
  const { data: netWorth } = useFinanceData<NetWorthData>('/overview/net-worth');

  // keep the LIVE pill honest — re-poll freshness every 60 s
  useEffect(() => {
    const id = setInterval(() => refetch(), 60_000);
    return () => clearInterval(id);
  }, [refetch]);

  const synced = syncedLabel(data?.freshness);

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
              onClick={(e) => onTabClick(e, tab.href)}
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
          <Suspense fallback={<div className="pill">···</div>}>
            <MonthSelector trend={netWorth?.trend} interactive={pathname === '/finance'} />
          </Suspense>
          <Link
            href="/finance/settings"
            onClick={(e) => onTabClick(e, '/finance/settings')}
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
