// Pure rebase math for the net-worth ridge's benchmark overlay (PLAN item 6).
import type { BenchmarkPoint, TrendPoint } from "./types";

/**
 * Rebase the benchmark's `indexed` series onto net worth's own scale so the
 * two lines can share one chart mapping instead of each being independently
 * min-max scaled — scaling them separately would make any two series "track"
 * regardless of what the numbers actually say (D28, AGENTS.md).
 *
 * Net worth here can be negative (a large education loan), so a plain ratio
 * against it is meaningless. Instead this reads as: what would net worth be
 * today if it had moved by the index's percentage change instead of its own,
 * sized by the *magnitude* of the opening net-worth figure. Aligned by date,
 * never by array index — a month missing from the benchmark response is a
 * gap (`null`), never interpolated.
 */
export function rebaseBenchmark(
  trend: TrendPoint[],
  points: BenchmarkPoint[]
): (number | null)[] {
  if (trend.length === 0) return [];
  const base = trend[0].net_worth;
  const assetsBase = Math.abs(base) || 1;
  const byDate = new Map(points.map((p) => [p.date, p.indexed]));

  return trend.map((t) => {
    const indexed = byDate.get(t.date);
    if (indexed === undefined) return null;
    return base + assetsBase * (indexed / 100 - 1);
  });
}
