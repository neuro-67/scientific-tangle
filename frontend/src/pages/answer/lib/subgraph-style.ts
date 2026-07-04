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
 * Ontology node types forming the chain material→process→equipment→result.
 * `dot` is a literal Tailwind class so the legend colors survive purging.
 */
export const NODE_TYPES = [
  {
    type: "Material",
    label: "Материал",
    colorToken: "--node-material",
    bgToken: "--node-material-bg",
    dot: "bg-node-material",
  },
  {
    type: "Process",
    label: "Процесс",
    colorToken: "--node-process",
    bgToken: "--node-process-bg",
    dot: "bg-node-process",
  },
  {
    type: "Equipment",
    label: "Оборудование",
    colorToken: "--node-equipment",
    bgToken: "--node-equipment-bg",
    dot: "bg-node-equipment",
  },
  {
    type: "Result",
    label: "Результат",
    colorToken: "--node-result",
    bgToken: "--node-result-bg",
    dot: "bg-node-result",
  },
] as const;

/** Cytoscape stylesheet built from the current theme's CSS variables. */
export function buildSubgraphStylesheet(): cytoscape.StylesheetStyle[] {
  const edgeColor = cssHsl("--graph-edge", "#94a3b8");
  const contradiction = cssHsl("--contradiction", "#e11d48");

  const base: cytoscape.StylesheetStyle[] = [
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
      } as any,
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
      } as any,
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
      } as any,
    },
    {
      selector: "node:selected, edge:selected",
      style: {
        "border-width": 4,
        "border-color": "#0f172a",
        "line-color": "#0f172a",
        "target-arrow-color": "#0f172a",
        "z-index": 999,
      } as any,
    },
  ];

  const byType: cytoscape.StylesheetStyle[] = NODE_TYPES.map(
    ({ type, colorToken, bgToken }) => {
      const color = cssHsl(colorToken, "#64748b");
      const bg = cssHsl(bgToken, "#f1f5f9");
      return {
        selector: `node[type = "${type}"]`,
        style: {
          "background-color": bg,
          "border-color": color,
          color,
          "shadow-color": color,
        },
      };
    }
  );

  return [...base, ...byType];
}
