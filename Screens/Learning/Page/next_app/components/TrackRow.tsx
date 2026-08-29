"use client";

interface TrackRowProps {
  name: string;
  status: string;
  progress: number;
}

export default function TrackRow({ name, status, progress }: TrackRowProps) {
  const pct = Math.max(0, Math.min(100, Math.round(progress * 100)));

  return (
    <div className="border border-term-border rounded p-3 flex items-center justify-between gap-4">
      <div>
        <div className="text-term-fg">{name}</div>
        <div className="text-xs text-term-dim">{status}</div>
      </div>

      <div className="w-32 h-2 bg-term-border rounded overflow-hidden">
        <div className="h-2 bg-term-green" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}
