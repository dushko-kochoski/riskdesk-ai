/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#080b12",
          900: "#0b1020",
          850: "#111827",
          800: "#172033",
        },
      },
      boxShadow: {
        panel: "0 18px 60px rgba(0, 0, 0, 0.28)",
      },
    },
  },
  plugins: [],
};
