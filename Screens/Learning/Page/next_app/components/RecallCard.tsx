"use client";

interface RecallCardProps {
  front: string;
  parts: string[];
  tag: string;
  tether?: string | null;
}

export default function RecallCard({ front, parts, tag, tether }: RecallCardProps) {
  return (
    <div className="border border-term-border rounded p-4">
      <div className="text-xs text-term-violet mb-2">[{tag}]</div>
      <div className="text-term-fg mb-3">{front}</div>

      <ul className="text-term-dim list-disc list-inside space-y-1">
        {parts.filter(Boolean).map((part, index) => (
          <li key={index}>{part}</li>
        ))}
      </ul>

      {tether ? <div className="mt-3 text-xs text-term-dim">tether: {tether}</div> : null}
    </div>
  );
}
