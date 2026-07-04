import type cytoscape from "cytoscape";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import CytoscapeComponent from "react-cytoscapejs";

import type { AnswerSubgraph, GraphEdge, GraphNode } from "@/entities/query";

import { NODE_TYPES, buildSubgraphStylesheet } from "../lib/subgraph-style";

type Props = {
  subgraph: AnswerSubgraph;
};

type Mode = "select" | "addNode" | "addEdge" | "addComment";

const TYPE_ORDER: Record<string, number> = {
  Material: 0,
  Process: 1,
  Equipment: 2,
  Result: 3,
  Comment: 4,
};

function buildLayout(nodeCount: number): cytoscape.LayoutOptions {
  return {
    name: "grid",
    fit: true,
    padding: 24,
    rows: 1,
    cols: nodeCount,
    avoidOverlap: true,
    condense: false,
    animate: false,
  } as any;
}

const TYPE_OPTIONS = ["Material", "Process", "Equipment", "Result"];

function nextId(prefix: string, existing: string[]) {
  let i = 1;
  while (existing.includes(`${prefix}${i}`)) i++;
  return `${prefix}${i}`;
}

/** Cytoscape rendering of the answer subgraph + editing toolbar + legend. */
export function SubgraphView({ subgraph }: Props) {
  const [nodes, setNodes] = useState<GraphNode[]>(subgraph.nodes);
  const [edges, setEdges] = useState<GraphEdge[]>(subgraph.edges);
  const [mode, setMode] = useState<Mode>("select");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [edgeSource, setEdgeSource] = useState<string | null>(null);

  const cyRef = useRef<cytoscape.Core | null>(null);
  const prevCountRef = useRef({ nodes: nodes.length, edges: edges.length });

  const stylesheet = useMemo(() => buildSubgraphStylesheet(), []);

  const selectedNode = useMemo(
    () => nodes.find((n) => n.id === selectedId) ?? null,
    [nodes, selectedId]
  );
  const selectedEdge = useMemo(
    () => edges.find((e) => e.id === selectedId) ?? null,
    [edges, selectedId]
  );

  const elements = useMemo<cytoscape.ElementDefinition[]>(() => {
    const sortedNodes = [...nodes].sort(
      (a, b) => (TYPE_ORDER[a.type] ?? 99) - (TYPE_ORDER[b.type] ?? 99)
    );
    return [
      ...sortedNodes.map((n) => ({
        data: {
          id: n.id,
          label: n.label,
          type: n.type,
        },
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
  }, [nodes, edges, selectedId]);

  const runLayout = useCallback(() => {
    if (!cyRef.current) return;
    cyRef.current.layout(buildLayout(nodes.length)).run();
  }, [nodes.length]);

  useEffect(() => {
    const prev = prevCountRef.current;
    if (prev.nodes !== nodes.length || prev.edges !== edges.length) {
      prevCountRef.current = { nodes: nodes.length, edges: edges.length };
      // Defer layout to the next tick so Cytoscape has updated elements.
      requestAnimationFrame(runLayout);
    }
  }, [nodes.length, edges.length, runLayout]);

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

  const addNode = useCallback(
    (_position: cytoscape.Position, type: string, label: string) => {
      const id = nextId(
        type === "Comment" ? "c" : "n",
        nodes.map((n) => n.id)
      );
      const newNode: GraphNode = {
        id,
        label,
        type,
      };
      setNodes((prev) => [...prev, newNode]);
      markSelected(id);
    },
    [nodes, markSelected]
  );

  const addEdge = useCallback(
    (source: string, target: string, label: string) => {
      const id = nextId(
        "e",
        edges.map((e) => e.id)
      );
      setEdges((prev) => [
        ...prev,
        {
          id,
          source,
          target,
          type: "custom",
          label,
        },
      ]);
      markSelected(id);
    },
    [edges, markSelected]
  );

  const updateNode = useCallback((id: string, label: string) => {
    setNodes((prev) => prev.map((n) => (n.id === id ? { ...n, label } : n)));
  }, []);

  const updateEdge = useCallback((id: string, label: string) => {
    setEdges((prev) => prev.map((e) => (e.id === id ? { ...e, label } : e)));
  }, []);

  const removeSelected = useCallback(() => {
    if (!selectedId) return;
    setNodes((prev) => prev.filter((n) => n.id !== selectedId));
    setEdges((prev) =>
      prev.filter(
        (e) =>
          e.id !== selectedId &&
          e.source !== selectedId &&
          e.target !== selectedId
      )
    );
    setSelectedId(null);
  }, [selectedId]);

  const handleEdit = useCallback(() => {
    if (selectedNode) {
      const next = window.prompt("Название узла:", selectedNode.label);
      if (next !== null) updateNode(selectedNode.id, next);
    } else if (selectedEdge) {
      const next = window.prompt("Название связи:", selectedEdge.label || "");
      if (next !== null) updateEdge(selectedEdge.id, next);
    }
  }, [selectedNode, selectedEdge, updateNode, updateEdge]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Delete" || e.key === "Backspace") {
        e.preventDefault();
        removeSelected();
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
        addNode(evt.position, type, label);
      } else if (mode === "addComment") {
        const text = window.prompt("Текст комментария:", "Комментарий");
        if (text === null) return;
        addNode(evt.position, "Comment", text);
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
        addEdge(sourceId, target.id(), label);
      }
    };

    cy.on("tap", "node", handleTapNode);
    cy.on("tap", "edge", handleTapEdge);
    cy.on("dbltap", "node", handleDblTap);
    cy.on("dbltap", "edge", handleDblTap);
    cy.on("tap", handleTapBg);
    cy.on("mousedown", "node", handleMouseDownNode);
    cy.on("mousemove", handleMouseMove);
    cy.on("mouseup", handleMouseUp);

    return () => {
      cy.off("tap", "node", handleTapNode);
      cy.off("tap", "edge", handleTapEdge);
      cy.off("dbltap", "node", handleDblTap);
      cy.off("dbltap", "edge", handleDblTap);
      cy.off("tap", handleTapBg);
      cy.off("mousedown", "node", handleMouseDownNode);
      cy.off("mousemove", handleMouseMove);
      cy.off("mouseup", handleMouseUp);
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
        {toolbarButton("addNode", "+ Шар", "Добавить узел")}
        {toolbarButton("addEdge", "+ Связь", "Соединить два узла")}
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
          onClick={removeSelected}
          className="rounded-lg px-2.5 py-1.5 text-xs font-medium transition-colors disabled:opacity-50 bg-destructive text-destructive-foreground hover:bg-destructive/90"
        >
          Удалить
        </button>
      </div>

      <div className="min-h-0 flex-1 overflow-hidden rounded-[14px] border border-input bg-muted/20">
        <CytoscapeComponent
          elements={elements}
          stylesheet={stylesheet}
          layout={buildLayout(nodes.length)}
          style={{ width: "100%", height: "100%" }}
          cy={(cy) => {
            cyRef.current = cy;
          }}
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
