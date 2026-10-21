/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        background: '#050505',
        surface: '#0d0d0d',
        'surface-hover': '#141414',
        card: '#0a0a0a',
        'card-border': '#1e1e1e',
        'border-light': '#2a2a2a',
        primary: '#ffffff',
        'primary-muted': '#a0a0a0',
        'primary-dark': '#050505',
        accent: '#ffffff',
        muted: '#666666',
        live: '#ffffff',
      },
      fontFamily: {
        sans: ['Outfit', 'Inter', 'system-ui', '-apple-system', 'sans-serif'],
        display: ['Outfit', 'Space Grotesk', 'sans-serif'],
        tech: ['Space Grotesk', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      animation: {
        'pulse-subtle': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'shimmer': 'shimmer 2s linear infinite',
      },
      keyframes: {
        shimmer: {
          from: { backgroundPosition: '0 0' },
          to: { backgroundPosition: '-200% 0' },
        },
      },
    },
  },
  plugins: [],
}
