// Shared number/date formatting for the Finance UI. Money is INR, no decimals;
// counts stay plain; rates/progress render as percentages.

export function inr(n: number | null | undefined): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(n);
}

export function num(n: number | null | undefined, digits = 0): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  return new Intl.NumberFormat("en-IN", {
    maximumFractionDigits: digits,
  }).format(n);
}

// compact Indian shorthand — ₹68.4L, ₹1.25Cr, ₹71.6k
export function inrCompact(n: number | null | undefined): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  const sign = n < 0 ? "-" : "";
  const abs = Math.abs(n);
  const trim = (v: number) => String(Math.round(v * 10) / 10);
  if (abs >= 1e7) return `${sign}₹${trim(abs / 1e7)}Cr`;
  if (abs >= 1e5) return `${sign}₹${trim(abs / 1e5)}L`;
  if (abs >= 1e3) return `${sign}₹${trim(abs / 1e3)}k`;
  return `${sign}₹${Math.round(abs)}`;
}

// progress values arrive as a 0..1 fraction; rates arrive already in percent.
export function pctFromFraction(n: number | null | undefined, digits = 0): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  return `${(n * 100).toFixed(digits)}%`;
}

export function pct(n: number | null | undefined, digits = 1): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  return `${num(n, digits)}%`;
}

export function dateOrDash(s: string | null | undefined): string {
  return s ? String(s).slice(0, 10) : "—";
}

// "2026-02" | "2026-02-14" → "FEB 2026"; anything unparseable stays a dash.
export function monthLabel(iso: string | null | undefined): string {
  if (!iso) return "—";
  const s = String(iso);
  const normalized = /^\d{4}-\d{2}$/.test(s) ? `${s}-01` : s.slice(0, 10);
  const d = new Date(`${normalized}T00:00:00`);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleDateString("en-GB", { month: "short", year: "numeric" }).toUpperCase();
}
