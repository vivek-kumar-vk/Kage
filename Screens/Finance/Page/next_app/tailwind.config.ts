import type { Config } from 'tailwindcss'

const config: Config = {
  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        carbon: { DEFAULT: '#1a1a1a', light: '#2d2d2d', dark: '#0f0f0f' },
        racing: { red: '#e10600', yellow: '#f9a800', blue: '#00d2ff', green: '#00ff87', silver: '#c0c0c0' },
        // AURUM — private-wealth terminal skin (Overview; red stays "act now" only)
        aurum: {
          bg0: '#08090F',
          bg1: '#0C0E16',
          gold: '#E4C07C',
          'gold-bright': '#F5DCA4',
          emerald: '#3DDC97',
          coral: '#FF7A6B',
          peri: '#8B93FF',
          cyan: '#6BE1FF',
          amber: '#F5B85C',
          text: '#ECEAE2',
          muted: '#9A9DAA',
          faint: '#5B5F6E',
        },
      },
      // families come from next/font (app/layout.tsx) via CSS variables
      fontFamily: {
        sans: ['var(--font-sans)', 'system-ui', 'sans-serif'],
        mono: ['var(--font-mono)', 'ui-monospace', 'monospace'],
        serif: ['var(--font-serif)', 'Georgia', 'serif'],
      },
      boxShadow: {
        'neon-red': '0 0 10px rgba(225, 6, 0, 0.5)',
        'neon-blue': '0 0 10px rgba(0, 210, 255, 0.5)',
      },
    },
  },
  plugins: [],
}
export default config
