"use client";

/** Right column, top module - the EMAIL card (AGENTS.md D22). Live and
    honest: a read-only Gmail sync runs in the menu backend; this card
    renders only what that store really holds.

    - the window is switchable: 1h / 4h / 12h / 24h
    - the AI buckets (newsletters / finance / jobs / priority) each show
      their count and latest subject; the old static FLAGGED list is gone
    - TODAY'S MIX is the real proportion of the chosen window
    - the footer names the real sync time, the owner and the account
    - every non-working state says so: not connected, needs the OAuth
      client file, consent in progress, token expired, brain offline
      (CLAUDE.md Rule 8). EMAIL_DEMO=1 shows a labelled simulation. */

import { useCallback, useEffect, useRef, useState } from "react";

const WINDOWS = [1, 4, 12, 24];

const COLOURS: Record<string, string> = {
  newsletters: "#ff7a00",
  finance: "#c98a3d",
  jobs: "#9a9a9a",
  priority: "#e10600", // act-now only (CLAUDE.md Rule 9)
  other: "#2e2e2e",
  uncategorised: "#4a4a4a",
};

type Latest = { subject: string; reason?: string; received_at: string };
type Bucket = {
  key: string;
  label: string;
  count: number;
  latest: Latest | null;
};
type Summary = {
  state:
    | "ok"
    | "not_connected"
    | "needs_credentials"
    | "needs_install"
    | "auth_error"
    | "connecting"
    | "error";
  demo?: boolean;
  problem?: string;
  hours: number;
  total?: number;
  account?: string;
  owner?: string;
  synced_at?: string;
  syncing?: boolean;
  connecting?: boolean;
  categories?: Bucket[];
  other?: number;
  uncategorised?: number;
  brain?: { state: string; model: string; detail?: string; error?: string };
  digest_note?: string;
  credentials_path?: string;
  setup_doc?: string;
};

function EnvelopeIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" aria-hidden="true" className="shrink-0 text-dim">
      <rect x="3" y="5" width="18" height="14" rx="1.5" fill="none" stroke="currentColor" strokeWidth="1.8" />
      <path d="M3.5 6.5 12 13l8.5-6.5" fill="none" stroke="currentColor" strokeWidth="1.8" />
    </svg>
  );
}

function ageOf(iso: string, now: number): string {
  const s = Math.max(0, (now - Date.parse(iso)) / 1000);
  if (s < 3600) return `${Math.max(1, Math.round(s / 60))}m`;
  if (s < 172800) return `${Math.round(s / 3600)}h`;
  return `${Math.round(s / 86400)}d`;
}

function clockOf(iso?: string): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function agoOf(iso?: string, now = Date.now()): string {
  if (!iso) return "never";
  return `${ageOf(iso, now)} ago`;
}

export function EmailPanel() {
  const [hours, setHours] = useState(24);
  const [data, setData] = useState<Summary | null>(null);
  const [fetchFailed, setFetchFailed] = useState(false);
  const [now, setNow] = useState(() => Date.now());
  const alive = useRef(true);

  const load = useCallback(async (h: number) => {
    try {
      const res = await fetch(`/api/main_menu/email/summary?hours=${h}`, {
        headers: { accept: "application/json" },
      });
      const body = (await res.json()) as Summary;
      if (alive.current) {
        setData(body);
        setFetchFailed(false);
      }
    } catch {
      if (alive.current) setFetchFailed(true);
    }
  }, []);

  useEffect(() => {
    alive.current = true;
    load(hours);
    return () => {
      alive.current = false;
    };
  }, [hours, load]);

  // Poll: normally once a minute; fast while a sync or the consent flow
  // is running so the card flips over the moment either lands.
  useEffect(() => {
    const busy = data?.syncing || data?.state === "connecting";
    const ms = busy ? 3000 : 60000;
    const t = setInterval(() => load(hours), ms);
    return () => clearInterval(t);
  }, [data?.syncing, data?.state, hours, load]);

  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 30000);
    return () => clearInterval(t);
  }, []);

  async function post(path: string) {
    try {
      await fetch(path, { method: "POST" });
    } catch {
      /* the next poll tells the truth if it failed */
    }
    setTimeout(() => load(hours), 800);
  }

  const ok = data?.state === "ok";
  const buckets = data?.categories ?? [];
  const mixSegments = [
    ...buckets.map((b) => ({ key: b.key, label: b.label, count: b.count })),
    { key: "other", label: "OTHER", count: data?.other ?? 0 },
    ...(data?.uncategorised
      ? [{ key: "uncategorised", label: "UNSORTED", count: data.uncategorised }]
      : []),
  ];
  const mixTotal = mixSegments.reduce((n, s) => n + s.count, 0) || 1;

  const syncLabel = data?.syncing
    ? "syncing…"
    : ok
      ? `synced ${agoOf(data?.synced_at, now)}`
      : data?.state === "connecting"
        ? "awaiting Google consent…"
        : "not synced";

  return (
    <section aria-label="Email" className="rubric-panel p-4">
      <header className="mb-3 flex items-center justify-between">
        <p className="rubric-label flex items-center gap-2">
          <EnvelopeIcon />
          Email
        </p>
        <span className="flex items-center gap-2">
          {data?.demo && (
            <span className="num rounded-full border border-[#ff7a00] px-1.5 py-px text-[7px] text-[#ff7a00]">
              DEMO
            </span>
          )}
          <button
            type="button"
            onClick={() => post("/api/main_menu/email/refresh")}
            className="rubric-sub cursor-pointer text-[8px] normal-case tracking-normal text-dim hover:text-white"
            title="Sync Gmail now"
          >
            {syncLabel}
          </button>
        </span>
      </header>

      {/* ----- big count ----- */}
      <div className="flex items-baseline gap-2">
        <span className="num rubric-accent text-[26px] font-semibold leading-none">
          {ok ? (data?.total ?? 0) : "—"}
        </span>
        <span className="rubric-sub text-[9px]">
          Emails
          <br />
          Past {hours}h
        </span>
      </div>

      {/* ----- window chips ----- */}
      <div className="mt-2.5 flex items-center gap-1.5">
        {WINDOWS.map((w) => (
          <button
            key={w}
            type="button"
            onClick={() => setHours(w)}
            className={`num cursor-pointer rounded-full border px-2 py-0.5 text-[8px] ${
              w === hours
                ? "border-[#ff7a00] text-[#ff7a00]"
                : "border-[#2a2a2a] text-dim hover:border-[#555]"
            }`}
          >
            {w}H
          </button>
        ))}
      </div>

      {/* ----- states that have no mail behind them yet ----- */}
      {!ok && (
        <div className="mt-3 border-t border-[#232323] pt-3">
          <p className="text-[11px] leading-snug text-white">{stateHeadline(data)}</p>
          {data?.problem && data.state !== "needs_credentials" && (
            <p className="mt-1 text-[9px] leading-snug text-dim">{data.problem}</p>
          )}
          {data?.state === "needs_credentials" && data.credentials_path && (
            <>
              <p className="num mt-1 break-all text-[8px] leading-snug text-[#c98a3d]">
                {data.credentials_path}
              </p>
              <p className="mt-1 text-[9px] text-dim">
                see EMAIL_SETUP.md &middot; the card wakes up the moment it is saved
              </p>
            </>
          )}
          {(data?.state === "needs_credentials" || data?.state === "not_connected") && (
            <button
              type="button"
              onClick={() => post("/api/main_menu/email/connect")}
              disabled={data?.state === "needs_credentials"}
              className="num mt-2 cursor-pointer rounded-full border border-[#ff7a00] px-3 py-1 text-[8px] text-[#ff7a00] hover:bg-[#ff7a00]/10 disabled:cursor-not-allowed disabled:border-[#333] disabled:text-dim"
            >
              CONNECT GMAIL
            </button>
          )}
          {data?.state === "auth_error" && (
            <button
              type="button"
              onClick={() => post("/api/main_menu/email/connect")}
              className="num mt-2 cursor-pointer rounded-full border border-[#ff7a00] px-3 py-1 text-[8px] text-[#ff7a00] hover:bg-[#ff7a00]/10"
            >
              RECONNECT
            </button>
          )}
          {fetchFailed && (
            <p className="num mt-2 text-[8px] text-dim">
              the menu backend did not answer - is :8000 up?
            </p>
          )}
        </div>
      )}

      {/* ----- AI buckets ----- */}
      {ok && (
        <>
          <p className="rubric-sub mt-3 text-[8px]">Sorted by the agent</p>
          <ul className="mt-1.5 flex flex-col">
            {buckets.map((b) => (
              <li
                key={b.key}
                className="border-t border-[#232323] py-2 first:border-t-0"
              >
                <div className="flex items-center gap-2">
                  <span
                    className="h-1.5 w-1.5 shrink-0 rounded-full"
                    style={{ background: COLOURS[b.key] ?? "#555" }}
                  />
                  <span className="rubric-sub flex-1 text-[8px]">{b.label}</span>
                  <span className="num text-[10px] text-white">{b.count}</span>
                </div>
                {b.latest && (
                  <div
                    className="mt-0.5 flex items-baseline gap-2 pl-3.5"
                    title={b.latest.reason ? `${b.latest.subject} — ${b.latest.reason}` : b.latest.subject}
                  >
                    <span className="min-w-0 flex-1 truncate text-[11px] text-white">
                      {b.latest.subject}
                    </span>
                    {b.key === "priority" && b.latest.reason && (
                      <span className="rubric-sub hidden truncate text-[7px] normal-case tracking-normal text-dim sm:block">
                        {b.latest.reason}
                      </span>
                    )}
                    <span className="num shrink-0 text-[10px] text-dim">
                      {ageOf(b.latest.received_at, now)}
                    </span>
                  </div>
                )}
              </li>
            ))}
          </ul>

          {/* ----- today's mix ----- */}
          <p className="rubric-sub mt-3 text-[8px]">Today&rsquo;s Mix</p>
          <div className="mt-1.5 flex h-1.5 overflow-hidden rounded-full">
            {mixSegments.map(
              (s) =>
                s.count > 0 && (
                  <div
                    key={s.key}
                    style={{
                      width: `${(s.count / mixTotal) * 100}%`,
                      background: COLOURS[s.key] ?? "#555",
                    }}
                  />
                ),
            )}
          </div>
          <div className="mt-1.5 flex flex-wrap gap-x-3 gap-y-1">
            {mixSegments.map((s) => (
              <span key={s.key} className="flex items-center gap-1">
                <span
                  className="h-1.5 w-1.5 rounded-full"
                  style={{ background: COLOURS[s.key] ?? "#555" }}
                />
                <span className="rubric-sub text-[7px]">
                  {s.label} &middot; {s.count}
                </span>
              </span>
            ))}
          </div>

          {(data?.uncategorised ?? 0) > 0 && (
            <p className="rubric-sub mt-1.5 text-[7px] normal-case tracking-normal text-dim">
              {data?.uncategorised} waiting for the agent&rsquo;s next pass
              {data?.brain?.error ? ` — ${data.brain.error}` : ""}
            </p>
          )}
          {data?.brain?.state === "missing" && (
            <p className="rubric-sub mt-1.5 text-[7px] normal-case tracking-normal text-dim">
              AI sorting offline — {data.brain.detail}
            </p>
          )}
          {data?.digest_note && (
            <p className="rubric-sub mt-1 text-[7px] normal-case tracking-normal text-dim">
              {data.digest_note}
            </p>
          )}
        </>
      )}

      {/* ----- footer ----- */}
      <p className="num mt-3 border-t border-[#232323] pt-2 text-[8px] text-dim">
        SYNCED {clockOf(ok ? data?.synced_at : undefined)} &middot;{" "}
        {ok ? data?.owner : "—"} &middot; {ok ? data?.account : "unconnected"}
      </p>
    </section>
  );
}

function stateHeadline(data: Summary | null): string {
  switch (data?.state) {
    case "needs_credentials":
      return "One file away from live:";
    case "not_connected":
      return "Gmail not connected yet.";
    case "connecting":
      return "Finish the consent in the Google tab that just opened.";
    case "auth_error":
      return "The Gmail token stopped working.";
    case "needs_install":
      return "The Gmail client libraries are not installed.";
    case "error":
      return "The last sync failed.";
    default:
      return "Waiting for the first sync…";
  }
}
