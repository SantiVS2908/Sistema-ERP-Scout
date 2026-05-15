export default {
  plugins: {
    "@tailwindcss/postcss": {}, // Aquí es donde estaba el error, le faltaba el @ y el /postcss
    autoprefixer: {},
  },
}