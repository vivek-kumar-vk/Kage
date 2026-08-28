import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // INKY has no always-on Node process - every screen is a lightweight
  // FastAPI server serving files. The rebuild is therefore a static
  // export (`npm run build` writes plain HTML/JS/CSS into ./out) that
  // the screen's own server mounts at / when USE_NEXT_UI is flipped on.
  output: "export",
  images: {
    // The static export has no image optimization server behind it.
    unoptimized: true,
  },
  // Don't let `next dev` drop its own AGENTS.md / CLAUDE.md into this
  // folder - this repo keeps one AGENTS.md at the root (its rule 7/8
  // numbering convention), and a second, tool-authored one here would
  // only confuse that.
  agentRules: false,
};

export default nextConfig;
