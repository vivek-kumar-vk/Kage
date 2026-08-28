import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "INKY // home",
  description:
    "The main menu of INKY: every screen, every agent, live from the trace ledger.",
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
.home-grid { grid-template-columns: 280px 1fr 280px; }
@media (max-width: 1100px) {
  .home-grid { grid-template-columns: 1fr; }
  .home-grid > :first-child { order: 2; }
  .home-grid > :nth-child(2) { order: 1; }
  .home-grid > :nth-child(3) { order: 3; }
}
/* A phone held sideways is wide and very short (about 740x360). The
   ring itself is resized in JS (useRingSize in CenterCore.tsx, since a
   CSS transform would leave the un-scaled box's footprint in normal
   flow and cause exactly the sideways scroll this rule exists to
   prevent) - this rule handles the part CSS still owns: trimming
   vertical padding so the side columns stay reachable without a
   mountain of scrolling.
*/
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
            palette cannot drift between the old page and this one. */}
        <link rel="stylesheet" href="/shared/colours_and_fonts.css" />
        <link rel="stylesheet" href="/shared/responsive_layout.css" />
        <style>{RESPONSIVE_CONTRACT}</style>
        {children}
      </body>
    </html>
  );
}
