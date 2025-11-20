import type { Config } from "tailwindcss";

const config = {
  content: ["./src/**/*.{html,js,svelte,ts}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        // NeuroForge Brand Colors (Tri-Gradient Identity)
        "nf-ember-core": "#FF4C39",
        "nf-pulse-violet": "#8A4FFF",
        "nf-neural-blue": "#4DB2FF",

        // Status / Feedback Colors
        "nf-success": "#2ECC71",
        "nf-warning": "#F1C40F",
        "nf-danger": "#FF2E63",
        "nf-info": "#3FC9FF",

        // Forge Neutrals (Ash / Gray scale)
        "forge-ash": {
          50: "#f8f8f8",
          100: "#f0f0f0",
          200: "#e0e0e0",
          300: "#c8c8c8",
          400: "#a8a8a8",
          500: "#888888",
          600: "#666666",
          700: "#2F2F33", // Updated to canonical value
          800: "#161618", // Updated to canonical value
          900: "#0d0d0d",
        },
        "forge-ember": {
          50: "#fff8f4",
          100: "#ffe8dc",
          200: "#ffd4bb",
          300: "#ffb896",
          400: "#ff9d6b",
          500: "#ff7a3d",
          600: "#e85c2a",
          700: "#c83f1a",
          800: "#a82a10",
          900: "#7a1a00",
        },
        "forge-brass": {
          50: "#fdfbf7",
          100: "#faf4ed",
          200: "#f4e8da",
          300: "#ead4b8",
          400: "#dab896",
          500: "#c89c70",
          600: "#a87d4d",
          700: "#805c35",
          800: "#5e4428",
          900: "#3d2a19",
        },
        "forge-ink": {
          50: "#f8f8f8",
          100: "#e8e8e8",
          200: "#d8d8d8",
          300: "#b8b8b8",
          400: "#888888",
          500: "#585858",
          600: "#383838",
          700: "#202020",
          800: "#0d0d0d", // Dark text
          900: "#000000", // Pure black for highest contrast
        },
      },
    },
  },
} satisfies Config;

export default config;
