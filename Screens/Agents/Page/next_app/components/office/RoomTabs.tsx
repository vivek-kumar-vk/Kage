"use client";

import type { OfficeDepartment } from "../../lib/office";

export default function RoomTabs({
  departments,
  selected,
  onSelect,
}: {
  departments: OfficeDepartment[];
  selected: string;
  onSelect: (id: string) => void;
}) {
  const tabs = [{ id: "all", label: "All Floors", color: "#8B9099" }, ...departments];

  return (
    <nav className="flex items-center gap-1 overflow-x-auto border-b border-deck-line bg-deck-panel px-3 py-1.5">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          type="button"
          onClick={() => onSelect(tab.id)}
          className={`whitespace-nowrap border px-3 py-1 text-xs font-semibold uppercase tracking-widest transition-colors ${
            selected === tab.id
              ? "text-deck-text"
              : "border-transparent text-deck-dim hover:text-deck-text"
          }`}
          style={selected === tab.id ? { borderColor: tab.color, color: tab.color } : undefined}
        >
          {tab.label}
        </button>
      ))}
    </nav>
  );
}
