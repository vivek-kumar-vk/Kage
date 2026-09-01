"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const TABS = [
  { name: "TODAY", href: "/" },
  { name: "PLAN", href: "/plan" },
  { name: "RECALL", href: "/recall" },
];

export default function TopNav() {
  const pathname = usePathname();

  return (
    <nav className="border-b border-term-border px-4 py-3 flex items-center gap-6">
      <span className="text-term-dim font-bold mr-4">[KAGE_OS]</span>

      {TABS.map((tab) => {
        const active = pathname === tab.href;

        return (
          <Link
            key={tab.href}
            href={tab.href}
            className={[
              "pb-1 border-b-2 transition-colors motion-reduce:transition-none",
              active
                ? "text-term-green border-term-green"
                : "text-term-dim border-transparent hover:text-term-fg",
            ].join(" ")}
          >
            {tab.name}
          </Link>
        );
      })}
    </nav>
  );
}
