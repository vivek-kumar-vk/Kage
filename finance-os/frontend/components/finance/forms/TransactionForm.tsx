"use client";
import { useState } from "react";
import { useSubmit } from "@/lib/api";

// mirror of finance-os/shared/constants/categories.py (not on the FE import path)
const TRANSACTION_CATEGORIES = [
  "food", "transport", "utilities", "rent", "health", "entertainment",
  "shopping", "education", "investment", "income", "transfer",
  "debt_payment", "other",
] as const;
const TRANSACTION_TYPES = [
  "income", "expense", "transfer", "investment", "debt_payment",
] as const;

export default function TransactionForm({
  accountId = 1,
  onSaved,
}: {
  accountId?: number;
  onSaved?: () => void;
}) {
  const { submit, isSubmitting, error } = useSubmit("/import/manual", "POST");
  const [date, setDate] = useState("");
  const [description, setDescription] = useState("");
  const [amount, setAmount] = useState("");
  const [type, setType] = useState("expense");
  const [category, setCategory] = useState("food");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    await submit({
      entity: "transaction",
      account_id: accountId,
      date,
      description,
      amount: Number(amount),
      type,
      category,
    });
    setDate("");
    setDescription("");
    setAmount("");
    onSaved?.();
  }

  return (
    <form onSubmit={handleSubmit} className="grid grid-cols-2 gap-3 text-sm md:grid-cols-3">
      <label className="flex flex-col gap-1">
        <span className="text-racing-silver">Date</span>
        <input
          type="date"
          required
          value={date}
          onChange={(e) => setDate(e.target.value)}
          className="rounded bg-carbon-dark px-2 py-1"
        />
      </label>
      <label className="flex flex-col gap-1">
        <span className="text-racing-silver">Description</span>
        <input
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          className="rounded bg-carbon-dark px-2 py-1"
        />
      </label>
      <label className="flex flex-col gap-1">
        <span className="text-racing-silver">Amount</span>
        <input
          type="number"
          step="0.01"
          required
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          className="rounded bg-carbon-dark px-2 py-1 font-mono"
        />
      </label>
      <label className="flex flex-col gap-1">
        <span className="text-racing-silver">Type</span>
        <select
          value={type}
          onChange={(e) => setType(e.target.value)}
          className="rounded bg-carbon-dark px-2 py-1"
        >
          {TRANSACTION_TYPES.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
      </label>
      <label className="flex flex-col gap-1">
        <span className="text-racing-silver">Category</span>
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="rounded bg-carbon-dark px-2 py-1"
        >
          {TRANSACTION_CATEGORIES.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      </label>
      <div className="flex items-end">
        <button
          type="submit"
          disabled={isSubmitting}
          className="rounded bg-racing-blue px-3 py-1 text-carbon-dark disabled:opacity-50"
        >
          {isSubmitting ? "…" : "Add"}
        </button>
      </div>
      {error && <p className="col-span-full value-negative text-xs">{error.message}</p>}
    </form>
  );
}
