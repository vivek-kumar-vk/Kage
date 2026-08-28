import type { ReactNode } from "react";

/** Shared prop contracts for the F1 primitive set. The local model
    authors each component body against these; orchestrator glue passes
    props by these names. Tones map to var(--f1-<tone>). */

export type Tone = "best" | "ahead" | "flat" | "alert";

export interface SparklineProps {
  series: number[];
  height?: number;
  stroke?: string;
  fill?: string;
}

export interface DeltaBadgeProps {
  value: string;
  tone: Tone;
  title?: string;
}

export interface StatDialProps {
  pct: number;
  value?: string;
  label?: string;
  size?: number;
}

export interface SegmentMeterProps {
  segments: { label: string; pct: number }[];
}

export interface TimingRowProps {
  rank: string;
  name: string;
  value: string;
  pct?: number;
  tone?: Tone;
  iconSrc?: string;
  delta?: string;
}

export interface TelemetryCardProps {
  label: string;
  value?: string;
  sub?: string;
  edge?: boolean;
  children?: ReactNode;
}

export interface WipeInProps {
  children: ReactNode;
  delay?: number;
}
