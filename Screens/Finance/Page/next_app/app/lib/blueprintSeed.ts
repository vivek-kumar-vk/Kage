/** Seed data for the Finance telemetry panels (v1).

    The real numbers here (total balance, the three emergency-fund tiers,
    the target) come straight from personal-financial-blueprint.html's
    emergency-fund calculator defaults. Everything tagged `SEED` is a
    placeholder demo value so the panels render and animate before the
    live wiring lands — each carries the endpoint it should read from.
    Superseded by finance-os. No panel invents a figure past this
    file. */

export const BLUEPRINT_SEED = {
  // --- from the blueprint (real) ---
  totalBalance: 150000,
  emergencyFund: {
    target: 150000,
    tiers: [
      { key: "t1", label: "Instant", amount: 25000, park: "Savings a/c · sweep FD" },
      { key: "t2", label: "Core", amount: 87500, park: "Liquid / overnight funds" },
      { key: "t3", label: "Buffer", amount: 37500, park: "Short-duration debt / FD" },
    ],
  },

  // --- 3-bucket system (structure real, fill % illustrative like the blueprint) ---
  buckets: [
    {
      key: "safety",
      name: "Safety Net",
      horizon: "Always ready",
      fillPct: 85,
      note: "Emergency fund · immediate needs",
    },
    {
      key: "short",
      name: "Short-Term",
      horizon: "1–5 yrs",
      fillPct: 55,
      note: "Goals 1–5 yrs · liquid assets",
    },
    {
      key: "long",
      name: "Long-Term",
      horizon: "10+ yrs",
      fillPct: 35,
      note: "Retirement · investments · legacy",
    },
  ],

  // --- standard widgets (SEED — swap to live endpoints, P8) ---
  cashFlow: { income: 90000, expenses: 61000 }, // SEED — /api/finance/money
  goals: [
    { label: "Emergency Fund", pct: 58 },
    { label: "Higher Studies", pct: 34 },
    { label: "New Bike", pct: 21 },
    { label: "Retirement", pct: 12 },
  ], // SEED — no endpoint yet (P8)
  investments: {
    current: 240000,
    // 12 monthly closing values in ₹ thousands
    series: [180, 176, 190, 205, 198, 214, 222, 219, 231, 228, 236, 240],
  }, // SEED — /api/finance/portfolio-analysis
  totalDebt: 160000, // SEED — /api/finance/debt
  portfolioValue: 240000, // SEED — /api/finance/portfolio-analysis
} as const;

export type BlueprintSeed = typeof BLUEPRINT_SEED;
