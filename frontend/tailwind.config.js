/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: {
        mono: ['IBM Plex Mono', 'monospace'],
        serif: ['Source Serif 4', 'Georgia', 'serif'],
      },
      colors: {
        bg: '#0e0e0e',
        fg: '#e8e2d9',
        accent: '#d97706',
        muted: '#6b6560',
        border: '#272320',
        card: '#141210',
      },
    },
  },
  plugins: [],
}
