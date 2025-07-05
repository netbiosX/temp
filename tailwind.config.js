/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        purpleMain: "#8000ff",
        purpleLight: "#e9d7ff",
      }
    },
  },
  plugins: [],
}
