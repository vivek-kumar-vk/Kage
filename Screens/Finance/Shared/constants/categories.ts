export const TRANSACTION_CATEGORIES = [
  "Salary",
  "Investment",
  "Debt",
  "Transfer",
  "Expense",
  "Income",
  "Miscellaneous",
] as const;

export const TRANSACTION_TYPES = [
  "Credit",
  "Debit",
] as const;

export const ACCOUNT_TYPES = [
  "Savings",
  "Current",
  "Fixed Deposit",
  "Mutual Fund",
  "Equity",
  "Debt",
  "Insurance",
  "Loan",
] as const;

export const HOLDING_TYPES = [
  "Equity",
  "Bond",
  "Mutual Fund",
  "Commodity",
  "Real Estate",
  "Art",
  "Collectibles",
] as const;

export type TransactionCategory = typeof TRANSACTION_CATEGORIES[number];
export type TransactionType = typeof TRANSACTION_TYPES[number];
export type AccountType = typeof ACCOUNT_TYPES[number];
export type HoldingType = typeof HOLDING_TYPES[number];
