"use client";

import { useEffect, useState } from "react";

interface LocalEngine {
  name: string;
  size_bytes: number | null;
}

/** Right column, middle module - "SKILLS DECK" in the reference image's
    card-grid layout, built around the one real "skill" INKY actually
    has today: the local Ollama engines this laptop can run
    (call_the_local_model.py). Names come from Ollama's own live
    /api/tags, never typed in (Rule 4) - Ollama not running reads as an
    honest empty deck, not a guessed one.

    The per-card switch is UI only for now, same "backend later" the
    owner asked for: it flips its own look and nothing else. The one
    real switch behind all local-model calls today is the single
    project-wide toggle in Shared_By_All_Agents/local_model_toggle.json
    (Models screen, Agents tab) - flipping a card here does not touch
    that file yet, and the caption says so rather than pretending it
    does (C12: no button that looks alive and does nothing silently). */
export function SkillsDeckPanel() {
  const [engines, setEngines] = useState<LocalEngine[] | null>(null);
  const [reachable, setReachable] = useState(true);
  const [on, setOn] = useState<Record<string, boolean>>({});

  useEffect(() => {
    let cancelled = false;
    fetch("/api/main_menu/local_ai")
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then((body: { reachable: boolean; engines: LocalEngine[] }) => {
        if (cancelled) return;
        setReachable(body.reachable);
        setEngines(body.engines);
        setOn(Object.fromEntries(body.engines.map((m) => [m.name, true])));
      })
      .catch(() => {
        if (!cancelled) {
          setReachable(false);
          setEngines([]);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const freshness = engines === null ? "empty" : engines.length > 0 ? "fresh" : "empty";

  return (
    <section
      aria-label="Skills deck"
      data-figure="skills-deck"
      data-fresh={freshness}
      className="agentic-panel p-3"
    >
      <header className="mb-2 flex items-baseline justify-between">
        <p className="agentic-label">Skills Deck</p>
        <span className="text-[10px] text-dim">local engines</span>
      </header>

      {engines === null && <p className="text-xs text-dim">asking Ollama&hellip;</p>}
      {engines !== null && !reachable && (
        <p className="text-xs text-amber">Ollama not reachable on this laptop at 127.0.0.1:11434</p>
      )}
      {engines !== null && reachable && engines.length === 0 && (
        <p className="text-xs text-dim">no local engines pulled yet</p>
      )}

      {engines !== null && engines.length > 0 && (
        <div className="grid grid-cols-2 gap-2">
          {engines.map((m) => (
            <div
              key={m.name}
              className="flex flex-col gap-2 rounded border border-[#262626] bg-[#1a1a1a] p-2"
            >
              <span className="num truncate text-[11px] text-white" title={m.name}>
                /{m.name}
              </span>
              <div className="flex items-center justify-between">
                <span className="text-[9px] uppercase tracking-wide text-dim">local &middot; ollama</span>
                <button
                  type="button"
                  role="switch"
                  aria-checked={!!on[m.name]}
                  aria-label={`toggle ${m.name} (UI only, not wired yet)`}
                  title="UI only - not wired to the real local-engine switch yet"
                  onClick={() => setOn((p) => ({ ...p, [m.name]: !p[m.name] }))}
                  className="relative h-4 w-8 shrink-0 rounded-full transition-colors"
                  style={{ background: on[m.name] ? "var(--agentic-amber, #ff7a00)" : "#333" }}
                >
                  <span
                    className="absolute top-0.5 h-3 w-3 rounded-full bg-white transition-all"
                    style={{ left: on[m.name] ? "18px" : "2px" }}
                  />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
      <p className="mt-2 text-[9px] leading-relaxed text-dim">
        names read live from Ollama &middot; the switch is UI only, not wired to a real on/off yet
      </p>
    </section>
  );
}
