"use client";

import { useEffect, useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

interface AgentFile {
  path: string;
  kind: string;
  size_bytes: number;
}

const KIND_COLOUR: Record<string, string> = {
  Memory: "var(--agentic-amber, #ff7a00)",
  Prompts: "#7fd6ff",
  root: "#8B9099",
};

function colour_for(kind: string): string {
  return KIND_COLOUR[kind] ?? "#b48cff";
}

/** Evenly spread n points on a sphere (the golden-angle / Fibonacci
    method) so the file graph never clumps or overlaps no matter how
    many files an agent has - the same "scales with real data, never a
    fixed layout" rule the ring itself already follows. */
function fibonacci_sphere(n: number, radius: number) {
  const points: Array<{ x: number; y: number; z: number }> = [];
  const golden = Math.PI * (3 - Math.sqrt(5));
  for (let i = 0; i < n; i++) {
    const y = 1 - (i / Math.max(n - 1, 1)) * 2;
    const r = Math.sqrt(Math.max(1 - y * y, 0));
    const theta = golden * i;
    points.push({
      x: Math.cos(theta) * r * radius,
      y: y * radius,
      z: Math.sin(theta) * r * radius,
    });
  }
  return points;
}

/** What clicking a ring node opens: the reference image's centre
    particle-network look, rebuilt around one real agent's real files
    (GET /api/main_menu/agents/&lt;name&gt;/files - a plain directory
    read, Tier 0, no model call) instead of decorative noise. Pure CSS
    3D (perspective + preserve-3d + translate3d), no Three.js - the
    same hosting limit CenterParticles.tsx already documented for the
    ambient core rules out anything a static export can't carry. */
export function AgentFilesGraph({ agentName, onClose }: { agentName: string; onClose: () => void }) {
  const [files, setFiles] = useState<AgentFile[] | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setFiles(null);
    setFailed(false);
    fetch(`/api/main_menu/agents/${encodeURIComponent(agentName)}/files`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then((body: { has_data: boolean; files: AgentFile[] }) => {
        if (!cancelled) setFiles(body.has_data ? body.files : []);
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, [agentName]);

  const points = useMemo(() => fibonacci_sphere(files?.length ?? 0, 150), [files]);

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center p-4"
        style={{ background: "rgba(0,0,0,0.75)" }}
        onClick={onClose}
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.96 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.96 }}
          onClick={(e) => e.stopPropagation()}
          className="agentic-panel flex max-h-[90vh] w-full max-w-[720px] flex-col p-4"
        >
          <header className="mb-3 flex items-center justify-between">
            <p className="agentic-label text-sm">{agentName.replace(/_Agent$/i, "")} &middot; files</p>
            <button
              type="button"
              onClick={onClose}
              aria-label="close"
              className="rounded border border-[#333] px-2 py-1 text-xs text-dim hover:text-white"
            >
              close
            </button>
          </header>

          {files === null && !failed && <p className="text-xs text-dim">reading Agents/{agentName}/&hellip;</p>}
          {failed && <p className="text-xs text-amber">could not read that agent&rsquo;s folder</p>}
          {files !== null && files.length === 0 && !failed && (
            <p className="text-xs text-dim">no files found under this agent&rsquo;s folder</p>
          )}

          {files !== null && files.length > 0 && (
            <>
              <div
                className="relative mx-auto mb-3"
                style={{ width: 320, height: 320, perspective: 900 }}
              >
                <motion.div
                  className="absolute left-1/2 top-1/2"
                  style={{ transformStyle: "preserve-3d", width: 0, height: 0 }}
                  animate={{ rotateY: 360 }}
                  transition={{ duration: 40, repeat: Infinity, ease: "linear" }}
                >
                  <div
                    className="absolute flex items-center justify-center rounded-full border text-[9px] text-dim"
                    style={{
                      width: 48,
                      height: 48,
                      left: -24,
                      top: -24,
                      borderColor: "var(--agentic-amber, #ff7a00)",
                      background: "var(--agentic-panel, #141212)",
                      transform: "translateZ(0)",
                    }}
                  >
                    hub
                  </div>
                  {files.map((f, i) => {
                    const p = points[i];
                    const depth = (p.z + 150) / 300;
                    return (
                      <div
                        key={f.path}
                        title={f.path}
                        className="absolute rounded-full"
                        style={{
                          width: 8,
                          height: 8,
                          left: p.x - 4,
                          top: p.y - 4,
                          background: colour_for(f.kind),
                          opacity: 0.35 + depth * 0.65,
                          transform: `translateZ(${p.z}px) scale(${0.6 + depth * 0.7})`,
                          boxShadow: `0 0 6px ${colour_for(f.kind)}`,
                        }}
                      />
                    );
                  })}
                </motion.div>
              </div>

              <ul className="flex-1 overflow-y-auto text-[11px]">
                {files.map((f) => (
                  <li key={f.path} className="flex items-center justify-between gap-2 border-b border-[#232323] py-1">
                    <span className="flex items-center gap-2 truncate text-white">
                      <span
                        className="inline-block h-1.5 w-1.5 shrink-0 rounded-full"
                        style={{ background: colour_for(f.kind) }}
                      />
                      {f.path}
                    </span>
                    <span className="num shrink-0 text-dim">{(f.size_bytes / 1024).toFixed(1)} KB</span>
                  </li>
                ))}
              </ul>
            </>
          )}
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
