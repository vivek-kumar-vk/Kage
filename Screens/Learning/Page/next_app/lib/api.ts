"use client";

import { useCallback, useEffect, useState } from "react";

export async function api<T = unknown>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch { /* not json */ }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export function post<T = unknown>(path: string, body?: unknown): Promise<T> {
  return api<T>(path, { method: "POST", body: body ? JSON.stringify(body) : undefined });
}

export const put = <T = unknown,>(path: string, body?: unknown): Promise<T> =>
  api<T>(path, { method: "PUT", body: body ? JSON.stringify(body) : undefined });

export const del = <T = unknown,>(path: string): Promise<T> =>
  api<T>(path, { method: "DELETE" });

/** Fetch-on-mount with loading / error / refetch. */
export function useResource<T>(path: string | null) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let alive = true;
    if (!path) return;
    setLoading(true);
    api<T>(path)
      .then((d) => {
        if (!alive) return;
        setData(d);
        setError(null);
      })
      .catch((e) => alive && setError(String(e.message ?? e)))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [path, tick]);

  const refetch = useCallback(() => setTick((t) => t + 1), []);
  return { data, error, loading, refetch };
}

export function fmtDate(iso: string): string {
  try {
    return new Date(iso + (iso.length === 10 ? "T00:00:00" : "")).toLocaleDateString(
      "en-GB", { weekday: "long", day: "numeric", month: "long" },
    );
  } catch {
    return iso;
  }
}
