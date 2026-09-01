"use client";

interface StatsBarProps {
  label: string;
  value: number;
  target: number;
}

export default function StatsBar({ label, value, target }: StatsBarProps) {
  const pct = target <= 0 ? 0 : Math.max(0, Math.min(100, Math.round((value / target) * 100)));

  return (
    <div>
      <div className="flex justify-between text-xs text-term-dim mb-1">
        <span>{label}</span>
        <span>
          {value} / {target}
        </span>
      </div>

      <div className="w-full h-2 bg-term-border rounded overflow-hidden">
        <div className="h-2 bg-term-green" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}
