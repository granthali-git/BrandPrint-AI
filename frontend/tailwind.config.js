/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          ocean: '#0b3c49',
          oceanDark: '#072730',
          oceanLight: '#144f60',
          amber: '#f4a321',
          amberHover: '#de9018',
          amberLight: '#fef3e2',
          cream: '#fbf9f4',
          creamDark: '#f3eee3',
          sand: '#e8e2d5',
          textDark: '#1a272b',
          textMuted: '#5d7177',
          charcoal: '#1a272b',
          charcoalMuted: '#5d7177',
        },
        ocean: '#0b3c49',
        oceanDark: '#072730',
        oceanLight: '#144f60',
        amber: {
          DEFAULT: '#f4a321',
          hover: '#de9018',
          light: '#fef3e2',
        },
        amberHover: '#de9018',
        amberLight: '#fef3e2',
        cream: {
          DEFAULT: '#fbf9f4',
          dark: '#f3eee3',
        },
        creamDark: '#f3eee3',
        sand: '#e8e2d5',
        textDark: '#1a272b',
        textMuted: '#5d7177',
        charcoal: '#1a272b',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace']
      },
      boxShadow: {
        'amber-glow': '0 0 20px -3px rgba(244, 163, 33, 0.35)',
        'card-soft': '0 1px 3px 0 rgba(11, 60, 73, 0.06), 0 1px 2px -1px rgba(11, 60, 73, 0.06)',
        'card-elevated': '0 4px 6px -1px rgba(11, 60, 73, 0.08), 0 2px 4px -2px rgba(11, 60, 73, 0.08)',
        'card-hover': '0 10px 15px -3px rgba(11, 60, 73, 0.1), 0 4px 6px -4px rgba(11, 60, 73, 0.08)',
      }
    },
  },
  plugins: [],
}
