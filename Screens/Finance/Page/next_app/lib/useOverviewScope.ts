"use client";
// The Overview month scope lives in the URL (?month=YYYY-MM-DD), not a React
// context — the header pill (layout.tsx) sits *above* the Overview page in
// the tree, so a context provider mounted on the page can't reach it (D28.1,
// AGENTS.md). The URL survives a refresh and a shared link too.
import { useRouter, useSearchParams, usePathname } from "next/navigation";
import { useCallback, useMemo } from "react";
import type { TrendPoint } from "./types";

export interface OverviewScope {
  /** ISO month-end date, or null for LIVE */
  through: string | null;
  /** "" for LIVE, "?through=YYYY-MM-DD" otherwise — append to a card's path */
  query: string;
  isHistorical: boolean;
  /** e.g. "JUN 2026" — for labels */
  label: string;
}

function monthLabelOf(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("en-GB", { month: "short", year: "numeric" }).toUpperCase();
}

/** Read-only side, used by every Overview card. */
export function useOverviewScope(): OverviewScope {
  const params = useSearchParams();
  const through = params.get("month");

  return useMemo(() => {
    if (!through) {
      return { through: null, query: "", isHistorical: false, label: "LIVE" };
    }
    return {
      through,
      query: `?through=${through}`,
      isHistorical: true,
      label: monthLabelOf(through),
    };
  }, [through]);
}

export interface MonthOption {
  date: string;
  label: string;
}

export interface MonthPicker {
  /** Newest first — the months that actually have a snapshot. */
  months: MonthOption[];
  selected: string | null;
  setThrough: (date: string | null) => void;
}

/** Writer side — mounted only where the trend array is already in hand
 * (the header pill fetches its own copy of /overview/net-worth). */
export function useMonthPicker(trend: TrendPoint[] | undefined): MonthPicker {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const selected = params.get("month");

  const months = useMemo<MonthOption[]>(
    () =>
      [...(trend ?? [])]
        .reverse()
        .map((t) => ({ date: t.date, label: monthLabelOf(t.date) })),
    [trend]
  );

  const setThrough = useCallback(
    (date: string | null) => {
      const next = new URLSearchParams(params.toString());
      if (date) next.set("month", date);
      else next.delete("month");
      const qs = next.toString();
      router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
    },
    [params, pathname, router]
  );

  return { months, selected, setThrough };
}
