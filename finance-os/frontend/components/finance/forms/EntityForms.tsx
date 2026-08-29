"use client";
import { useState } from "react";
import { useSubmit } from "@/lib/api";

// mirrors of finance-os/shared/constants/categories.py (not on the FE import path)
const ACCOUNT_TYPES = ["bank", "demat", "loan", "credit_card", "cash", "other"] as const;
const HOLDING_TYPES = ["stock", "mutual_fund", "etf", "bond", "other"] as const;
const INSURANCE_TYPES = ["term", "health", "vehicle", "home", "other"] as const;

function field(label: string, node: React.ReactNode) {
  return (
    <label className="flex flex-col gap-1 text-sm">
      <span className="text-racing-silver">{label}</span>
      {node}
    </label>
  );
}

const inputCls = "rounded bg-carbon-dark px-2 py-1";

function SubmitButton({ busy }: { busy: boolean }) {
  return (
    <button
      type="submit"
      disabled={busy}
      className="mt-2 rounded bg-racing-blue px-3 py-1 text-sm text-carbon-dark disabled:opacity-50"
    >
      {busy ? "…" : "Save"}
    </button>
  );
}

export function AccountForm({ onSaved }: { onSaved?: () => void }) {
  const { submit, isSubmitting, error } = useSubmit("/accounts", "POST");
  const [name, setName] = useState("");
  const [type, setType] = useState<string>(ACCOUNT_TYPES[0]);
  const [institution, setInstitution] = useState("");
  return (
    <form
      className="flex flex-col gap-2"
      onSubmit={async (e) => {
        e.preventDefault();
        await submit({ name, type, institution });
        onSaved?.();
      }}
    >
      {field("Name", <input className={inputCls} required value={name} onChange={(e) => setName(e.target.value)} />)}
      {field("Type", (
        <select className={inputCls} value={type} onChange={(e) => setType(e.target.value)}>
          {ACCOUNT_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
      ))}
      {field("Institution", <input className={inputCls} value={institution} onChange={(e) => setInstitution(e.target.value)} />)}
      <SubmitButton busy={isSubmitting} />
      {error && <p className="value-negative text-xs">{error.message}</p>}
    </form>
  );
}

export function GoalForm({ onSaved }: { onSaved?: () => void }) {
  const { submit, isSubmitting, error } = useSubmit("/goals", "POST");
  const [name, setName] = useState("");
  const [target_amount, setTarget] = useState("");
  const [target_date, setDate] = useState("");
  const [start_date, setStart] = useState("");
  return (
    <form
      className="flex flex-col gap-2"
      onSubmit={async (e) => {
        e.preventDefault();
        await submit({
          name,
          target_amount: Number(target_amount) || 0,
          target_date,
          start_date: start_date || new Date().toISOString().slice(0, 10),
        });
        onSaved?.();
      }}
    >
      {field("Name", <input className={inputCls} required value={name} onChange={(e) => setName(e.target.value)} />)}
      {field("Target amount", <input className={inputCls} type="number" value={target_amount} onChange={(e) => setTarget(e.target.value)} />)}
      {field("Target date", <input className={inputCls} type="date" value={target_date} onChange={(e) => setDate(e.target.value)} />)}
      {field("Start date (baseline)", <input className={inputCls} type="date" value={start_date} onChange={(e) => setStart(e.target.value)} />)}
      <p className="text-[11px] text-racing-silver">current_amount is entered manually later and can go stale.</p>
      <SubmitButton busy={isSubmitting} />
      {error && <p className="value-negative text-xs">{error.message}</p>}
    </form>
  );
}

export function InsuranceForm({ onSaved }: { onSaved?: () => void }) {
  const { submit, isSubmitting, error } = useSubmit("/insurance", "POST");
  const [type, setType] = useState<string>(INSURANCE_TYPES[0]);
  const [provider, setProvider] = useState("");
  const [coverage_amount, setCover] = useState("");
  const [premium, setPremium] = useState("");
  return (
    <form
      className="flex flex-col gap-2"
      onSubmit={async (e) => {
        e.preventDefault();
        await submit({
          type,
          provider,
          coverage_amount: Number(coverage_amount) || 0,
          premium: Number(premium) || 0,
        });
        onSaved?.();
      }}
    >
      {field("Type", (
        <select className={inputCls} value={type} onChange={(e) => setType(e.target.value)}>
          {INSURANCE_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
      ))}
      {field("Provider", <input className={inputCls} value={provider} onChange={(e) => setProvider(e.target.value)} />)}
      {field("Coverage", <input className={inputCls} type="number" value={coverage_amount} onChange={(e) => setCover(e.target.value)} />)}
      {field("Premium", <input className={inputCls} type="number" value={premium} onChange={(e) => setPremium(e.target.value)} />)}
      <SubmitButton busy={isSubmitting} />
      {error && <p className="value-negative text-xs">{error.message}</p>}
    </form>
  );
}

export function SalaryForm({ onSaved }: { onSaved?: () => void }) {
  const { submit, isSubmitting, error } = useSubmit("/salary", "POST");
  const [monthly_gross, setGross] = useState("");
  const [monthly_net, setNet] = useState("");
  const [effective_date, setEff] = useState("");
  return (
    <form
      className="flex flex-col gap-2"
      onSubmit={async (e) => {
        e.preventDefault();
        await submit({
          monthly_gross: Number(monthly_gross) || 0,
          monthly_net: Number(monthly_net) || 0,
          effective_date: effective_date || new Date().toISOString().slice(0, 10),
        });
        onSaved?.();
      }}
    >
      {field("Monthly gross", <input className={inputCls} type="number" value={monthly_gross} onChange={(e) => setGross(e.target.value)} />)}
      {field("Monthly net", <input className={inputCls} type="number" value={monthly_net} onChange={(e) => setNet(e.target.value)} />)}
      {field("Effective date", <input className={inputCls} type="date" value={effective_date} onChange={(e) => setEff(e.target.value)} />)}
      <p className="text-[11px] text-racing-silver">A raise is a new record — history is never edited.</p>
      <SubmitButton busy={isSubmitting} />
      {error && <p className="value-negative text-xs">{error.message}</p>}
    </form>
  );
}

export function HoldingForm({ onSaved, accountId = 1 }: { onSaved?: () => void; accountId?: number }) {
  const { submit, isSubmitting, error } = useSubmit("/import/manual", "POST");
  const [symbol, setSymbol] = useState("");
  const [name, setName] = useState("");
  const [type, setType] = useState<string>(HOLDING_TYPES[0]);
  const [units, setUnits] = useState("");
  const [cost_per_unit, setCost] = useState("");
  const isUnpriceable = type === "bond" || type === "other";
  return (
    <form
      className="flex flex-col gap-2"
      onSubmit={async (e) => {
        e.preventDefault();
        await submit({
          entity: "holding",
          account_id: accountId,
          symbol,
          name,
          type,
          units: Number(units) || 0,
          cost_per_unit: cost_per_unit === "" ? null : Number(cost_per_unit),
        });
        onSaved?.();
      }}
    >
      {field("Symbol", <input className={inputCls} required value={symbol} onChange={(e) => setSymbol(e.target.value)} />)}
      {field("Name", <input className={inputCls} value={name} onChange={(e) => setName(e.target.value)} />)}
      {field("Type", (
        <select className={inputCls} value={type} onChange={(e) => setType(e.target.value)}>
          {HOLDING_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
      ))}
      {field("Units", <input className={inputCls} type="number" value={units} onChange={(e) => setUnits(e.target.value)} />)}
      {field(
        isUnpriceable ? "Manual price (bond/other)" : "Cost per unit",
        <input className={inputCls} type="number" value={cost_per_unit} onChange={(e) => setCost(e.target.value)} />
      )}
      <SubmitButton busy={isSubmitting} />
      {error && <p className="value-negative text-xs">{error.message}</p>}
    </form>
  );
}

export function DebtForm({ onSaved }: { onSaved?: () => void }) {
  const { submit, isSubmitting, error } = useSubmit("/import/manual", "POST");
  const [lender, setLender] = useState("");
  const [type, setType] = useState("personal_loan");
  const [outstanding, setOut] = useState("");
  const [interest_rate, setRate] = useState("");
  const [emi, setEmi] = useState("");
  return (
    <form
      className="flex flex-col gap-2"
      onSubmit={async (e) => {
        e.preventDefault();
        await submit({
          entity: "debt",
          lender,
          type,
          outstanding: Number(outstanding) || 0,
          interest_rate: Number(interest_rate) || 0,
          emi: Number(emi) || 0,
        });
        onSaved?.();
      }}
    >
      {field("Lender", <input className={inputCls} required value={lender} onChange={(e) => setLender(e.target.value)} />)}
      {field("Type", <input className={inputCls} value={type} onChange={(e) => setType(e.target.value)} />)}
      {field("Outstanding", <input className={inputCls} type="number" value={outstanding} onChange={(e) => setOut(e.target.value)} />)}
      {field("Interest rate %", <input className={inputCls} type="number" value={interest_rate} onChange={(e) => setRate(e.target.value)} />)}
      {field("EMI", <input className={inputCls} type="number" value={emi} onChange={(e) => setEmi(e.target.value)} />)}
      <SubmitButton busy={isSubmitting} />
      {error && <p className="value-negative text-xs">{error.message}</p>}
    </form>
  );
}
