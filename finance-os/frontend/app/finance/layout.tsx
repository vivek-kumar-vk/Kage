'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

const tabs = [
  { name: 'Overview', href: '/finance' },
  { name: 'Investments', href: '/finance/investments' },
  { name: 'Debt', href: '/finance/debt' },
  { name: 'Tracker', href: '/finance/tracker' },
  { name: 'Learning', href: '/finance/learning' },
];

const Layout = ({ children }: { children: React.ReactNode }) => {
  const pathname = usePathname();
  return (
    <div className="flex flex-col h-screen">
      <header className="bg-racing-red text-white shadow-neon-red p-4">
        <span className="status-dot"></span>
        <h1>FINANCE OS</h1>
      </header>
      <nav className="bg-carbon-light p-4">
        <ul className="flex space-x-4">
          {tabs.map(tab => (
            <li key={tab.href} className={`flex items-center ${pathname === tab.href ? 'bg-racing-red text-white shadow-neon-red' : 'text-gray-400 hover:text-white hover:bg-carbon-light'}`}>
              <Link href={tab.href}>{tab.name}</Link>
            </li>
          ))}
        </ul>
      </nav>
      <main className="flex-1">
        <Link href="/finance/settings">Settings</Link>
        <div className="p-4">
          {children}
        </div>
      </main>
    </div>
  );
};

export default Layout;
