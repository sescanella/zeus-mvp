import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // Paleta ZEUES Soft Brutalism v2.0
        zeues: {
          // KM Brand Colors (Base)
          orange: '#FF5B00',        // Primary CTA (KM)
          'orange-dark': '#E64A19', // Hover primary
          blue: '#0A4C95',          // Secondary (KM)
          'blue-dark': '#083A75',   // Hover secondary

          // Terrosos Desaturados (Soft Brutalism)
          stone: '#D4D2CE',         // Cards/contenedores background
          beige: '#F5F1E8',         // Page background
          sage: '#9CAF88',          // Success state
          taupe: '#8B7F73',         // Secondary text

          // States
          red: '#DC2626',           // Danger/Cancel
          warning: '#EA580C',       // Warning
        },
        // Alias para compatibilidad con código existente
        'km-orange': '#FF5B00',
        'km-blue': '#0A4C95',
      },
    },
  },
  plugins: [],
};

export default config;
