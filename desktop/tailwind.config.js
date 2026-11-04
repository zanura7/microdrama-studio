/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        cyber: {
          bg: "#0b0e14",
          card: "#121824",
          border: "#1e293b",
          primary: "#00f0ff",
          accent: "#ff007f",
          neonGreen: "#00ff66",
        }
      }
    },
  },
  plugins: [],
}
