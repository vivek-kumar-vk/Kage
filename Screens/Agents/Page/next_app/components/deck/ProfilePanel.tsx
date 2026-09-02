"use client";

import { useCallback, useEffect, useState } from "react";
import type { AgentView, OfficeAgent, OfficeDepartment } from "../../lib/office";
import PixelAvatar from "./PixelAvatar";

interface FileMeta {
  name: string;
  size: number;
  updated: string | null;
}

interface FilePayload {
  state: string;
  file: FileMeta & { content: string };
}

const CANONICAL: Record<string, string> = {
  "identity.md": "# Identity\n\n(who this agent is — role, temperament, boundaries)\n",
  "context.md": "# Context\n\n(standing context the agent should know for every task)\n",
  "memory.md": "# Memory\n\n(durable notes carried across tasks)\n",
};

function relTime(iso: string | null) {
  if (!iso) return "—";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "—";
  const mins = Math.max(0, Math.round((Date.now() - then) / 60000));
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}

interface Props {
  agent: OfficeAgent;
  departments: OfficeDepartment[];
  states: Map<string, AgentView>;
  onClose: () => void;
}

/** Right drawer: profile + the agent's real files, editable in place (D17.4). */
export default function ProfilePanel({ agent, departments, states, onClose }: Props) {
  const [tab, setTab] = useState<"profile" | "files">("profile");

  const dept = departments.find((d) => d.id === agent.department);
  const accent = dept?.color ?? "#A08762";
  const view = states.get(agent.name);

  return (
    <section className="flex h-full min-h-0 flex-col">
      <header className="border-b-2 border-deck-line bg-deck-panel p-4">
        <div className="flex items-start justify-between gap-2">
          <div className="flex min-w-0 items-center gap-3">
            <PixelAvatar name={agent.name} color={accent} size={44} />
            <div className="min-w-0">
              <p className="truncate font-display text-base tracking-wide">
                {agent.name.replace(/_Agent$/, "")}
              </p>
              <p className="truncate text-xs text-deck-dim">{agent.role}</p>
            </div>
          </div>
          <button
            type="button"
            className="px-btn px-2 py-1"
            onClick={onClose}
            aria-label="Close profile"
            title="Close (Esc)"
          >
            ✕
          </button>
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-2">
          <span className="px-chip" style={{ color: accent }}>
            <span className="inline-block h-2 w-2" style={{ background: accent }} aria-hidden="true" />
            {dept?.label ?? agent.department}
          </span>
          <span className="px-chip">{agent.tier}</span>
          {agent.parent ? <span className="px-chip">reports to {agent.parent}</span> : null}
        </div>

        <div className="mt-3 flex gap-1">
          <button
            type="button"
            className={`profile-tab${tab === "profile" ? " profile-tab-active" : ""}`}
            onClick={() => setTab("profile")}
          >
            PROFILE
          </button>
          <button
            type="button"
            className={`profile-tab${tab === "files" ? " profile-tab-active" : ""}`}
            onClick={() => setTab("files")}
          >
            FILES
          </button>
        </div>
      </header>

      {tab === "profile" ? (
        <ProfileTab agent={agent} accent={accent} view={view} />
      ) : (
        <FilesTab agentName={agent.name} />
      )}
    </section>
  );
}

function ProfileTab({
  agent,
  accent,
  view,
}: {
  agent: OfficeAgent;
  accent: string;
  view?: AgentView;
}) {
  const rows: [string, string][] = [
    ["status", view?.status === "working" ? "working" : view?.status === "stuck" ? "needs attention" : "idle"],
    ["current task", view?.text ?? "—"],
    ["last activity", view?.at ? relTime(new Date(view.at).toISOString()) : "—"],
    ["department", agent.department],
    ["tier", agent.tier],
    ["reports to", agent.parent ?? "—"],
    ["dm room", agent.room_id],
  ];

  return (
    <div className="deck-scroll flex min-h-0 flex-1 flex-col gap-3 p-4">
      <p
        className="px-corners p-3 text-sm"
        style={{ background: "#FFF9EC", color: "var(--deck-text)" }}
      >
        {view?.text && view.status !== "idle" ? (
          <>
            <span className="section-label block">On the stage</span>
            <span className="mt-1 block">{view.text}</span>
            {view.sim ? <span className="sim-tag mt-2 inline-block">SIMULATED</span> : null}
          </>
        ) : (
          <>
            <span className="section-label block">On the stage</span>
            <span className="mt-1 block text-deck-dim">
              Desk is empty — {agent.name.replace(/_Agent$/, "")} appears when a task
              arrives.
            </span>
          </>
        )}
      </p>

      <dl className="text-sm">
        {rows.map(([label, value]) => (
          <div
            key={label}
            className="flex items-baseline justify-between gap-3 border-b border-deck-line py-2"
          >
            <dt className="section-label shrink-0">{label}</dt>
            <dd
              className="truncate text-right"
              style={label === "status" && view?.status === "stuck" ? { color: "var(--deck-alert)" } : undefined}
            >
              {value}
            </dd>
          </div>
        ))}
      </dl>

      <p className="text-xs text-deck-dim">
        Live replies and task runs land with the V2 model wiring (PLAN.md item 4).
        The FILES tab edits this agent&apos;s real profile files on disk.
      </p>
    </div>
  );
}

function FilesTab({ agentName }: { agentName: string }) {
  const [files, setFiles] = useState<FileMeta[] | null>(null);
  const [openFile, setOpenFile] = useState<string | null>(null);
  const [content, setContent] = useState("");
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const base = `/api/agents/agents/${encodeURIComponent(agentName)}/files`;

  const loadList = useCallback(() => {
    let cancelled = false;
    fetch(base)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json() as Promise<{ files: FileMeta[] }>;
      })
      .then((data) => {
        if (!cancelled) {
          setFiles(data.files ?? []);
          setError(null);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "files failed");
          setFiles([]);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [base]);

  useEffect(() => {
    setFiles(null);
    setOpenFile(null);
    setDirty(false);
    return loadList();
  }, [loadList]);

  const open = useCallback(
    async (name: string) => {
      setBusy(true);
      setError(null);
      try {
        const res = await fetch(`${base}/${encodeURIComponent(name)}`);
        const data = (await res.json()) as FilePayload & { problem?: string };
        if (!res.ok) throw new Error(data.problem ?? `HTTP ${res.status}`);
        setOpenFile(name);
        setContent(data.file.content);
        setDirty(false);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "open failed");
      } finally {
        setBusy(false);
      }
    },
    [base]
  );

  const create = useCallback(
    async (name: string) => {
      const template = CANONICAL[name] ?? "";
      setBusy(true);
      setError(null);
      try {
        const res = await fetch(`${base}/${encodeURIComponent(name)}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json", Accept: "application/json" },
          body: JSON.stringify({ content: template }),
        });
        const data = (await res.json()) as { problem?: string };
        if (!res.ok) throw new Error(data.problem ?? `HTTP ${res.status}`);
        loadList();
        await open(name);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "create failed");
      } finally {
        setBusy(false);
      }
    },
    [base, loadList, open]
  );

  const save = useCallback(async () => {
    if (!openFile) return;
    setBusy(true);
    setError(null);
    try {
      const res = await fetch(`${base}/${encodeURIComponent(openFile)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ content }),
      });
      const data = (await res.json()) as { problem?: string };
      if (!res.ok) throw new Error(data.problem ?? `HTTP ${res.status}`);
      setDirty(false);
      loadList();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "save failed");
    } finally {
      setBusy(false);
    }
  }, [base, content, openFile, loadList]);

  const fileNames = new Set((files ?? []).map((f) => f.name));
  const missing = Object.keys(CANONICAL).filter((name) => !fileNames.has(name));

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="deck-scroll max-h-44 shrink-0 border-b-2 border-deck-line p-2">
        {files === null ? (
          <p className="section-label px-2 py-1">Listing files…</p>
        ) : (
          <>
            {files.map((file) => (
              <button
                key={file.name}
                type="button"
                className={`files-row${openFile === file.name ? " files-row-active" : ""}`}
                onClick={() => void open(file.name)}
              >
                <span className="truncate">{file.name}</span>
                <span className="shrink-0 text-[10px] text-deck-dim">
                  {file.size} B · {relTime(file.updated)}
                </span>
              </button>
            ))}
            {files.length === 0 ? (
              <p className="px-2 py-1 text-xs text-deck-dim">No editable files yet.</p>
            ) : null}
            {missing.length > 0 ? (
              <div className="flex flex-wrap gap-2 px-2 pt-2">
                <span className="section-label w-full">Create</span>
                {missing.map((name) => (
                  <button
                    key={name}
                    type="button"
                    className="px-btn text-[10px]"
                    onClick={() => void create(name)}
                    disabled={busy}
                  >
                    + {name}
                  </button>
                ))}
              </div>
            ) : null}
          </>
        )}
      </div>

      {openFile ? (
        <div className="flex min-h-0 flex-1 flex-col gap-2 p-2">
          <div className="flex items-center justify-between gap-2">
            <span className="font-mono text-xs text-deck-dim">
              {agentName}/{openFile}
              {dirty ? " ·" : ""}
            </span>
            <button
              type="button"
              className="px-btn px-btn-primary text-[11px]"
              onClick={() => void save()}
              disabled={busy || !dirty}
            >
              {busy ? "…" : "SAVE"}
            </button>
          </div>
          <textarea
            className="files-editor min-h-0 flex-1"
            value={content}
            onChange={(event) => {
              setContent(event.target.value);
              setDirty(true);
            }}
            spellCheck={false}
            aria-label={`Edit ${openFile}`}
          />
        </div>
      ) : (
        <p className="p-4 text-sm text-deck-dim">
          Pick a file to view or edit it — identity, context, memory and office
          metadata live in this agent&apos;s profile folder.
        </p>
      )}

      {error ? (
        <p className="m-2 px-2 py-1 text-xs" style={{ color: "var(--deck-alert)" }}>
          {error}
        </p>
      ) : null}
    </div>
  );
}
