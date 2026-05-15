/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'scout-green': '#2d6a4f', // Nuestro verde scout personalizado
      }
    },
  },
  plugins: [],
}