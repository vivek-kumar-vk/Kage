"use client";
import { useState } from "react";
import { Card } from "@/components/finance/Card";
import { FormModal } from "@/components/finance/FormModal";
import { useFinanceData } from "@/lib/api";
import {
  AccountForm,
  GoalForm,
  InsuranceForm,
  SalaryForm,
} from "@/components/finance/forms/EntityForms";

const TABS = ["accounts", "goals", "insurance", "salary"] as const;
type Tab = (typeof TABS)[number];

function Section({
  title,
  path,
  renderRow,
  form: FormComp,
}: {
  title: string;
  path: string;
  renderRow: (row: Record<string, unknown>) => string;
  form: React.ComponentType<{ onSaved?: () => void }>;
}) {
  const { data, isLoading, error, refetch } = useFinanceData<Record<string, unknown>[]>(path);
  const [open, setOpen] = useState(false);
  return (
    <Card title={title} isLoading={isLoading} error={error}>
      <button
        className="mb-3 rounded bg-racing-blue px-3 py-1 text-sm text-carbon-dark"
        onClick={() => setOpen(true)}
      >
        + Add
      </button>
      {!data || data.length === 0 ? (
        <p className="text-sm text-racing-silver">Nothing here yet.</p>
      ) : (
        <ul className="space-y-1 text-sm">
          {data.map((row, i) => (
            <li key={(row.id as number) ?? i} className="border-t border-carbon-light py-1">
              {renderRow(row)}
            </li>
          ))}
        </ul>
      )}
      <FormModal open={open} onClose={() => setOpen(false)} title={`Add ${title.toLowerCase()}`}>
        <FormComp
          onSaved={() => {
            setOpen(false);
            refetch();
          }}
        />
      </FormModal>
    </Card>
  );
}

export default function SettingsPage() {
  const [tab, setTab] = useState<Tab>("accounts");
  return (
    <div>
      <div className="mb-4 flex gap-2 text-sm">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`rounded px-3 py-1 capitalize ${
              tab === t ? "bg-racing-red text-white" : "bg-carbon-light text-racing-silver"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === "accounts" && (
        <Section
          title="Accounts"
          path="/accounts"
          form={AccountForm}
          renderRow={(r) => `${r.name} · ${r.type}${r.institution ? ` · ${r.institution}` : ""}`}
        />
      )}
      {tab === "goals" && (
        <Section
          title="Goals"
          path="/goals"
          form={GoalForm}
          renderRow={(r) => `${r.name} · target ${r.target_amount ?? "—"} by ${r.target_date ?? "—"}`}
        />
      )}
      {tab === "insurance" && (
        <Section
          title="Insurance"
          path="/insurance"
          form={InsuranceForm}
          renderRow={(r) => `${r.type} · ${r.provider ?? "—"} · cover ${r.coverage_amount ?? "—"}`}
        />
      )}
      {tab === "salary" && (
        <Section
          title="Salary"
          path="/salary"
          form={SalaryForm}
          renderRow={(r) => `net ${r.monthly_net ?? "—"} · from ${r.effective_date ?? "—"}`}
        />
      )}
    </div>
  );
}
