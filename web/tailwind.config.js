/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Nightreign menu palette: cold desaturated navy/charcoal, pale
        // silver-blue text, gold used only as a rare accent.
        void: "#05070c",
        night: {
          DEFAULT: "#0a0e17",
          900: "#080b12",
          800: "#0d121d",
          700: "#121a29",
          600: "#182133",
          500: "#20293c",
        },
        line: {
          DEFAULT: "#25324a",
          soft: "#1b2740",
          bright: "#3c506f",
        },
        ink: "#cbd6e6", // primary pale text
        silver: "#9dafc8", // secondary
        dim: "#6f7f99",
        faint: "#465268",
        gold: {
          DEFAULT: "#c9a24a",
          bright: "#e8cf8a",
          deep: "#7c6531",
        },
        frost: "#8fb6e6", // cold selection glow
        relic: {
          red: "#cd6a5e",
          blue: "#5f93cf",
          yellow: "#d8b657",
          green: "#5fa878",
          any: "#c3cede",
        },
      },
      fontFamily: {
        display: ["Cinzel", "serif"],
        serif: ['"EB Garamond"', "Georgia", "serif"],
        sans: ['"Inter"', "system-ui", "sans-serif"],
      },
      letterSpacing: {
        widest2: "0.28em",
      },
      keyframes: {
        rise: {
          "0%": { opacity: "0", transform: "translateY(18px)" },
          "100%": { opacity: "1", transform: "none" },
        },
        breathe: {
          "0%,100%": { opacity: "0.45" },
          "50%": { opacity: "1" },
        },
        shimmer: {
          "0%": { transform: "translateX(-120%) skewX(-18deg)" },
          "100%": { transform: "translateX(320%) skewX(-18deg)" },
        },
      },
      animation: {
        rise: "rise 0.55s cubic-bezier(.2,.7,.3,1) forwards",
        breathe: "breathe 2.4s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
