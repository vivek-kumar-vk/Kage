/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        term: {
          bg: "var(--term-bg)",
          fg: "var(--term-fg)",
          green: "var(--term-green)",
          cyan: "var(--term-cyan)",
          amber: "var(--term-amber)",
          violet: "var(--term-violet)",
          red: "var(--term-red)",
          dim: "var(--term-dim)",
          border: "var(--term-border)",
        },
        heat: {
          0: "var(--heat-0)",
          1: "var(--heat-1)",
          2: "var(--heat-2)",
          3: "var(--heat-3)",
          4: "var(--heat-4)",
        },
      },
      fontFamily: {
        mono: ["var(--font-jetbrains-mono)", "'Fira Code'", "monospace"],
      },
    },
  },
  plugins: [],
};
