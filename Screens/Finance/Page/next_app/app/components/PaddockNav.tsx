"use client";

import { usePrefersReducedMotion } from "@/app/lib/usePrefersReducedMotion";

type Item = { id: string; label: string };

/** The left-rail nav — a plain vertical list. The active row carries a
    2px leading bar in the current livery accent (var(--liv-accent), set
    by the .liv-* class on the grid wrapper), so the team colour shifts
    as you move between tabs. Same items/tab/onSelect contract the old
    SpeedoNav had; parent still owns the tab state. */
export function PaddockNav({
  items,
  tab,
  onSelect,
}: {
  items: Item[];
  tab: string;
  onSelect: (id: string) => void;
}) {
  const reduce = usePrefersReducedMotion();

  return (
    <nav aria-label="Finance sections" className="shrink-0">
      <ul className="flex flex-col gap-1">
        {items.map((it) => {
          const on = it.id === tab;
          return (
            <li key={it.id}>
              <button
                type="button"
                aria-current={on ? "page" : undefined}
                onClick={() => onSelect(it.id)}
                style={{
                  borderLeftColor: on ? "var(--liv-accent)" : "transparent",
                  background: on ? "var(--liv-surface)" : "transparent",
                  color: on ? "var(--liv-text)" : "var(--liv-text-dim)",
                  transition: reduce ? "none" : "background 160ms, color 160ms",
                }}
                className="num w-full border-l-2 px-3 py-2 text-left text-xs tracking-[0.18em] hover:text-[color:var(--liv-text)]"
              >
                {it.label}
              </button>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
