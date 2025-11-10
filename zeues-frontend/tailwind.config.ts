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
        // Paleta ZEUES custom
        zeues: {
          orange: '#FF5B00',        // Principal (marca)
          'orange-dark': '#E64A19', // Hover principal
          blue: '#0A7EA4',          // Secundario
          cyan: '#0891B2',          // INICIAR acción
          green: '#16A34A',         // COMPLETAR acción
          red: '#DC2626',           // Error
          warning: '#EA580C',       // Warning
        },
      },
    },
  },
  plugins: [],
};

export default config;
