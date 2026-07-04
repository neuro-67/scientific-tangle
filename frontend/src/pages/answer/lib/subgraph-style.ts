import type cytoscape from "cytoscape";

/**
 * Read an HSL design token from index.css and produce a color string that
 * Cytoscape's parser understands. Tokens are stored space-separated
 * (`190 90% 42%`), but Cytoscape only accepts the comma form
 * (`hsl(190, 90%, 42%)`), so we normalize the separators here.
 */
const cssHsl = (name: string, fallback: string): string => {
  if (typeof window === "undefined") return fallback;
  const value = getComputedStyle(document.documentElement)
    .getPropertyValue(name)
    .trim();
  if (!value) return fallback;
  const parts = value.split(/\s+/);
  return parts.length === 3 ? `hsl(${parts.join(", ")})` : fallback;
};

/**
 * Node type palette. Two families of types are mixed here:
 *   - the manual ontology (Material / Process / Equipment / Result) that the
 *     UI toolbar lets the user create; those pull colors from CSS variables so
 *     they follow the theme;
 *   - the actual Neo4j domain labels (Expert / Facility / Publication / etc.)
 *     that come back from /query/ask; those are hex-colored directly so we
 *     don't have to add a CSS variable per label.
 * The `dot` field is a literal Tailwind class or a raw color for the legend
 * swatch; when it starts with `#` the SubgraphView renders it inline instead
 * of via a class.
 */
export const NODE_TYPES = [
  {
    type: "Material",
    label: "Материал",
    colorToken: "--node-material",
    bgToken: "--node-material-bg",
    color: null,
    bg: null,
    dot: "bg-node-material",
    icon: "⚪",
  },
  {
    type: "Process",
    label: "Процесс",
    colorToken: "--node-process",
    bgToken: "--node-process-bg",
    color: null,
    bg: null,
    dot: "bg-node-process",
    icon: "⚙️",
  },
  {
    type: "Equipment",
    label: "Оборудование",
    colorToken: "--node-equipment",
    bgToken: "--node-equipment-bg",
    color: null,
    bg: null,
    dot: "bg-node-equipment",
    icon: "🔧",
  },
  {
    type: "Result",
    label: "Результат",
    colorToken: "--node-result",
    bgToken: "--node-result-bg",
    color: null,
    bg: null,
    dot: "bg-node-result",
    icon: "✅",
  },
  {
    type: "Expert",
    label: "Эксперт",
    colorToken: null,
    bgToken: null,
    color: "#4F46E5",
    bg: "#EEF2FF",
    dot: "#4F46E5",
    icon: "👤",
  },
  {
    type: "Facility",
    label: "Организация",
    colorToken: null,
    bgToken: null,
    color: "#0EA5E9",
    bg: "#E0F2FE",
    dot: "#0EA5E9",
    icon: "🏛️",
  },
  {
    type: "Publication",
    label: "Публикация",
    colorToken: null,
    bgToken: null,
    color: "#8B5CF6",
    bg: "#F5F3FF",
    dot: "#8B5CF6",
    icon: "📄",
  },
  {
    type: "Measurement",
    label: "Измерение",
    colorToken: null,
    bgToken: null,
    color: "#F59E0B",
    bg: "#FEF3C7",
    dot: "#F59E0B",
    icon: "📏",
  },
  {
    type: "Finding",
    label: "Утверждение",
    colorToken: null,
    bgToken: null,
    color: "#059669",
    bg: "#D1FAE5",
    dot: "#059669",
    icon: "💡",
  },
  {
    type: "Source",
    label: "Источник",
    colorToken: null,
    bgToken: null,
    color: "#6B7280",
    bg: "#F3F4F6",
    dot: "#6B7280",
    icon: "📚",
  },
] as const;

/** Cytoscape stylesheet built from the current theme's CSS variables. */
export function buildSubgraphStylesheet(): cytoscape.StylesheetStyle[] {
  const edgeColor = cssHsl("--graph-edge", "#94a3b8");
  const contradiction = cssHsl("--contradiction", "#e11d48");
  const gap = cssHsl("--gap", "#f97316");

  const base = [
    {
      selector: "node",
      style: {
        label: "data(label)",
        "font-size": 20,
        "font-weight": 700,
        "text-valign": "center",
        "text-halign": "center",
        "text-wrap": "wrap",
        "text-max-width": "160px",
        "line-height": 1.2,
        "text-outline-color": "#ffffff",
        "text-outline-width": 4,
        "text-outline-opacity": 0.95,
        shape: "ellipse",
        width: "190px",
        height: "190px",
        padding: "0px",
        "background-opacity": 1,
        "border-width": 4,
        "shadow-blur": 24,
        "shadow-opacity": 0.5,
        "shadow-offset-x": 0,
        "shadow-offset-y": 0,
      },
    },
    {
      selector: "edge",
      style: {
        width: 5,
        "line-color": edgeColor,
        "target-arrow-shape": "triangle",
        "target-arrow-color": edgeColor,
        "arrow-scale": 1.8,
        "curve-style": "bezier",
        label: "data(label)",
        "font-size": 16,
        "font-weight": 700,
        color: "#1e293b",
        "text-valign": "center",
        "text-halign": "center",
        "text-background-color": "#ffffff",
        "text-background-opacity": 1,
        "text-background-padding": 6,
        "text-background-shape": "roundrectangle",
        "text-outline-color": "#ffffff",
        "text-outline-width": 3,
        "text-outline-opacity": 1,
        "text-margin-y": -20,
        "z-index": 1,
      },
    },
    {
      selector: 'edge[type = "contradicts"]',
      style: {
        "line-color": contradiction,
        "target-arrow-color": contradiction,
        "line-style": "dashed",
        width: 2,
      },
    },
    {
      selector: 'node[type = "Comment"]',
      style: {
        shape: "roundrectangle",
        width: "label",
        height: "label",
        padding: "8px",
        "background-color": "#f1f5f9",
        "border-color": "#cbd5e1",
        "border-width": 1,
        color: "#475569",
        "font-size": 12,
        "text-max-width": "140px",
        "text-valign": "center",
        "text-halign": "center",
        "text-outline-color": "#ffffff",
        "text-outline-width": 1,
        "shadow-blur": 0,
      },
    },
    {
      selector: "node[revisionCount > 0]",
      style: {
        "border-width": 8,
        "border-color": gap,
        "overlay-color": gap,
        "overlay-opacity": 0.08,
        "text-background-color": "#ffffff",
        "text-background-opacity": 0.9,
        "text-background-padding": 5,
        "text-background-shape": "roundrectangle",
      },
    },
    {
      selector: "node:selected, edge:selected",
      style: {
        "border-width": 4,
        "border-color": "#0f172a",
        "line-color": "#0f172a",
        "target-arrow-color": "#0f172a",
        "z-index": 999,
      },
    },
  ] as unknown as cytoscape.StylesheetStyle[];

  const byType: cytoscape.StylesheetStyle[] = NODE_TYPES.map((t) => {
    const color = t.colorToken ? cssHsl(t.colorToken, t.color ?? "#64748b") : (t.color ?? "#64748b");
    const bg = t.bgToken ? cssHsl(t.bgToken, t.bg ?? "#f1f5f9") : (t.bg ?? "#f1f5f9");
    return {
      selector: `node[type = "${t.type}"]`,
      style: {
        "background-color": bg,
        "border-color": color,
        color,
        "shadow-color": color,
      },
    };
  });

  return [...base, ...byType];
}
