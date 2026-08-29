import type { Config } from 'tailwindcss'

const config: Config = {
  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        carbon: { DEFAULT: '#1a1a1a', light: '#2d2d2d', dark: '#0f0f0f' },
        racing: { red: '#e10600', yellow: '#f9a800', blue: '#00d2ff', green: '#00ff87', silver: '#c0c0c0' },
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
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
