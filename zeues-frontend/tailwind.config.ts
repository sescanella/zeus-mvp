import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        mono: ['var(--font-mono)', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'Liberation Mono', 'Courier New', 'monospace'],
      },
      screens: {
        // Narrow screens (small tablets/large phones like 601x962px)
        'narrow': {'max': '640px'},
      },
      colors: {
        zeues: {
          // KM Brand Colors (Base)
          orange: '#FF5B00',        // Primary CTA (KM)
          'orange-dark': '#E64A19', // Hover primary
          blue: '#0A4C95',          // Secondary (KM)
          'blue-dark': '#083A75',   // Hover secondary

          // States
          red: '#DC2626',           // Danger/Cancel
          warning: '#EA580C',       // Warning

          // Blueprint base
          navy: '#001F3F',             // Dark background
          'orange-border': '#E55D26',  // Selected state border
          'orange-pressed': '#CC5322', // Active/pressed state border
        },
      },
    },
  },
  plugins: [],
};

export default config;
