import type { Config } from 'tailwindcss'

const config: Config = {
  content: ['./src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: '#17171C',
        'bg-deep': '#0E0E12',
        surface: '#202027',
        'surface-2': '#26262E',
        'surface-3': '#2C2C35',
        line: '#2A2A31',
        txt: '#F4F5F7',
        'txt-2': '#9A9AA3',
        'txt-3': '#6B6B73',
        up: '#F04452',
        down: '#4593FC',
        blue: '#3182F6',
        teal: '#2BC4B6',
        purple: '#8B5CF6',
        amber: '#F7A93B',
      },
      fontFamily: {
        sans: ['Pretendard Variable', 'Pretendard', '-apple-system', 'system-ui', 'sans-serif'],
      },
      fontWeight: {
        800: '800',
      },
      borderRadius: {
        card: '16px',
      },
      maxWidth: {
        app: '390px',
      },
    },
  },
  plugins: [],
}

export default config
