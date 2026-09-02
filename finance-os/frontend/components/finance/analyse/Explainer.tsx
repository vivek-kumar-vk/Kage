"use client";

// Metric explanations for the Analyse drawer. Every line says what the
// number means and where it comes from — the user is not finance-educated,
// so no jargon is left unexplained. Links go to Zerodha Varsity chapters.

const DEFS: { term: string; def: string }[] = [
  { term: "Expense ratio (TER)", def: "The fund's yearly fee, cut from your money every day. 1% on ₹1,00,000 is ₹1,000 a year — whether the fund makes or loses money. A direct plan is the same fund without the distributor commission, so its TER is lower." },
  { term: "XIRR", def: "YOUR money-weighted return — the annual rate that makes every buy you made (at its date) grow into today's value. Unlike a fund's advertised return, it respects when you actually invested." },
  { term: "Beta", def: "How much the fund swings compared to the index. Beta 1 moves with the market, 1.2 swings 20% harder, 0.6 is calmer. Computed against NIFTY 50 over the last year." },
  { term: "Alpha", def: "Return the manager added beyond what the market's move (beta) explains. Positive alpha is genuine skill, negative is paying fees to underperform." },
  { term: "Sharpe ratio", def: "Return earned per unit of total ups-and-downs. Compare funds in the same category — a higher Sharpe means the same return came with a smoother ride." },
  { term: "Sortino ratio", def: "Like Sharpe, but only counts the DOWN days in the penalty. A fund that swings upward a lot looks better on Sortino than on Sharpe." },
  { term: "Volatility (standard deviation)", def: "How wildly the daily returns scatter, annualised. 10% means a typical year wanders ±10% around its average." },
  { term: "Max drawdown", def: "The worst peak-to-trough fall in the period. If you had bought at the worst top, this is how deep under water you would have been." },
  { term: "R-squared", def: "How much of the fund's movement the index explains. Near 1.0 = it is basically the index (an index fund sits at 1.0). Small values make beta/alpha unreliable." },
  { term: "Portfolio overlap", def: "How much two funds own the SAME stocks, by weight. 60% overlap means six of every ten rupees ride the same companies — owning both adds less variety than it looks." },
  { term: "Portfolio X-ray (look-through)", def: "Your funds' own holdings combined into one list — what you REALLY own, company by company, weighted by what each fund is worth to you." },
  { term: "HHI / effective number of stocks", def: "A concentration measure regulators use. 1/HHI converts your whole portfolio into 'how many distinct stocks it behaves like' — 9 funds may really be just 20 companies." },
  { term: "STCG / LTCG", def: "Capital-gains tax on units sold within a year (STCG, 20%) vs after a year (LTCG, 12.5% beyond ₹1.25L a year, for equity funds). Gold ETFs need 24 months for long-term." },
  { term: "Exit load", def: "A fee for redeeming too early. '1% within 365 days' means selling in the first year costs 1% of what you take out." },
  { term: "AUM", def: "Assets under management — the fund's total size in ₹ crore. Very small funds carry closure risk; very large equity funds find it harder to be nimble." },
];

export default function Explainer() {
  return (
    <details className="group mt-5 border-t border-white/[.07] pt-4">
      <summary className="cursor-pointer list-none plabel">
        What these numbers mean
        <span className="tag">varsity · free</span>
        <span className="ml-1 text-aurum-faint transition-transform group-open:rotate-90">▸</span>
      </summary>
      <div className="mt-3 grid grid-cols-1 gap-2.5 md:grid-cols-2">
        {DEFS.map((d) => (
          <div key={d.term} className="rounded-lg border border-white/[.06] bg-white/[.02] p-3">
            <div className="text-[11px] font-semibold tracking-wide text-aurum-gold">{d.term}</div>
            <div className="mt-1 text-[12px] leading-relaxed text-aurum-muted">{d.def}</div>
          </div>
        ))}
      </div>
      <p className="footnote mt-3">
        Learn deeper (free):{" "}
        <a className="text-aurum-gold underline-offset-2 hover:underline"
           href="https://zerodha.com/varsity/module/mutual-funds-understanding-types-risks" target="_blank" rel="noreferrer">
          Varsity — Mutual Funds
        </a>{" · "}
        <a className="text-aurum-gold underline-offset-2 hover:underline"
           href="https://zerodha.com/varsity/chapter/portfolio-management" target="_blank" rel="noreferrer">
          Varsity — Portfolio construction
        </a>{" · "}
        <a className="text-aurum-gold underline-offset-2 hover:underline"
           href="https://zerodha.com/varsity/chapter/capital-gains-tax" target="_blank" rel="noreferrer">
          Varsity — Capital gains
        </a>
      </p>
    </details>
  );
}
