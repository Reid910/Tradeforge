import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        forge: {
          bg: "#0b0d10",
          panel: "#14171c",
          border: "#242830",
          accent: "#e0a339",
          rare: "#a855f7",
        },
      },
    },
  },
  plugins: [],
};

export default config;
