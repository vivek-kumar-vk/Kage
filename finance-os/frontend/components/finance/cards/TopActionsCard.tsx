"use client";
import { useFinanceData } from "@/lib/api";
import type { TopActionsData } from "@/lib/types";

// Rendered inside the shared panel in app/finance/page.tsx — no .panel here.
export default function TopActionsCard() {
  const { data, isLoading, error } = useFinanceData<TopActionsData>("/overview/top-actions");
  const actions = data?.actions ?? [];

  return (
    <div className="flex h-full flex-col">
      {isLoading ? (
        <p className="footnote">LOADING…</p>
      ) : error ? (
        <p className="text-xs text-aurum-coral">Failed to load: {error.message}</p>
      ) : (
        <>
          <div className="plabel">
            Top Actions
            <span className={`tag ${actions.length === 0 ? "dim" : ""}`}>
              {actions.length} open
            </span>
          </div>

          {actions.length === 0 ? (
            <p className="mt-4 text-xs text-aurum-muted">Nothing needs a decision today.</p>
          ) : (
            actions.map((a, i) => (
              <div key={a.title} className="mt-4 flex items-start gap-3">
                <div
                  className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full border font-mono text-[11px] ${
                    a.urgent
                      ? "border-aurum-coral/40 bg-aurum-coral/[.07] text-aurum-coral"
                      : "border-aurum-gold/40 bg-aurum-gold/[.07] text-aurum-gold"
                  }`}
                >
                  {i + 1}
                </div>
                <div className="min-w-0">
                  <div className="text-[12.5px] font-semibold">{a.title}</div>
                  <div className="mt-[3px] text-[11.5px] leading-[1.45] text-aurum-muted">
                    {a.detail}
                  </div>
                </div>
              </div>
            ))
          )}
        </>
      )}
    </div>
  );
}
