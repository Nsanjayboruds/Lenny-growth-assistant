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
          50: '#f0eeff',
          100: '#e0ddff',
          200: '#c5bfff',
          300: '#a89aff',
          400: '#8b73ff',
          500: '#6c63ff',
          600: '#5a4de0',
          700: '#4839bf',
          800: '#38299f',
          900: '#291b80',
        },
        surface: {
          900: '#0d0d1a',
          800: '#13131f',
          750: '#161624',
          700: '#1a1a2e',
          600: '#22223b',
          500: '#2d2d47',
          400: '#3a3a5c',
          300: '#4a4a72',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      animation: {
        'fade-in': 'fadeIn 0.2s ease-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'pulse-slow': 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
}
