"use client";
import { useState } from "react";
import { Card } from "@/components/finance/Card";
import { useSubmit } from "@/lib/api";

interface SimResult {
  net_worth: { current: number; projected: number; delta: number };
  goal_probability: { current: number; projected: number; delta: number };
  debt: { months_saved: number; interest_saved: number };
}

function inr(n: number) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(n);
}

function Lever({
  label,
  value,
  onChange,
  max,
  step,
  suffix = "",
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  max: number;
  step: number;
  suffix?: string;
}) {
  return (
    <label className="flex flex-col gap-1 text-sm">
      <span className="flex justify-between text-racing-silver">
        <span>{label}</span>
        <span className="font-mono text-gray-200">
          {value}
          {suffix}
        </span>
      </span>
      <input
        type="range"
        min={0}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="accent-racing-blue"
      />
    </label>
  );
}

export default function ScenarioPage() {
  const { submit, isSubmitting, error } = useSubmit<Record<string, number>, SimResult>(
    "/scenario/simulate",
    "POST"
  );
  const [extra, setExtra] = useState(5000);
  const [salary, setSalary] = useState(0);
  const [bonus, setBonus] = useState(0);
  const [sip, setSip] = useState(0);
  const [result, setResult] = useState<SimResult | null>(null);

  async function run() {
    const r = await submit({
      extra_debt_payment: extra,
      monthly_salary_delta: salary,
      one_off_bonus: bonus,
      sip_step_up_pct: sip,
    });
    setResult(r);
  }

  return (
    <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
      <Card title="Scenario levers" error={error}>
        <div className="space-y-4">
          <Lever label="Extra debt payment / mo" value={extra} onChange={setExtra} max={50000} step={1000} />
          <Lever label="Monthly salary change" value={salary} onChange={setSalary} max={100000} step={2000} />
          <Lever label="One-off bonus" value={bonus} onChange={setBonus} max={1000000} step={25000} />
          <Lever label="SIP step-up / mo" value={sip} onChange={setSip} max={20000} step={1000} />
          <button
            onClick={run}
            disabled={isSubmitting}
            className="rounded bg-racing-blue px-4 py-1 text-sm text-carbon-dark disabled:opacity-50"
          >
            {isSubmitting ? "Simulating…" : "Simulate"}
          </button>
        </div>
      </Card>

      <Card title="Projection">
        {!result ? (
          <p className="text-sm text-racing-silver">Set the levers and run a simulation.</p>
        ) : (
          <ul className="space-y-2 text-sm">
            <li className="flex justify-between">
              <span className="text-racing-silver">Net worth</span>
              <span className="font-mono">
                {inr(result.net_worth.current)} →{" "}
                <span className="value-positive">{inr(result.net_worth.projected)}</span>
              </span>
            </li>
            <li className="flex justify-between">
              <span className="text-racing-silver">Net-worth delta</span>
              <span className="value-positive font-mono">{inr(result.net_worth.delta)}</span>
            </li>
            <li className="flex justify-between">
              <span className="text-racing-silver">Goal probability</span>
              <span className="font-mono">
                {result.goal_probability.current}% → {result.goal_probability.projected}%
              </span>
            </li>
            <li className="flex justify-between">
              <span className="text-racing-silver">Debt: months saved</span>
              <span className="font-mono">{result.debt.months_saved}</span>
            </li>
            <li className="flex justify-between">
              <span className="text-racing-silver">Debt: interest saved</span>
              <span className="value-positive font-mono">{inr(result.debt.interest_saved)}</span>
            </li>
          </ul>
        )}
        {/* Visualization planned: before/after projection bars (net worth, goal probability) */}
      </Card>
    </div>
  );
}
