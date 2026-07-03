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
  { type: "Material", label: "Материал", token: "--node-material", dot: "bg-node-material" },
  { type: "Process", label: "Процесс", token: "--node-process", dot: "bg-node-process" },
  { type: "Equipment", label: "Оборудование", token: "--node-equipment", dot: "bg-node-equipment" },
  { type: "Result", label: "Результат", token: "--node-result", dot: "bg-node-result" },
] as const;

/** Cytoscape stylesheet built from the current theme's CSS variables. */
export function buildSubgraphStylesheet(): cytoscape.StylesheetStyle[] {
  const edgeColor = cssHsl("--border", "#cbd5e1");
  const contradiction = cssHsl("--contradiction", "#e11d48");

  const base: cytoscape.StylesheetStyle[] = [
    {
      selector: "node",
      style: {
        label: "data(label)",
        "font-size": 11,
        "text-valign": "center",
        "text-halign": "center",
        "text-wrap": "wrap",
        "text-max-width": "120px",
        shape: "round-rectangle",
        width: "label",
        height: "label",
        padding: "10px",
        "background-opacity": 0.15,
        "border-width": 1.5,
      },
    },
    {
      selector: "edge",
      style: {
        width: 1.5,
        "line-color": edgeColor,
        "target-arrow-color": edgeColor,
        "target-arrow-shape": "triangle",
        "curve-style": "bezier",
        "font-size": 9,
        color: cssHsl("--muted-foreground", "#64748b"),
        label: "data(label)",
        "text-background-opacity": 0,
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
  ];

  const byType: cytoscape.StylesheetStyle[] = NODE_TYPES.map(({ type, token }) => {
    const color = cssHsl(token, "#64748b");
    return {
      selector: `node[type = "${type}"]`,
      style: {
        "background-color": color,
        "border-color": color,
        color,
      },
    };
  });

  return [...base, ...byType];
}
