import type { Config } from "tailwindcss";
import animate from "tailwindcss-animate";

// Colors map to the CSS variables declared in src/app/styles/index.css.
// Never hardcode literal colors in components — extend this map instead.
const config: Config = {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: { "2xl": "1400px" },
    },
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        main: "hsl(var(--main-text))",
        description: "hsl(var(--description))",
        label: "hsl(var(--label))",
        placeholder: "hsl(var(--placeholder))",
        eyebrow: "hsl(var(--eyebrow))",
        sidebar: {
          DEFAULT: "hsl(var(--sidebar))",
          foreground: "hsl(var(--sidebar-foreground))",
          muted: "hsl(var(--sidebar-muted))",
          accent: "hsl(var(--sidebar-accent))",
        },
        // Domain semantics — confidence levels of an answer/fact.
        confidence: {
          high: "hsl(var(--confidence-high))",
          medium: "hsl(var(--confidence-medium))",
          low: "hsl(var(--confidence-low))",
        },
        // Domain semantics — geography of a source (RU vs foreign practice).
        geo: {
          ru: "hsl(var(--geo-ru))",
          foreign: "hsl(var(--geo-foreign))",
        },
        // Domain semantics — knowledge-graph gaps and contradictions.
        gap: "hsl(var(--gap))",
        contradiction: "hsl(var(--contradiction))",
        // Knowledge-graph node types (subgraph visualization).
        node: {
          material: "hsl(var(--node-material))",
          process: "hsl(var(--node-process))",
          equipment: "hsl(var(--node-equipment))",
          result: "hsl(var(--node-result))",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
    },
  },
  plugins: [animate],
};

export default config;
