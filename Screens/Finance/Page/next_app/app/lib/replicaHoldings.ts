/** Exact data from Screenshot 2026-08-22 090804.png — the Investments
    tab. Placeholder values; the owner will swap real numbers in later.
    Currency is INR; `current` and `units` are the editable fields. */

export const REPLICA_SUMMARY = {
  invested: 134166,
  currentValue: 160742,
  gainLoss: 26576,
};

export const REPLICA_GATE = {
  code: "G2",
  text: ": BUFFER GATE. Surplus routes to emergency fund.",
};

export type ReplicaHolding = {
  name: string;
  kind: string;
  code: string | null;
  navStatus: "fresh2d" | "not_in_ledger";
  invested: number;
  current: number;
  gainAbs: number;
  gainPct: number;
  units: number;
};

export const REPLICA_HOLDINGS: ReplicaHolding[] = [
  { name: "HDFC Mid Cap Fund Direct Growth", kind: "mutual_fund", code: "118989", navStatus: "fresh2d", invested: 33355, current: 36931.55, gainAbs: 3577, gainPct: 10.72, units: 156.209 },
  { name: "HDFC Children's Fund Plan", kind: "mutual_fund", code: null, navStatus: "not_in_ledger", invested: 9900, current: 30359.04, gainAbs: 20459, gainPct: 206.66, units: 103.765 },
  { name: "Parag Parikh Flexi Cap Fund Direct Growth", kind: "mutual_fund", code: "122639", navStatus: "fresh2d", invested: 20999, current: 20539.16, gainAbs: -460, gainPct: -2.19, units: 226.345 },
  { name: "UTI Multi Asset Allocation Fund Direct Growth", kind: "mutual_fund", code: "120760", navStatus: "fresh2d", invested: 18999, current: 19244.98, gainAbs: 246, gainPct: 1.29, units: 214.126 },
  { name: "SBI ELSS Tax Saver Fund Growth", kind: "mutual_fund", code: "119723", navStatus: "fresh2d", invested: 13998, current: 14234.99, gainAbs: 237, gainPct: 1.69, units: 32.828 },
  { name: "ICICI Prudential NASDAQ 100 Index Fund Direct Growth", kind: "mutual_fund", code: "149219", navStatus: "fresh2d", invested: 12499, current: 13681.38, gainAbs: 1182, gainPct: 9.46, units: 563.006 },
  { name: "UTI Nifty Next 50 Index Fund Direct Growth", kind: "mutual_fund", code: "143341", navStatus: "fresh2d", invested: 9927, current: 11723.46, gainAbs: 1796, gainPct: 18.09, units: 425.082 },
  { name: "Nippon India ETF Gold BeES", kind: "etf", code: "INF204KB17I5", navStatus: "not_in_ledger", invested: 11109, current: 10439.28, gainAbs: -670, gainPct: -6.03, units: 81 },
  { name: "Bandhan Small Cap Fund Direct Growth", kind: "mutual_fund", code: "147946", navStatus: "fresh2d", invested: 2879, current: 3085.69, gainAbs: 207, gainPct: 7.18, units: 54.271 },
];
