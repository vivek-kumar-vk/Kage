"use client";

import { useCallback, useEffect, useState } from "react";

export type FetchState = "loading" | "fresh" | "error";

export interface RecallCard {
  id: string;
  topic: string;
  track: string;
  elevator?: string;
  likely_q?: string;
  trap_q?: string;
  example?: string;
  reps?: number;
  interval?: number;
  next_due?: string;
}

export interface RecallCardsPayload {
  cards: RecallCard[];
  due: RecallCard[];
  resume_ready_count: number;
}

/** GET /api/learning/recall-cards - the new 5-part SM-2 queue. */
export function useRecallCards() {
  const [data, setData] = useState<RecallCardsPayload | null>(null);
  const [state, setState] = useState<FetchState>("loading");

  const load = useCallback(() => {
    setState((s) => (s === "fresh" ? s : "loading"));
    fetch("/api/learning/recall-cards")
      .then((r) => {
        if (!r.ok) throw new Error(String(r.status));
        return r.json();
      })
      .then((body) => {
        setData(body as RecallCardsPayload);
        setState("fresh");
      })
      .catch(() => setState("error"));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const review = useCallback((cardId: string, quality: number) => {
    fetch("/api/learning/recall-cards/review", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ card_id: cardId, quality }),
    })
      .then((r) => r.json())
      .then(() => load())
      .catch(() => load());
  }, [load]);

  return { data, state, reload: load, review };
}

export interface NoteRow {
  note_file: string;
  title: string;
  box: number;
  last_reviewed: string | null;
  next_due: string | null;
  is_due: boolean;
}

export interface NotesPayload {
  built: boolean;
  total_notes: number;
  due_count: number;
  due: NoteRow[];
  not_due: NoteRow[];
}

/** GET /api/learning/recall - the original five-box Leitner queue over
    Knowledge_Base notes, kept exactly as it was. */
export function useRecallNotes() {
  const [data, setData] = useState<NotesPayload | null>(null);
  const [state, setState] = useState<FetchState>("loading");

  const load = useCallback(() => {
    setState((s) => (s === "fresh" ? s : "loading"));
    fetch("/api/learning/recall")
      .then((r) => {
        if (!r.ok) throw new Error(String(r.status));
        return r.json();
      })
      .then((body) => {
        setData(body as NotesPayload);
        setState("fresh");
      })
      .catch(() => setState("error"));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const review = useCallback((noteFile: string, remembered: boolean) => {
    fetch("/api/learning/recall/review", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ note_file: noteFile, remembered }),
    })
      .then((r) => r.json())
      .then(() => load())
      .catch(() => load());
  }, [load]);

  return { data, state, reload: load, review };
}
