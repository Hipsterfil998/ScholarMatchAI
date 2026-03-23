/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: {
        mono: ['IBM Plex Mono', 'monospace'],
        sans: ['-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Helvetica Neue', 'sans-serif'],
      },
      colors: {
        bg:     '#0f0f12',
        card:   '#17171c',
        input:  '#1e1e24',
        border: '#2e2e38',
        fg:     '#e8e8f0',
        muted:  '#7a7a8f',
        accent: '#818cf8',
      },
    },
  },
  plugins: [],
}
