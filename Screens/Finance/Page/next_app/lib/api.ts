"use client";
import { useCallback, useEffect, useState, useSyncExternalStore } from "react";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "";

let cacheVersion = 0;
const listeners = new Set<() => void>();

function subscribe(cb: () => void) {
  listeners.add(cb);
  return () => listeners.delete(cb);
}
function getVersion() {
  return cacheVersion;
}
export function invalidateCache() {
  cacheVersion += 1;
  listeners.forEach((l) => l());
}

export async function fetchFinanceData<T>(path: string): Promise<T> {
  const url = path.startsWith("http")
    ? path
    : `${API_BASE}/api/finance${path.startsWith("/") ? path : `/${path}`}`;
  const res = await fetch(url, { headers: { Accept: "application/json" } });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return (await res.json()) as T;
}

export function useFinanceData<T>(path: string) {
  const version = useSyncExternalStore(subscribe, getVersion, getVersion);
  const [data, setData] = useState<T | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const load = useCallback(() => {
    let alive = true;
    setIsLoading(true);
    setError(null);
    fetchFinanceData<T>(path)
      .then((d) => {
        if (alive) setData(d);
      })
      .catch((e) => {
        if (alive) setError(e instanceof Error ? e : new Error(String(e)));
      })
      .finally(() => {
        if (alive) setIsLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [path]);

  useEffect(() => load(), [load, version]);

  return { data, isLoading, error, refetch: load };
}

export function useSubmit<TBody = unknown, TResp = unknown>(
  path: string,
  method: "POST" | "PUT" | "PATCH" | "DELETE" = "POST"
) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const submit = useCallback(
    async (body?: TBody): Promise<TResp> => {
      setIsSubmitting(true);
      setError(null);
      try {
        const url = `${API_BASE}/api/finance${
          path.startsWith("/") ? path : `/${path}`
        }`;
        const res = await fetch(url, {
          method,
          headers: { "Content-Type": "application/json" },
          body: body === undefined ? undefined : JSON.stringify(body),
        });
        if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
        const json = (await res.json()) as TResp;
        invalidateCache();
        return json;
      } catch (e) {
        const err = e instanceof Error ? e : new Error(String(e));
        setError(err);
        throw err;
      } finally {
        setIsSubmitting(false);
      }
    },
    [path, method]
  );

  return { submit, isSubmitting, error };
}
