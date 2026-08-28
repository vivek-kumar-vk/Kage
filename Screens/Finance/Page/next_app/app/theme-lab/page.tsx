"use client";

import type { CSSProperties } from "react";
import ThemeLabStage from "./stage";
import SakuraPetals from "./petals";

/** PROTOTYPE — throwaway livery preview (P9 Phase 0). Shows the real
    globals.css tokens under .liv-ferrari (Overview) and .liv-rb
    (Investments) on sample F1-feel UI. Deleted in Phase 5. */

const pane: CSSProperties = {
  position: "relative",
  overflow: "hidden",
  minHeight: "100dvh",
  background: "var(--liv-bg)",
  color: "var(--liv-text)",
  fontFamily: "ui-sans-serif, system-ui, sans-serif",
};

const tag: CSSProperties = {
  position: "absolute",
  top: 16,
  left: 20,
  zIndex: 2,
  fontSize: 12,
  letterSpacing: 2,
  textTransform: "uppercase",
  color: "var(--liv-text-dim)",
};

const ThemeLab = () => (
  <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: 0 }}>
    <section className="liv-ferrari" style={pane}>
      <span style={tag}>Ferrari livery · Overview</span>
      <SakuraPetals />
      <ThemeLabStage />
    </section>
    <section className="liv-rb" style={pane}>
      <span style={tag}>Red Bull livery · Investments</span>
      <SakuraPetals />
      <ThemeLabStage />
    </section>
  </div>
);

export default ThemeLab;
