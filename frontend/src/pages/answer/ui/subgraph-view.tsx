import type cytoscape from "cytoscape";
import { useMemo } from "react";
import CytoscapeComponent from "react-cytoscapejs";

import type { AnswerSubgraph } from "@/entities/query";

import { NODE_TYPES, buildSubgraphStylesheet } from "../lib/subgraph-style";

type Props = {
  subgraph: AnswerSubgraph;
};

const LAYOUT = {
  name: "breadthfirst",
  directed: true,
  spacingFactor: 1.15,
  padding: 16,
} as cytoscape.LayoutOptions;

/** Cytoscape rendering of the answer subgraph + a color legend. */
export function SubgraphView({ subgraph }: Props) {
  const elements = useMemo<cytoscape.ElementDefinition[]>(
    () => [
      ...subgraph.nodes.map((n) => ({
        data: { id: n.id, label: n.label, type: n.type },
      })),
      ...subgraph.edges.map((e) => ({
        data: {
          id: e.id,
          source: e.source,
          target: e.target,
          type: e.type,
          label: e.type,
        },
      })),
    ],
    [subgraph]
  );

  const stylesheet = useMemo(() => buildSubgraphStylesheet(), []);

  return (
    <div className="flex flex-col gap-3">
      <div className="h-80 w-full overflow-hidden rounded-md border bg-muted/20">
        <CytoscapeComponent
          elements={elements}
          stylesheet={stylesheet}
          layout={LAYOUT}
          style={{ width: "100%", height: "100%" }}
        />
      </div>
      <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">
        {NODE_TYPES.map((t) => (
          <span key={t.type} className="flex items-center gap-1.5">
            <span className={`h-2.5 w-2.5 rounded-full ${t.dot}`} />
            {t.label}
          </span>
        ))}
        <span className="flex items-center gap-1.5">
          <span className="h-0 w-4 border-t-2 border-dashed border-contradiction" />
          противоречие
        </span>
      </div>
    </div>
  );
}
