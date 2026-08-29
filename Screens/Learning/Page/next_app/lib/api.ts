"use client";

import { useCallback, useEffect, useState } from "react";

const API_BASE = "";

export function useResource<T>(path: string) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const res = await fetch(`${API_BASE}${path}`);
        const text = await res.text();

        let parsed: T | null = null;
        if (text) {
          try {
            parsed = JSON.parse(text) as T;
          } catch {
            parsed = null;
          }
        }

        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }

        if (!cancelled) {
          setData(parsed);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setData(null);
          setError(err instanceof Error ? err.message : String(err));
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    load();

    return () => {
      cancelled = true;
    };
  }, [path]);

  return { data, error, loading };
}

export function useSubmit<T>(
  path: string,
  method: "POST" | "PUT" | "DELETE" = "POST"
) {
  const [submitting, setSubmitting] = useState(false);

  const submit = useCallback(
    async (body?: unknown): Promise<{ data: T | null; error: string | null }> => {
      setSubmitting(true);

      try {
        const res = await fetch(`${API_BASE}${path}`, {
          method,
          headers: {
            "Content-Type": "application/json",
          },
          body: body === undefined ? undefined : JSON.stringify(body),
        });

        const text = await res.text();

        let parsed: T | null = null;
        if (text) {
          try {
            parsed = JSON.parse(text) as T;
          } catch {
            parsed = null;
          }
        }

        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }

        return { data: parsed, error: null };
      } catch (err) {
        return {
          data: null,
          error: err instanceof Error ? err.message : String(err),
        };
      } finally {
        setSubmitting(false);
      }
    },
    [path, method]
  );

  return { submit, submitting };
}
