import type { Config } from "tailwindcss";

/**
 * Color values are extracted verbatim from the Phase 3 design file
 * (Kortex.dc.html) — do not "normalize" them to Tailwind's palette; e.g.
 * accent-tint is #EEF0FF, not indigo-50's #EEF2FF.
 */
const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        surface: "#FAFAF9",
        raised: "#FBFBFA",
        canvas: "#EDEDEB",
        line: "#E5E5E3",
        "line-soft": "#E8E8E6",
        chip: "#F0F0EE",
        ink: {
          900: "#1C1C1E",
          700: "#33333A",
          600: "#57575B",
          500: "#6B6B68",
          400: "#9A9A96",
        },
        accent: {
          DEFAULT: "#4F46E5",
          deep: "#4338CA",
          tint: "#EEF0FF",
        },
        success: {
          DEFAULT: "#3F7D4E",
          tint: "#EEF6EF",
          line: "#CFE6D4",
        },
        danger: {
          DEFAULT: "#A6433A",
          tint: "#FBEEEC",
          line: "#E8C9C6",
        },
      },
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
      },
      boxShadow: {
        card: "0 1px 2px rgba(16,16,15,0.04)",
        toast: "0 4px 16px rgba(0,0,0,0.18)",
      },
    },
  },
  plugins: [],
};
export default config;
