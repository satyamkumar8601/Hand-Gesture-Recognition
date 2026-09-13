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
        primary: {
          DEFAULT: '#6366F1', // Indigo
          hover: '#4F46E5',
          light: '#EEF2FF',
          dark: '#3730A3',
        },
        secondary: {
          DEFAULT: '#8B5CF6', // Purple
          hover: '#7C3AED',
          light: '#F5F3FF',
        },
        accent: {
          DEFAULT: '#22C55E', // Green
          hover: '#16A34A',
          light: '#F0FDF4',
        },
        cyber: {
          cyan: '#00F0FF',
          gold: '#FFB800',
          pink: '#FF007A',
        },
        dark: {
          bg: '#0F172A',
          card: '#1E293B',
          border: '#334155',
          text: '#F8FAFC',
          muted: '#94A3B8',
        },
        light: {
          bg: '#F8FAFC',
          card: '#FFFFFF',
          border: '#E2E8F0',
          text: '#0F172A',
          muted: '#64748B',
        }
      },
      fontFamily: {
        sans: ['Inter', 'Segoe UI', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        'glow-primary': '0 0 20px rgba(99, 102, 241, 0.35)',
        'glow-accent': '0 0 20px rgba(34, 197, 94, 0.35)',
        'glow-cyan': '0 0 20px rgba(0, 240, 255, 0.4)',
      }
    },
  },
  plugins: [],
}
