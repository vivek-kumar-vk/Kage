import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "INKY - Enhancement Board",
  description:
    "The Enhancement idea board: every idea captured, columned, and live off the trace ledger.",
};

// The responsive contract (C9): follow the device width, and reach past
// the notch so env(safe-area-inset-*) means something on a real phone.
export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

// The four widths every INKY page changes its mind at (ADR-060) and the
// one question that is not about width. Written in
// Shared_By_All_Screens/Look_And_Feel/responsive_layout.css; repeated
// here because CSS cannot read a custom property inside a @media query.
const RESPONSIVE_CONTRACT = `
@media (max-width: 1100px) {
  .board-grid { grid-template-columns: 1fr; }
}
@media (max-width: 820px) {
  .rail { flex-direction: row; flex-wrap: wrap; }
  .rail > * { flex: 1 1 260px; }
}
@media (max-width: 560px) {
  .board-title { font-size: 1.25rem; }
  .stats-strip { grid-template-columns: repeat(2, 1fr); }
  .board-column { width: 220px; }
}
@media (max-width: 420px) {
  .header-pad { padding-left: 12px; padding-right: 12px; }
  .board-column { width: 200px; }
}
/* A phone held sideways is wide and very short: the board's own
   overflow-x already carries the columns, so only the header needs to
   shrink to keep everything reachable without vertical scroll. */
@media (orientation: landscape) and (max-height: 560px) {
  .board-header { position: static; }
  .board-main { padding-top: 8px; }
}
`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col">
        {/* The shared look, published by this screen's own server at
            /shared exactly as it is for every other INKY page - the
            palette cannot drift between the old page and this one. */}
        <link rel="stylesheet" href="/shared/colours_and_fonts.css" />
        <link rel="stylesheet" href="/shared/responsive_layout.css" />
        <style>{RESPONSIVE_CONTRACT}</style>
        {children}
      </body>
    </html>
  );
}
