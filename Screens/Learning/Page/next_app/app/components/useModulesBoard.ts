"use client";

import { useCallback, useEffect, useState } from "react";

export type FetchState = "loading" | "fresh" | "error";

export interface BoardTopicRow {
  id: string;
  topic: string;
  tier?: string;
  status?: string;
  module_state: "ready" | "missing" | "malformed";
  note_file?: string;
  title?: string;
  tasks_done?: number;
  tasks_total?: number;
}

export interface BoardGroup {
  group: string;
  track: string;
  topics: BoardTopicRow[];
}

export interface ModulesBoard {
  built: boolean;
  topics_total: number;
  topics_with_modules: number;
  groups: BoardGroup[];
}

/** GET /api/learning/modules - every topic, in the topic file's own
    order, each carrying exactly one module_state: ready / missing /
    malformed. topics_with_modules out of topics_total is the honest
    gap this board leads with - never padded. */
export function useModulesBoard() {
  const [board, setBoard] = useState<ModulesBoard | null>(null);
  const [state, setState] = useState<FetchState>("loading");

  const load = useCallback(() => {
    setState((s) => (s === "fresh" ? s : "loading"));
    fetch("/api/learning/modules")
      .then((r) => {
        if (!r.ok) throw new Error(String(r.status));
        return r.json();
      })
      .then((body) => {
        setBoard(body as ModulesBoard);
        setState("fresh");
      })
      .catch(() => setState("error"));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return { board, state, reload: load };
}

export interface ModuleQuestion {
  id: string;
  text: string;
  attempts?: number | null;
  solved: boolean;
}

export interface ModuleTask {
  id: string;
  number: number;
  title: string;
  done: boolean;
  questions: ModuleQuestion[];
}

export interface OneModule {
  ok: boolean;
  note_file: string;
  title: string;
  malformed: boolean;
  topic_id: string | null;
  tasks: ModuleTask[];
  counts: { done: number; total: number };
}

/** GET /api/learning/modules/one?name=... - one module's task list.
    Loaded on demand when a topic row with a real module is opened. */
export function useOneModule(name: string | null) {
  const [module, setModule] = useState<OneModule | null>(null);
  const [state, setState] = useState<FetchState>("loading");

  const load = useCallback(() => {
    if (!name) return;
    setState("loading");
    fetch(`/api/learning/modules/one?name=${encodeURIComponent(name)}`)
      .then((r) => {
        if (!r.ok) throw new Error(String(r.status));
        return r.json();
      })
      .then((body) => {
        setModule(body as OneModule);
        setState("fresh");
      })
      .catch(() => setState("error"));
  }, [name]);

  useEffect(() => {
    load();
  }, [load]);

  const toggleTask = useCallback((taskId: string) => {
    if (!name) return;
    fetch("/api/learning/modules/task", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, task_id: taskId }),
    })
      .then((r) => r.json())
      .then(() => load())
      .catch(() => load());
  }, [name, load]);

  return { module, state, reload: load, toggleTask };
}
