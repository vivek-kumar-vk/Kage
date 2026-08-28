import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "RUBRIC // Agentic OS",
  description:
    "The main menu of INKY, rebuilt as the RUBRIC Agentic OS dashboard: a rotating agent ring around a live 3D particle core.",
};

// The responsive contract (C9): follow the device width, and reach past
// the notch so env(safe-area-inset-*) means something on a real phone.
export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

// The strict 3-column grid from the reference (300 / 1fr / 300),
// collapsing to a single column on a narrow screen (ADR-060 widths).
// Written here because CSS cannot read a custom property inside a
// @media query.
const RESPONSIVE_CONTRACT = `
.home-grid { grid-template-columns: 300px 1fr 300px; }
@media (max-width: 1100px) {
  .home-grid { grid-template-columns: 1fr; }
  .home-grid > :first-child { order: 2; }
  .home-grid > :nth-child(2) { order: 1; }
  .home-grid > :nth-child(3) { order: 3; }
}
/* A phone held sideways is wide and very short (about 740x360). The
   ring itself is resized in JS (useRingSize in CenterCore.tsx); this
   rule handles the part CSS still owns - trimming vertical padding so
   the side columns stay reachable without a mountain of scrolling. */
@media (orientation: landscape) and (max-height: 560px) {
  .home-grid { gap: 8px; padding-top: 8px; padding-bottom: 8px; }
}
`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col">
        {/* The shared look, published by this screen's own server at
            /shared exactly as it is for every other INKY page - the
            font stacks and named colours cannot drift between pages. */}
        <link rel="stylesheet" href="/shared/colours_and_fonts.css" />
        <link rel="stylesheet" href="/shared/responsive_layout.css" />
        <style>{RESPONSIVE_CONTRACT}</style>
        {children}
      </body>
    </html>
  );
}
