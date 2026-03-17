/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      colors: {
        navy:    "#0a0f1e",
        surface: "#0d1526",
        accent:  "#00ff88",
        danger:  "#ff4444",
        amber:   "#ffaa00",
      },
      fontFamily: {
        mono: ['"JetBrains Mono"', "monospace"],
        sans: ["Inter", "sans-serif"],
      },
    },
  },
  plugins: [],
};
