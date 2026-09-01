"use client";

import { useCallback, useEffect, useState } from "react";

export const API_BASE = "";

export type IdeaStatus = "ideas" | "todo" | "in_progress" | "done";
export type IdeaPriority = "low" | "medium" | "high" | "critical";
export type IdeaSource = "user" | "ai";
export type CommentAuthor = "user" | "ai";

export interface Room {
  id: string;
  kind: "board" | "agent" | "system";
  name: string;
  agent_name: string | null;
}

export interface Agent {
  name: string;
  role: string;
}

export interface IdeaCounts {
  ideas: number;
  todo: number;
  in_progress: number;
  done: number;
}

export interface Workspace {
  state: string;
  rooms: Room[];
  agents: Agent[];
  counts: {
    ideas: IdeaCounts;
  };
}

export type Selection = {
  kind: "room" | "agent";
  id: string;
};

export interface IdeaComment {
  id: string;
  text: string;
  author: CommentAuthor;
  created_at: string | null;
}

export interface Idea {
  id: string;
  key: string;
  title: string;
  note: string;
  area: string;
  source: IdeaSource;
  status: IdeaStatus;
  priority: IdeaPriority;
  order_index: number | null;
  added_at: string | null;
  updated_at: string | null;
  comments: IdeaComment[];
}

export interface IdeasResponse {
  state: string;
  ideas: Idea[];
}

export interface DuplicateWarning {
  idea_id: string;
  key: string;
  title: string;
  reason: string;
}

export interface IdeaEnvelope {
  ok: boolean;
  item?: Idea;
  problem?: string;
  duplicate?: boolean;
  duplicate_warning?: DuplicateWarning;
}

export interface CreateIdeaInput {
  title: string;
  note?: string;
  area?: string;
  source?: IdeaSource;
  priority?: IdeaPriority;
}

export interface MoveIdeaInput {
  status: IdeaStatus;
  order_index?: number;
}

export interface AddCommentInput {
  text: string;
  author?: CommentAuthor;
}

type SubmitMethod = "POST" | "PUT" | "PATCH" | "DELETE";

function extractMessage(parsed: unknown): string | null {
  if (typeof parsed === "object" && parsed !== null) {
    const record = parsed as Record<string, unknown>;

    if (typeof record.detail === "string") {
      return record.detail;
    }

    if (typeof record.problem === "string") {
      return record.problem;
    }
  }

  return null;
}

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    Accept: "application/json",
  };

  if (init?.body) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
  });

  const text = await response.text();
  let parsed: unknown = null;

  if (text) {
    try {
      parsed = JSON.parse(text);
    } catch {
      throw new Error(`Invalid JSON from ${path}`);
    }
  }

  if (!response.ok) {
    const message = extractMessage(parsed);
    throw new Error(message ?? `Request failed with status ${response.status}`);
  }

  return parsed as T;
}

export function useResource<T>(path: string) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let cancelled = false;

    setLoading(true);
    setError(null);

    http<T>(path)
      .then((result) => {
        if (!cancelled) {
          setData(result);
          setLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setData(null);
          setError(err instanceof Error ? err.message : "Request failed");
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [path, tick]);

  const reload = useCallback(() => {
    setTick((value) => value + 1);
  }, []);

  return { data, loading, error, reload };
}

export function useSubmit<TInput, TOutput>(path: string, method: SubmitMethod = "POST") {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = useCallback(
    async (
      input?: TInput,
      pathOverride?: string
    ): Promise<{ data: TOutput | null; error: string | null }> => {
      setLoading(true);
      setError(null);

      try {
        const result = await http<TOutput>(pathOverride ?? path, {
          method,
          body: input === undefined ? undefined : JSON.stringify(input),
        });

        return { data: result, error: null };
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : "Request failed";
        setError(message);
        return { data: null, error: message };
      } finally {
        setLoading(false);
      }
    },
    [path, method]
  );

  return { submit, loading, error };
}
