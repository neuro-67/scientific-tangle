import type cytoscape from "cytoscape";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import CytoscapeComponent from "react-cytoscapejs";
import { toast } from "sonner";

import {
  createGraphNode,
  deleteGraphEdge,
  deleteGraphNode,
  updateGraphEdge,
  updateGraphNode,
} from "@/entities/graph";
import type { AnswerSubgraph, GraphEdge, GraphNode } from "@/entities/query";
import { handleApiError } from "@/shared/lib/api-error";

import { NODE_TYPES, buildSubgraphStylesheet } from "../lib/subgraph-style";

type Props = {
  subgraph: AnswerSubgraph;
};

type Mode = "select" | "addNode" | "addComment";

/**
 * Force-directed layout — hub nodes (like a facility with many expert
 * neighbors) get pushed to the center automatically, and disconnected
 * meta-nodes end up in a readable cluster instead of one horizontal row.
 * Cytoscape core ships `cose`; no extension install needed.
 */
function buildLayout(): cytoscape.LayoutOptions {
  return {
    name: "cose",
    fit: true,
    padding: 60,
    animate: false,
    randomize: true,
    nodeRepulsion: () => 800_000,
    idealEdgeLength: () => 180,
    edgeElasticity: () => 120,
    gravity: 0.4,
    numIter: 1200,
    initialTemp: 200,
    coolingFactor: 0.95,
    minTemp: 1.0,
  } as unknown as cytoscape.LayoutOptions;
}

const TYPE_OPTIONS = ["Material", "Process", "Equipment", "Result"];

let __tempSeq = 0;
const tempId = (prefix: string) => `__tmp_${prefix}_${++__tempSeq}`;

/** Cytoscape rendering of the answer subgraph + editing toolbar + legend. */
export function SubgraphView({ subgraph }: Props) {
  const [nodes, setNodes] = useState<GraphNode[]>(subgraph.nodes);
  const [edges, setEdges] = useState<GraphEdge[]>(subgraph.edges);
  const [mode, setMode] = useState<Mode>("select");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);

  const cyRef = useRef<cytoscape.Core | null>(null);
  const positionsRef = useRef<Record<string, cytoscape.Position>>({});

  // Sync state when a different subgraph is loaded (nav to another answer).
  useEffect(() => {
    setNodes(subgraph.nodes);
    setEdges(subgraph.edges);
    positionsRef.current = {};
    setSelectedId(null);
  }, [subgraph]);

  const stylesheet = useMemo(() => buildSubgraphStylesheet(), []);
  const initialLayout = useMemo(() => buildLayout(), []);

  const selectedNode = useMemo(
    () => nodes.find((n) => n.id === selectedId) ?? null,
    [nodes, selectedId]
  );
  const selectedEdge = useMemo(
    () => edges.find((e) => e.id === selectedId) ?? null,
    [edges, selectedId]
  );

  const elements = useMemo<cytoscape.ElementDefinition[]>(() => {
    return [
      ...nodes.map((n) => ({
        data: {
          id: n.id,
          label: n.label,
          type: n.type,
        },
        position: positionsRef.current[n.id],
      })),
      ...edges.map((e) => ({
        data: {
          id: e.id,
          source: e.source,
          target: e.target,
          type: e.type,
          label: e.label ?? "",
        },
      })),
    ];
  }, [nodes, edges]);

  const markSelected = useCallback((id: string | null) => {
    setSelectedId(id);
    if (cyRef.current && id) {
      const el = cyRef.current.getElementById(id);
      if (el.length) el.select();
    }
  }, []);

  const clearSelection = useCallback(() => {
    setSelectedId(null);
    cyRef.current?.elements().unselect();
  }, []);

  // ---- Mutations ----
  // Each editor action is optimistic: mutate local state immediately with a
  // temp id, fire the request; on success swap temp id → server id, on error
  // roll back and toast. This keeps the graph responsive on slow networks and
  // avoids a full-page loading state for every action.

  const addNode = useCallback(
    async (position: cytoscape.Position, type: string, label: string) => {
      const localId = tempId(type === "Comment" ? "c" : "n");
      positionsRef.current[localId] = position;
      setNodes((prev) => [...prev, { id: localId, label, type }]);
      markSelected(localId);
      try {
        const created = await createGraphNode({ type, label });
        positionsRef.current[created.id] = positionsRef.current[localId];
        delete positionsRef.current[localId];
        setNodes((prev) =>
          prev.map((n) => (n.id === localId ? created : n))
        );
        markSelected(created.id);
      } catch (err) {
        setNodes((prev) => prev.filter((n) => n.id !== localId));
        delete positionsRef.current[localId];
        handleApiError(err, { fallback: "Не удалось создать узел" });
      }
    },
    [markSelected]
  );

  const updateNode = useCallback(
    async (id: string, label: string) => {
      const prevLabel = nodes.find((n) => n.id === id)?.label;
      setNodes((prev) => prev.map((n) => (n.id === id ? { ...n, label } : n)));
      // Temp ids belong to nodes that haven't been persisted yet — skip PATCH
      // and let the follow-up server response own the label. This shouldn't
      // happen in practice (double-click on freshly-created node before the
      // POST resolves), but the guard is cheap.
      if (id.startsWith("__tmp_")) return;
      try {
        await updateGraphNode(id, { label });
      } catch (err) {
        setNodes((prev) =>
          prev.map((n) => (n.id === id ? { ...n, label: prevLabel ?? "" } : n))
        );
        handleApiError(err, { fallback: "Не удалось обновить узел" });
      }
    },
    [nodes]
  );

  const updateEdge = useCallback(
    async (id: string, label: string) => {
      const prevLabel = edges.find((e) => e.id === id)?.label;
      setEdges((prev) => prev.map((e) => (e.id === id ? { ...e, label } : e)));
      if (id.startsWith("__tmp_")) return;
      try {
        await updateGraphEdge(id, { label });
      } catch (err) {
        setEdges((prev) =>
          prev.map((e) =>
            e.id === id ? { ...e, label: prevLabel } : e
          )
        );
        handleApiError(err, { fallback: "Не удалось обновить связь" });
      }
    },
    [edges]
  );

  const removeSelected = useCallback(async () => {
    if (!selectedId) return;
    const isNode = nodes.some((n) => n.id === selectedId);
    const isEdge = !isNode && edges.some((e) => e.id === selectedId);

    // Snapshot for rollback.
    const prevNodes = nodes;
    const prevEdges = edges;

    // Optimistic remove.
    if (isNode) {
      setNodes((prev) => prev.filter((n) => n.id !== selectedId));
      // Neo4j DETACH DELETE removes attached edges; mirror that on the client.
      setEdges((prev) =>
        prev.filter(
          (e) => e.source !== selectedId && e.target !== selectedId
        )
      );
    } else if (isEdge) {
      setEdges((prev) => prev.filter((e) => e.id !== selectedId));
    }
    setSelectedId(null);

    if (selectedId.startsWith("__tmp_")) return; // never persisted

    try {
      if (isNode) await deleteGraphNode(selectedId);
      else if (isEdge) await deleteGraphEdge(selectedId);
      toast.success("Удалено");
    } catch (err) {
      setNodes(prevNodes);
      setEdges(prevEdges);
      handleApiError(err, { fallback: "Не удалось удалить" });
    }
  }, [selectedId, nodes, edges]);

  const handleEdit = useCallback(() => {
    if (selectedNode) {
      const next = window.prompt("Название узла:", selectedNode.label);
      if (next !== null && next !== selectedNode.label)
        void updateNode(selectedNode.id, next);
    } else if (selectedEdge) {
      const next = window.prompt("Название связи:", selectedEdge.label || "");
      if (next !== null && next !== selectedEdge.label)
        void updateEdge(selectedEdge.id, next);
    }
  }, [selectedNode, selectedEdge, updateNode, updateEdge]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't hijack Delete/Backspace while the user is typing in a prompt or
      // some other input — only trigger when focus is on the body/graph.
      const t = e.target as HTMLElement | null;
      const typing =
        t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.isContentEditable);
      if (typing) return;
      if (e.key === "Delete" || e.key === "Backspace") {
        e.preventDefault();
        void removeSelected();
      } else if (e.key === "Escape") {
        if (isFullscreen) setIsFullscreen(false);
        setMode("select");
        clearSelection();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [removeSelected, clearSelection, isFullscreen]);

  // Poke Cytoscape to recompute its viewport after the parent size flips.
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    const id = window.setTimeout(() => {
      cy.resize();
      cy.fit(undefined, 60);
    }, 50);
    return () => window.clearTimeout(id);
  }, [isFullscreen]);

  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;

    const handleTapNode = (evt: cytoscape.EventObject) => {
      const id = evt.target.id();
      markSelected(id);
    };

    const handleTapEdge = (evt: cytoscape.EventObject) => {
      const id = evt.target.id();
      markSelected(id);
    };

    const handleDblTap = (evt: cytoscape.EventObject) => {
      const id = evt.target.id();
      if (!id) return;
      markSelected(id);
      handleEdit();
    };

    const handleTapBg = (evt: cytoscape.EventObject) => {
      // Cytoscape fires `tap` on cy for both background and elements. We only
      // want background — otherwise a node tap immediately clears the very
      // selection that handleTapNode just set.
      if (evt.target !== cy) return;
      if (mode === "addNode") {
        const label = window.prompt("Название шара:", "Новый узел");
        if (label === null) return;
        const type = window.prompt(
          `Тип (${TYPE_OPTIONS.join(", ")}):`,
          "Material"
        );
        if (!type || !TYPE_OPTIONS.includes(type)) return;
        void addNode(evt.position, type, label);
      } else if (mode === "addComment") {
        const text = window.prompt("Текст комментария:", "Комментарий");
        if (text === null) return;
        void addNode(evt.position, "Comment", text);
      } else {
        clearSelection();
      }
    };

    const handleDragFree = (evt: cytoscape.EventObject) => {
      const node = evt.target as cytoscape.NodeSingular;
      positionsRef.current[node.id()] = { ...node.position() };
    };

    cy.on("tap", "node", handleTapNode);
    cy.on("tap", "edge", handleTapEdge);
    cy.on("dbltap", "node", handleDblTap);
    cy.on("dbltap", "edge", handleDblTap);
    cy.on("tap", handleTapBg);
    cy.on("dragfree", "node", handleDragFree);

    return () => {
      cy.off("tap", "node", handleTapNode);
      cy.off("tap", "edge", handleTapEdge);
      cy.off("dbltap", "node", handleDblTap);
      cy.off("dbltap", "edge", handleDblTap);
      cy.off("tap", handleTapBg);
      cy.off("dragfree", "node", handleDragFree);
    };
  }, [
    mode,
    addNode,
    markSelected,
    clearSelection,
    handleEdit,
  ]);

  const toolbarButton = (key: Mode, label: string, title: string) => (
    <button
      key={key}
      type="button"
      title={title}
      onClick={() => {
        setMode(key);
        clearSelection();
      }}
      className={`rounded-lg px-2.5 py-1.5 text-xs font-medium transition-colors ${
        mode === key
          ? "bg-primary text-white"
          : "bg-muted text-foreground hover:bg-muted/80"
      }`}
    >
      {label}
    </button>
  );

  // In fullscreen we jump out of the normal card and cover the viewport.
  // The graph inside adapts because it fills its parent.
  const containerClass = isFullscreen
    ? "fixed inset-0 z-50 flex h-screen w-screen flex-col gap-2 bg-background p-4"
    : "flex h-full flex-col gap-2";

  return (
    <div className={containerClass}>
      <div className="flex flex-wrap items-center gap-2">
        {toolbarButton("select", "Выбрать", "Выделить элемент")}
        {toolbarButton("addNode", "+ Шар", "Добавить узел (кликни в свободное место)")}
        {toolbarButton("addComment", "+ Коммент", "Добавить комментарий")}
        <button
          type="button"
          disabled={!selectedId}
          onClick={handleEdit}
          className="rounded-lg px-2.5 py-1.5 text-xs font-medium transition-colors disabled:opacity-50 bg-muted text-foreground hover:bg-muted/80"
        >
          Изменить текст
        </button>
        <button
          type="button"
          disabled={!selectedId}
          onClick={() => void removeSelected()}
          className="rounded-lg px-2.5 py-1.5 text-xs font-medium transition-colors disabled:opacity-50 bg-destructive text-destructive-foreground hover:bg-destructive/90"
        >
          Удалить
        </button>
        <button
          type="button"
          onClick={() => setIsFullscreen((v) => !v)}
          title={isFullscreen ? "Свернуть" : "На весь экран"}
          className="rounded-lg px-2.5 py-1.5 text-xs font-medium transition-colors bg-muted text-foreground hover:bg-muted/80"
        >
          {isFullscreen ? "⤡ Свернуть" : "⛶ На весь экран"}
        </button>
        <span className="ml-auto text-[11px] text-muted-foreground">
          Правки идут в общий граф Neo4j
        </span>
      </div>

      <div className="min-h-0 flex-1 overflow-hidden rounded-[14px] border border-input bg-muted/20">
        <CytoscapeComponent
          elements={elements}
          stylesheet={stylesheet}
          layout={initialLayout}
          wheelSensitivity={2}
          style={{ width: "100%", height: "100%" }}
          cy={(cy) => {
            cyRef.current = cy;
            positionsRef.current = Object.fromEntries(
              cy.nodes().map((n) => [n.id(), { ...n.position() }])
            );
          }}
        />
      </div>

      <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">
        {NODE_TYPES.map((t) => {
          // Hex colors render inline; tailwind classes render via className so
          // JIT can pick them up. Splitting them here keeps the config file
          // free of a colossal switch statement.
          const isHex = t.dot.startsWith("#");
          return (
            <span key={t.type} className="flex items-center gap-1.5">
              {isHex ? (
                <span
                  className="h-2.5 w-2.5 rounded-full"
                  style={{ backgroundColor: t.dot }}
                />
              ) : (
                <span className={`h-2.5 w-2.5 rounded-full ${t.dot}`} />
              )}
              <span>
                {t.icon} {t.label}
              </span>
            </span>
          );
        })}
        <span className="flex items-center gap-1.5">
          <span className="h-0 w-4 border-t-2 border-dashed border-contradiction" />
          противоречие
        </span>
      </div>
    </div>
  );
}
