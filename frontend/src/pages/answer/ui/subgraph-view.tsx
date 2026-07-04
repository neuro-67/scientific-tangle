import type cytoscape from "cytoscape";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import CytoscapeComponent from "react-cytoscapejs";
import { toast } from "sonner";

import {
  createGraphEdge,
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

type Mode = "select" | "addNode" | "addEdge" | "addComment";

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
/**
 * Default relationship type for user-created edges. Neo4j rel types are part
 * of the schema (uppercase snake_case), so we can't use the user-provided
 * label directly as the type — that goes into r.label.
 */
const DEFAULT_EDGE_TYPE = "RELATED";

let __tempSeq = 0;
const tempId = (prefix: string) => `__tmp_${prefix}_${++__tempSeq}`;

/** Cytoscape rendering of the answer subgraph + editing toolbar + legend. */
export function SubgraphView({ subgraph }: Props) {
  const [nodes, setNodes] = useState<GraphNode[]>(subgraph.nodes);
  const [edges, setEdges] = useState<GraphEdge[]>(subgraph.edges);
  const [mode, setMode] = useState<Mode>("select");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [edgeSource, setEdgeSource] = useState<string | null>(null);

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
    setEdgeSource(null);
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

  const addEdge = useCallback(
    async (source: string, target: string, label: string) => {
      const localId = tempId("e");
      setEdges((prev) => [
        ...prev,
        { id: localId, source, target, type: DEFAULT_EDGE_TYPE, label },
      ]);
      markSelected(localId);
      try {
        const created = await createGraphEdge({
          source,
          target,
          type: DEFAULT_EDGE_TYPE,
          label,
        });
        setEdges((prev) =>
          prev.map((e) =>
            e.id === localId
              ? {
                  id: created.id,
                  source: created.source,
                  target: created.target,
                  type: created.type,
                  label: created.label ?? "",
                }
              : e
          )
        );
        markSelected(created.id);
      } catch (err) {
        setEdges((prev) => prev.filter((e) => e.id !== localId));
        handleApiError(err, { fallback: "Не удалось создать связь" });
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
      if (e.key === "Delete" || e.key === "Backspace") {
        e.preventDefault();
        void removeSelected();
      } else if (e.key === "Escape") {
        setMode("select");
        clearSelection();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [removeSelected, clearSelection]);

  // Disable node dragging while drawing an edge.
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    if (mode === "addEdge") {
      cy.nodes().ungrabify();
    } else {
      cy.nodes().grabify();
    }
  }, [mode]);

  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;

    const PREVIEW_NODE = "__preview-target";
    const PREVIEW_EDGE = "__preview-edge";
    const draggingRef = { current: false };

    const removePreview = () => {
      cy.getElementById(PREVIEW_EDGE).remove();
      cy.getElementById(PREVIEW_NODE).remove();
    };

    const createPreview = (sourceId: string, pos: cytoscape.Position) => {
      cy.add([
        {
          group: "nodes",
          data: { id: PREVIEW_NODE },
          position: pos,
          style: { width: 1, height: 1, "background-opacity": 0 },
        },
        {
          group: "edges",
          data: { id: PREVIEW_EDGE, source: sourceId, target: PREVIEW_NODE },
          style: {
            "line-style": "dashed",
            "line-color": "#94a3b8",
            width: 3,
            "target-arrow-shape": "none",
          },
        },
      ]);
    };

    const movePreview = (pos: cytoscape.Position) => {
      const n = cy.getElementById(PREVIEW_NODE);
      if (n.length) n.position(pos);
    };

    const handleTapNode = (evt: cytoscape.EventObject) => {
      const id = evt.target.id();
      if (draggingRef.current) return;
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
      if (draggingRef.current) return;
      if (mode === "addEdge") return;
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

    const handleMouseDownNode = (evt: cytoscape.EventObject) => {
      if (mode !== "addEdge") return;
      const id = evt.target.id();
      draggingRef.current = true;
      setEdgeSource(id);
      createPreview(id, evt.position);
    };

    const handleMouseMove = (evt: cytoscape.EventObject) => {
      if (mode !== "addEdge" || !draggingRef.current) return;
      movePreview(evt.position);
    };

    const handleMouseUp = () => {
      if (mode !== "addEdge" || !draggingRef.current) return;
      const sourceId = edgeSource;
      draggingRef.current = false;
      removePreview();
      setEdgeSource(null);
      if (!sourceId) return;
      const hovered = cy
        .nodes(":hover")
        .filter((n) => n.id() !== PREVIEW_NODE && n.id() !== sourceId);
      const target = hovered.first();
      if (target.length) {
        const label =
          window.prompt("Название связи:", "связано с") || "связано с";
        void addEdge(sourceId, target.id(), label);
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
    cy.on("mousedown", "node", handleMouseDownNode);
    cy.on("mousemove", handleMouseMove);
    cy.on("mouseup", handleMouseUp);
    cy.on("dragfree", "node", handleDragFree);

    return () => {
      cy.off("tap", "node", handleTapNode);
      cy.off("tap", "edge", handleTapEdge);
      cy.off("dbltap", "node", handleDblTap);
      cy.off("dbltap", "edge", handleDblTap);
      cy.off("tap", handleTapBg);
      cy.off("mousedown", "node", handleMouseDownNode);
      cy.off("mousemove", handleMouseMove);
      cy.off("mouseup", handleMouseUp);
      cy.off("dragfree", "node", handleDragFree);
    };
  }, [
    mode,
    edgeSource,
    addNode,
    addEdge,
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

  return (
    <div className="flex h-full flex-col gap-2">
      <div className="flex flex-wrap items-center gap-2">
        {toolbarButton("select", "Выбрать", "Выделить элемент")}
        {toolbarButton("addNode", "+ Шар", "Добавить узел (кликни в свободное место)")}
        {toolbarButton("addEdge", "+ Связь", "Соединить два узла: зажать на узле → перетянуть")}
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
        <span className="ml-auto text-[11px] text-muted-foreground">
          Правки идут в общий граф Neo4j
        </span>
      </div>

      <div className="min-h-0 flex-1 overflow-hidden rounded-[14px] border border-input bg-muted/20">
        <CytoscapeComponent
          elements={elements}
          stylesheet={stylesheet}
          layout={initialLayout}
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
