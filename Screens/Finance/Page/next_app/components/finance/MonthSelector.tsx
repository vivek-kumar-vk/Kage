"use client";
import { useEffect, useRef, useState } from "react";
import { useMonthPicker } from "@/lib/useOverviewScope";
import type { TrendPoint } from "@/lib/types";

interface Props {
  trend: TrendPoint[] | undefined;
  /** Only the Overview tab actually scopes on this — elsewhere it's a plain
   * read-only "LIVE" pill so a click can't imply a control that does nothing. */
  interactive: boolean;
}

function Chevron() {
  return (
    <svg width="8" height="8" viewBox="0 0 8 8" aria-hidden="true" className="shrink-0">
      <path d="M1 2.5 L4 5.5 L7 2.5" fill="none" stroke="currentColor" strokeWidth="1.3" />
    </svg>
  );
}

export default function MonthSelector({ trend, interactive }: Props) {
  const { months, selected, setThrough } = useMonthPicker(trend);
  const [open, setOpen] = useState(false);
  const [highlight, setHighlight] = useState(0);
  const rootRef = useRef<HTMLDivElement | null>(null);

  const options = [{ date: null as string | null, label: "LIVE" }, ...months];
  const selectedIndex = Math.max(
    0,
    options.findIndex((o) => o.date === selected)
  );
  const currentLabel = options[selectedIndex]?.label ?? "LIVE";

  useEffect(() => {
    if (open) setHighlight(selectedIndex);
  }, [open, selectedIndex]);

  useEffect(() => {
    if (!open) return;
    function onClick(e: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [open]);

  if (!interactive) {
    return <div className="pill">{currentLabel}</div>;
  }

  const pick = (index: number) => {
    setThrough(options[index]?.date ?? null);
    setOpen(false);
  };

  return (
    <div ref={rootRef} className="month-select">
      <button
        type="button"
        className={`pill month-select-trigger${selected ? " historical" : ""}`}
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        onKeyDown={(e) => {
          if (e.key === "ArrowDown" || e.key === "Enter") {
            e.preventDefault();
            setOpen(true);
          }
        }}
      >
        {selected ? <span aria-hidden="true">↺</span> : null}
        {currentLabel}
        <Chevron />
      </button>

      {open ? (
        <ul
          role="listbox"
          className="month-select-dropdown"
          tabIndex={-1}
          onKeyDown={(e) => {
            if (e.key === "Escape") {
              e.preventDefault();
              setOpen(false);
            } else if (e.key === "ArrowDown") {
              e.preventDefault();
              setHighlight((h) => Math.min(h + 1, options.length - 1));
            } else if (e.key === "ArrowUp") {
              e.preventDefault();
              setHighlight((h) => Math.max(h - 1, 0));
            } else if (e.key === "Enter") {
              e.preventDefault();
              pick(highlight);
            }
          }}
        >
          {options.map((option, index) => (
            <li key={option.date ?? "live"}>
              <button
                type="button"
                role="option"
                aria-selected={index === selectedIndex}
                className={`month-select-option${index === selectedIndex ? " selected" : ""}${
                  index === highlight ? " highlighted" : ""
                }${index === 1 ? " month-select-divider" : ""}`}
                onMouseEnter={() => setHighlight(index)}
                onClick={() => pick(index)}
              >
                {option.label}
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
