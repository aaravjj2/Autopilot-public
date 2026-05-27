import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        apex: {
          bg: "#0b0f14",
          card: "#121a24",
          accent: "#3b82f6",
          green: "#22c55e",
          red: "#ef4444",
        },
      },
    },
  },
  plugins: [],
};

export default config;
