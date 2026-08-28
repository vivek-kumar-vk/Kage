"use client";

import { useEffect, useState } from "react";

interface Figure {
  amount: unknown;
  display: string | null;
}
interface Usage {
  cost_display: string | null;
  input_display?: string | null;
  output_display?: string | null;
}
interface Brief {
  total_assets: Figure;
  total_liabilities: Figure;
  before_slice_refill: Figure;
  inky_usage: Usage;
  claude_code_usage: Usage;
}

/** Left column, top module - "SYSTEM METRICS" in the reference's
    list-style layout (icon + label + value per row). Same
    /api/main_menu/home_brief read the earlier neon build used for
    MoneyWidget + AiUsageWidget, merged into one module here to match
    the reference's single "MICRO APPS" panel shape. A blank noticeboard
    value stays blank, never a zero, never a guess (C12). */
export function SystemMetricsPanel() {
  const [brief, setBrief] = useState<Brief | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetch("/api/main_menu/home_brief")
      .then((r) => {
        if (!r.ok) throw new Error(String(r.status));
        return r.json();
      })
      .then((body) => {
        if (!cancelled) setBrief(body);
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const row = (label: string, value: string | null | undefined) => {
    const honest = value !== null && value !== undefined && value !== "[UNVERIFIED]";
    return (
      <li key={label} className="flex items-center justify-between gap-2 py-1.5">
        <span className="text-xs text-dim">{label}</span>
        <span className={`num text-sm ${honest ? "text-white" : "text-dim"}`}>
          {honest ? value : "—"}
        </span>
      </li>
    );
  };

  const anyHonest =
    !!brief &&
    [
      brief.total_assets?.display,
      brief.total_liabilities?.display,
      brief.before_slice_refill?.display,
      brief.inky_usage?.cost_display,
      brief.claude_code_usage?.cost_display,
    ].some((v) => v !== null && v !== undefined && v !== "[UNVERIFIED]");

  return (
    <div
      data-figure="system-metrics"
      data-fresh={failed ? "unavailable" : anyHonest ? "fresh" : "empty"}
      className="agentic-panel p-4"
    >
      <p className="agentic-label mb-2">System Metrics</p>
      {failed ? (
        <p className="text-xs text-amber">the noticeboard did not answer - figures withheld, not guessed</p>
      ) : !brief ? (
        <p className="text-xs text-dim">reading the noticeboard&hellip;</p>
      ) : (
        <ul className="divide-y divide-[#262626]">
          {row("Assets", brief.total_assets?.display)}
          {row("Liabilities", brief.total_liabilities?.display)}
          {row("Before Slice refill", brief.before_slice_refill?.display)}
          {row("Inky usage", brief.inky_usage?.cost_display)}
          {row("Claude Code usage", brief.claude_code_usage?.cost_display)}
        </ul>
      )}
    </div>
  );
}
