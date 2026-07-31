export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        ink: '#0C0B0A', 'ink-2': '#141210',
        washi: '#F2EDE4', 'washi-2': '#E8DFCD', 'washi-3': '#D6CEC0',
        stone: '#8E8779', 'stone-2': '#6F6759', 'stone-3': '#A79E90',
        gold: '#C9A227', crimson: '#B8382C', jade: '#5B7C6E',
      },
      fontFamily: {
        serif: ['"Source Serif 4"', 'Georgia', 'serif'],
        sans: ['Inter', 'ui-sans-serif', 'system-ui'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
    },
  },
  plugins: [],
}
