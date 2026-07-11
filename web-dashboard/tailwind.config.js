/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./app/**/*.{js,ts,jsx,tsx,mdx}', './components/**/*.{js,ts,jsx,tsx,mdx}'],
  theme: {
    extend: {
      colors: {
        primary: { DEFAULT: '#065366', hover: '#0a6b80' },
        secondary: { DEFAULT: '#a0ba3b' },
      },
    },
  },
  plugins: [],
};
