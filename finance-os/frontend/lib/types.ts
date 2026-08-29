export interface NetWorthData {
  net_worth: number;
  assets: number;
  liabilities: number;
  trend: { date: string; net_worth: number }[];
}

export interface CashflowData {
  income: number;
  expenses: number;
  cash_flow: number;
}

export interface PortfolioPulseData {
  total_value: number;
  growth_rate: number;
  recent_transactions: any[];
}

export interface EmergencyFundData {
  balance: number;
  target: number;
  progress: number;
}

export interface DebtStatusData {
  total_debt: number;
  interest_rate: number;
  monthly_payment: number;
  remaining_months: number;
}

export interface SurplusAllocationData {
  surplus: number;
  allocation: { category: string; amount: number }[];
}

export interface GoalsOverviewData {
  total_months: number;
  goal_probability: number;
  current_progress: number;
  target_amount: number;
}

export interface TopActionsData {
  actions: { title: string; description: string; action: () => void }[];
}

export interface DataHealthData {
  status: string;
  details: { [key: string]: any };
}
