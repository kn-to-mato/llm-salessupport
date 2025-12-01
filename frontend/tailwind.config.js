/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Noto Sans JP', 'SF Pro Display', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      colors: {
        primary: {
          50: '#eef6ff',
          100: '#d9eaff',
          200: '#bbdaff',
          300: '#8cc4ff',
          400: '#56a4ff',
          500: '#2d7fff',
          600: '#1560f5',
          700: '#0e4be1',
          800: '#123db6',
          900: '#15388f',
          950: '#112357',
        },
        accent: {
          50: '#fef6ee',
          100: '#fcebd7',
          200: '#f8d4ae',
          300: '#f3b57a',
          400: '#ed8c44',
          500: '#e86d20',
          600: '#d95316',
          700: '#b43d14',
          800: '#903218',
          900: '#742c17',
          950: '#3e130a',
        },
        dark: {
          50: '#f6f6f7',
          100: '#e2e3e5',
          200: '#c5c6cb',
          300: '#a0a2a9',
          400: '#7b7e87',
          500: '#60636c',
          600: '#4c4e56',
          700: '#3f4047',
          800: '#36373c',
          900: '#1e1f23',
          950: '#121316',
        }
      },
      animation: {
        'fade-in': 'fadeIn 0.3s ease-out',
        'slide-up': 'slideUp 0.4s ease-out',
        'pulse-soft': 'pulseSoft 2s infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        pulseSoft: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.7' },
        },
      },
    },
  },
  plugins: [],
}



