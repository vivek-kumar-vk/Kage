// Response shapes of the /api/finance/overview/* endpoints (must match
// services/calculations/core.py). Optional = backend could not compute it and
// returns null — the UI shows a dash, never an invented number.

export interface TrendPoint {
  date: string;
  net_worth: number;
}

export interface ProjectionPoint {
  month: string; // "2026-09"
  net_worth: number;
}

export interface NetWorthData {
  net_worth: number;
  assets: number;
  liabilities: number;
  all_time_pct: number | null;
  month_change_pct: number | null;
  month_change_abs: number | null;
  trend: TrendPoint[];
  projection: ProjectionPoint[];
}

export interface CashflowMonth {
  month: string; // "2026-04"
  label: string; // "APR"
  income: number;
  expenses: number;
  surplus: number;
}

export interface CashflowData {
  income: number;
  expenses: number;
  cash_flow: number;
  months: CashflowMonth[];
}

export interface BestToday {
  symbol: string;
  name: string;
  change_pct: number;
}

export interface PulsePoint {
  date: string;
  value: number;
}

export interface PortfolioPulseData {
  total_value: number;
  invested: number;
  history: PulsePoint[];
  day_change: number | null;
  day_change_pct: number | null;
  xirr_pct: number | null;
  holdings_count: number;
  asset_classes: number;
  best_today: BestToday | null;
}

export interface EmergencyFundData {
  balance: number;
  target: number;
  monthly_expenses: number;
  monthly_earmark: number;
  months_covered: number;
  progress: number; // 0..1
  eta_date: string | null; // ISO date
}

export interface LoanRow {
  id: number;
  name: string;
  outstanding: number;
  rate: number | null;
  emi: number | null;
  share: number; // 0..1 of total
}

export interface DebtStatusData {
  total_debt: number;
  total_emi: number;
  weighted_rate: number;
  count: number;
  loans: LoanRow[];
}

export interface SweepRule {
  emergency: number;
  investments: number;
  goals: number;
}

export interface SurplusAllocationData {
  surplus: number;
  monthly_net: number;
  monthly_expenses: number;
  monthly_emi: number;
  rule: SweepRule;
  allocation: { category: string; amount: number }[];
}

export interface GoalRow {
  id: number;
  name: string;
  target_amount: number;
  current_amount: number;
  target_date: string | null;
  progress: number; // 0..1
  probability: number; // percent
  probability_source: "monte-carlo" | "heuristic";
}

export interface GoalsOverviewData {
  goals: GoalRow[];
  count: number;
  monthly_goal_sip: number;
  assumed_return_pct: number;
  assumed_vol_pct: number;
}

export interface TopAction {
  title: string;
  detail: string;
  urgent?: boolean;
}

export interface TopActionsData {
  actions: TopAction[];
  count: number;
}

export interface DataHealthData {
  id: number;
  cas_last_import: string | null;
  price_last_refresh: string | null;
  sms_last_import: string | null;
  unmatched_transactions: number;
  missing_info: string | null;
  health_score: string | null;
  updated_at: string | null;
  freshness: { cas?: string | null; prices?: string | null; sms?: string | null };
  score: number | null;
}
