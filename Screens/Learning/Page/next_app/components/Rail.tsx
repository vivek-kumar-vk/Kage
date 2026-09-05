"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import type { MouseEvent } from "react";

const OVERVIEW = "/";

/**
 * Tab clicks that keep browser history shallow. The stack for this
 * screen never grows past [main menu, Today, current tab], so one Back
 * press from any tab lands on Today and one more lands on the main menu
 * — instead of walking back through every tab visited.
 *
 *   -> Today       : step back (Today is always the entry just below a tab)
 *   Today -> tab   : push (the single entry above Today)
 *   tab -> tab     : replace (swap that single entry)
 *
 * Keeps <Link> for prefetch + real href; only the plain left-click is
 * intercepted.
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

const ITEMS = [
  { href: "/", label: "Today", key: "1", ico: (
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
        <circle cx="12" cy="12" r="9" /><circle cx="12" cy="12" r="3.2" fill="currentColor" stroke="none" />
      </svg>) },
  { href: "/path", label: "Path", key: "2", ico: (
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
        <path d="M4 19V5m0 14h9l-2-3 2-3H4" /><circle cx="19" cy="6" r="2.5" /><path d="M4 5h9l-2 3 2 3" />
      </svg>) },
  { href: "/recall", label: "Recall", key: "3", ico: (
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
        <rect x="7" y="4" width="13" height="16" rx="2" /><path d="M4 7v11a2 2 0 0 0 2 2h9" />
      </svg>) },
  { href: "/insights", label: "Insights", key: "4", ico: (
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
        <path d="M3 12h4l2.5-6 4 12 2.5-6H21" />
      </svg>) },
  { href: "/crew", label: "Crew", key: "5", ico: (
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
        <circle cx="9" cy="8" r="3.2" /><path d="M3.5 19c.6-3 2.9-4.6 5.5-4.6s4.9 1.6 5.5 4.6" />
        <circle cx="17" cy="9" r="2.4" /><path d="M16 14.6c2.3.1 4 1.5 4.5 4" />
      </svg>) },
];

export default function Rail() {
  const path = usePathname();
  const onTabClick = useShallowTabNav();
  return (
    <aside className="rail">
      <div className="logo">
        KAGE<b>·</b>LEARNING
      </div>
      {ITEMS.map((it) => {
        const active = it.href === "/" ? path === "/" : path.startsWith(it.href);
        return (
          <Link key={it.href} href={it.href}
            onClick={(e) => onTabClick(e, it.href)}
            className={`nav-item${active ? " active" : ""}`}>
            <span className="nav-ico">{it.ico}</span>
            {it.label}
            <span className="key">{it.key}</span>
          </Link>
        );
      })}
      <div className="rail-foot">
        <div className="row"><span className="track-dot dim" style={{ width: 6, height: 6 }} />CTRL+K CAPTURE</div>
        <div className="row"><span className="track-dot jade" style={{ width: 6, height: 6 }} />KAGE OS · V2</div>
      </div>
    </aside>
  );
}
