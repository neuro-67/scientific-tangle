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
import {
  createAnswerEdge,
  createAnswerNode,
  deleteAnswerEdge,
  deleteAnswerNode,
  updateAnswerEdge,
  updateAnswerNode,
  type AnswerSubgraph,
  type GraphEdge,
  type GraphNode,
} from "@/entities/query";
import { handleApiError } from "@/shared/lib/api-error";
import { Badge } from "@/shared/ui";

import { canShowFactHistory } from "../lib/fact-history";
import { NODE_TYPES, buildSubgraphStylesheet } from "../lib/subgraph-style";
import { FactHistoryPanel } from "./fact-history-panel";
import { GraphElementModal, type NodeDraft, type EdgeDraft } from "./graph-element-modal";

type Props = {
  subgraph: AnswerSubgraph;
  /**
   * If set, mutations are routed through /answers/{answerId}/... so the
   * change is written to Neo4j AND mirrored on the stored answer snapshot.
   * Absent only for the brief window between /query/ask returning and the
   * answer row being persisted — we fall back to /graph/* in that case.
   */
  answerId: string | null;
};

type Mode = "select" | "addNode" | "addComment" | "addEdge";

const NODE_TYPE_OPTIONS = ["Material", "Process", "Equipment", "Result"] as const;

const EDGE_TYPE_OPTIONS: { value: string; label: string }[] = [
  { value: "RELATED_TO", label: "Связано с" },
  { value: "DEPENDS_ON", label: "Зависит от" },
  { value: "PART_OF", label: "Часть" },
  { value: "RESULTS_IN", label: "Приводит к" },
  { value: "USES", label: "Использует" },
  { value: "CONTRADICTS", label: "Противоречит" },
];

const DEFAULT_EDGE_TYPE = EDGE_TYPE_OPTIONS[0].value;

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

let __tempSeq = 0;
const tempId = (prefix: string) => `__tmp_${prefix}_${++__tempSeq}`;

// Comments have no dedicated `created_at` field in Neo4j, so we embed the date
// straight in the label — the graph shows it as part of the sticky note.
function stampComment(text: string): string {
  const today = new Date().toISOString().slice(0, 10);
  return `[${today}] ${text}`.trim();
}

export function SubgraphView({ subgraph, answerId }: Props) {
  const [nodes, setNodes] = useState<GraphNode[]>(subgraph.nodes);
  const [edges, setEdges] = useState<GraphEdge[]>(subgraph.edges);
  const [mode, setMode] = useState<Mode>("select");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);

  // Modal state for creating/editing nodes and edges. `null` = closed.
  const [nodeModal, setNodeModal] = useState<
    | {
        mode: "create";
        kind: "node" | "comment";
        position: cytoscape.Position;
      }
    | {
        mode: "edit";
        node: GraphNode;
      }
    | null
  >(null);
  const [edgeModal, setEdgeModal] = useState<
    | { mode: "create"; source: string; target: string }
    | { mode: "edit"; edge: GraphEdge }
    | null
  >(null);
  const [edgeSource, setEdgeSource] = useState<string | null>(null);

  const cyRef = useRef<cytoscape.Core | null>(null);
  const positionsRef = useRef<Record<string, cytoscape.Position>>({});

  useEffect(() => {
    setNodes(subgraph.nodes);
    setEdges(subgraph.edges);
    positionsRef.current = {};
    setSelectedId(null);
    setEdgeSource(null);
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
          label: n.revision_count ? `${n.label}\n↺ ${n.revision_count}` : n.label,
          type: n.type,
          revisionCount: n.revision_count ?? 0,
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

  const persistCreateNode = useCallback(
    (body: { type: string; label: string }) =>
      answerId ? createAnswerNode(answerId, body) : createGraphNode(body),
    [answerId]
  );
  const persistUpdateNode = useCallback(
    (id: string, body: { label: string }) =>
      answerId ? updateAnswerNode(answerId, id, body) : updateGraphNode(id, body),
    [answerId]
  );
  const persistDeleteNode = useCallback(
    (id: string) =>
      answerId ? deleteAnswerNode(answerId, id) : deleteGraphNode(id),
    [answerId]
  );
  const persistCreateEdge = useCallback(
    (body: { source: string; target: string; type: string; label?: string }) =>
      answerId ? createAnswerEdge(answerId, body) : createGraphEdge(body),
    [answerId]
  );
  const persistUpdateEdge = useCallback(
    (id: string, body: { label: string }) =>
      answerId ? updateAnswerEdge(answerId, id, body) : updateGraphEdge(id, body),
    [answerId]
  );
  const persistDeleteEdge = useCallback(
    (id: string) =>
      answerId ? deleteAnswerEdge(answerId, id) : deleteGraphEdge(id),
    [answerId]
  );

  const addNode = useCallback(
    async (position: cytoscape.Position, draft: NodeDraft, isComment: boolean) => {
      const label = isComment ? stampComment(draft.label) : draft.label;
      const type = isComment ? "Comment" : draft.type;
      const localId = tempId(isComment ? "c" : "n");
      positionsRef.current[localId] = position;
      setNodes((prev) => [...prev, { id: localId, label, type }]);
      markSelected(localId);
      try {
        const created = await persistCreateNode({ type, label });
        positionsRef.current[created.id] = positionsRef.current[localId];
        delete positionsRef.current[localId];
        setNodes((prev) => prev.map((n) => (n.id === localId ? created : n)));
        markSelected(created.id);
      } catch (err) {
        setNodes((prev) => prev.filter((n) => n.id !== localId));
        delete positionsRef.current[localId];
        handleApiError(err, { fallback: "Не удалось создать узел" });
      }
    },
    [markSelected, persistCreateNode]
  );

  const updateNode = useCallback(
    async (id: string, label: string) => {
      const prev = nodes.find((n) => n.id === id);
      const prevLabel = prev?.label;
      setNodes((current) =>
        current.map((n) => (n.id === id ? { ...n, label } : n))
      );
      if (id.startsWith("__tmp_")) return;
      try {
        await persistUpdateNode(id, { label });
      } catch (err) {
        setNodes((current) =>
          current.map((n) => (n.id === id ? { ...n, label: prevLabel ?? "" } : n))
        );
        handleApiError(err, { fallback: "Не удалось обновить узел" });
      }
    },
    [nodes, persistUpdateNode]
  );

  const addEdge = useCallback(
    async (draft: EdgeDraft, source: string, target: string) => {
      const localId = tempId("e");
      const optimistic: GraphEdge = {
        id: localId,
        source,
        target,
        type: draft.type,
        label: draft.label || undefined,
      };
      setEdges((prev) => [...prev, optimistic]);
      markSelected(localId);
      try {
        const created = await persistCreateEdge({
          source,
          target,
          type: draft.type,
          label: draft.label || undefined,
        });
        const createdEdge: GraphEdge = {
          ...created,
          label: created.label ?? undefined,
        };
        setEdges((prev) =>
          prev.map((e) => (e.id === localId ? createdEdge : e))
        );
        markSelected(created.id);
      } catch (err) {
        setEdges((prev) => prev.filter((e) => e.id !== localId));
        handleApiError(err, { fallback: "Не удалось создать связь" });
      }
    },
    [markSelected, persistCreateEdge]
  );

  const updateEdge = useCallback(
    async (id: string, label: string) => {
      const prevLabel = edges.find((e) => e.id === id)?.label;
      setEdges((prev) =>
        prev.map((e) => (e.id === id ? { ...e, label } : e))
      );
      if (id.startsWith("__tmp_")) return;
      try {
        await persistUpdateEdge(id, { label });
      } catch (err) {
        setEdges((prev) =>
          prev.map((e) => (e.id === id ? { ...e, label: prevLabel } : e))
        );
        handleApiError(err, { fallback: "Не удалось обновить связь" });
      }
    },
    [edges, persistUpdateEdge]
  );

  const removeSelected = useCallback(async () => {
    if (!selectedId) return;
    const isNode = nodes.some((n) => n.id === selectedId);
    const isEdge = !isNode && edges.some((e) => e.id === selectedId);

    const prevNodes = nodes;
    const prevEdges = edges;

    if (isNode) {
      setNodes((prev) => prev.filter((n) => n.id !== selectedId));
      setEdges((prev) =>
        prev.filter(
          (e) => e.source !== selectedId && e.target !== selectedId
        )
      );
    } else if (isEdge) {
      setEdges((prev) => prev.filter((e) => e.id !== selectedId));
    }
    setSelectedId(null);

    if (selectedId.startsWith("__tmp_")) return;

    try {
      if (isNode) await persistDeleteNode(selectedId);
      else if (isEdge) await persistDeleteEdge(selectedId);
      toast.success("Удалено");
    } catch (err) {
      setNodes(prevNodes);
      setEdges(prevEdges);
      handleApiError(err, { fallback: "Не удалось удалить" });
    }
  }, [selectedId, nodes, edges, persistDeleteNode, persistDeleteEdge]);

  const openEditModal = useCallback(() => {
    if (selectedNode) setNodeModal({ mode: "edit", node: selectedNode });
    else if (selectedEdge) setEdgeModal({ mode: "edit", edge: selectedEdge });
  }, [selectedNode, selectedEdge]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
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
      if (mode === "addEdge") {
        if (!edgeSource) {
          setEdgeSource(id);
          markSelected(id);
          return;
        }
        if (edgeSource === id) {
          // Same node clicked twice — cancel edge start silently.
          setEdgeSource(null);
          clearSelection();
          return;
        }
        setEdgeModal({ mode: "create", source: edgeSource, target: id });
        setEdgeSource(null);
        return;
      }
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
      openEditModal();
    };

    const handleTapBg = (evt: cytoscape.EventObject) => {
      if (evt.target !== cy) return;
      if (mode === "addNode") {
        setNodeModal({ mode: "create", kind: "node", position: evt.position });
      } else if (mode === "addComment") {
        setNodeModal({
          mode: "create",
          kind: "comment",
          position: evt.position,
        });
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
  }, [mode, edgeSource, markSelected, clearSelection, openEditModal]);

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

  const containerClass = isFullscreen
    ? "fixed inset-0 z-50 flex h-screen w-screen flex-col gap-2 bg-background p-4"
    : "flex h-full flex-col gap-2";

  return (
    <div className={containerClass}>
      <div className="flex flex-wrap items-center gap-2">
        {toolbarButton("select", "Выбрать", "Выделить элемент")}
        {toolbarButton("addNode", "+ Узел", "Добавить узел — кликни в свободное место")}
        {toolbarButton("addComment", "+ Коммент", "Добавить комментарий с датой")}
        {toolbarButton(
          "addEdge",
          edgeSource ? "→ Выбери цель" : "+ Связь",
          "Создать связь: клик по источнику, затем по цели"
        )}
        <button
          type="button"
          disabled={!selectedId}
          onClick={openEditModal}
          className="rounded-lg bg-muted px-2.5 py-1.5 text-xs font-medium text-foreground transition-colors hover:bg-muted/80 disabled:opacity-50"
        >
          Изменить
        </button>
        <button
          type="button"
          disabled={!selectedId}
          onClick={() => void removeSelected()}
          className="rounded-lg bg-destructive px-2.5 py-1.5 text-xs font-medium text-destructive-foreground transition-colors hover:bg-destructive/90 disabled:opacity-50"
        >
          Удалить
        </button>
        <button
          type="button"
          onClick={() => setIsFullscreen((v) => !v)}
          title={isFullscreen ? "Свернуть" : "На весь экран"}
          className="rounded-lg bg-muted px-2.5 py-1.5 text-xs font-medium text-foreground transition-colors hover:bg-muted/80"
        >
          {isFullscreen ? "⤡ Свернуть" : "⛶ На весь экран"}
        </button>
        <span className="ml-auto text-[11px] text-muted-foreground">
          Правки сохраняются в этом ответе и в общем графе
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
        <span className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full border-2 border-gap" />
          есть версии факта
        </span>
      </div>

      {/* Provenance: where the selected fact came from. Shown for ANY node so
          the source is always visible on click (every graph node carries a
          source_document); the version history below appears additionally for
          versioned fact types. */}
      {selectedNode ? (
        <div className="mt-3 rounded-2xl border border-input bg-card p-4">
          <div className="mb-2 flex items-center justify-between gap-2">
            <h3 className="text-sm font-semibold text-foreground">
              Провенанс факта
            </h3>
            <Badge variant="outline">{selectedNode.type}</Badge>
          </div>
          <p className="text-sm font-medium leading-5 text-foreground">
            {selectedNode.label}
          </p>
          <div className="mt-2 flex items-start gap-2 text-xs leading-5 text-description">
            <span className="shrink-0">📄 Источник:</span>
            <span className="font-medium text-main">
              {selectedNode.source_document ?? "не указан"}
            </span>
          </div>
          {selectedNode.revision_count ? (
            <div className="mt-1 text-xs text-description">
              ↺ Версий факта: {selectedNode.revision_count}
            </div>
          ) : null}
        </div>
      ) : (
        <p className="mt-3 rounded-2xl border border-dashed border-input bg-muted/30 p-3 text-center text-xs text-description">
          Нажмите на узел графа, чтобы увидеть его источник (провенанс) и историю
          версий факта.
        </p>
      )}

      {canShowFactHistory(selectedNode) ? (
        <FactHistoryPanel factId={selectedNode.id} factType={selectedNode.type} />
      ) : null}

      {nodeModal ? (
        <GraphElementModal
          kind="node"
          initial={
            nodeModal.mode === "edit"
              ? { type: nodeModal.node.type, label: nodeModal.node.label }
              : nodeModal.kind === "comment"
                ? { type: "Comment", label: "" }
                : { type: NODE_TYPE_OPTIONS[0], label: "" }
          }
          isComment={nodeModal.mode === "create" && nodeModal.kind === "comment"}
          nodeTypeOptions={NODE_TYPE_OPTIONS as unknown as string[]}
          onClose={() => setNodeModal(null)}
          onSubmit={(draft) => {
            if (nodeModal.mode === "edit") {
              void updateNode(nodeModal.node.id, draft.label);
            } else {
              void addNode(
                nodeModal.position,
                draft,
                nodeModal.kind === "comment"
              );
            }
            setNodeModal(null);
          }}
        />
      ) : null}

      {edgeModal ? (
        <GraphElementModal
          kind="edge"
          initial={
            edgeModal.mode === "edit"
              ? {
                  type: edgeModal.edge.type,
                  label: edgeModal.edge.label ?? "",
                }
              : { type: DEFAULT_EDGE_TYPE, label: "" }
          }
          edgeTypeOptions={EDGE_TYPE_OPTIONS}
          disableTypeEdit={edgeModal.mode === "edit"}
          onClose={() => setEdgeModal(null)}
          onSubmit={(draft) => {
            if (edgeModal.mode === "edit") {
              void updateEdge(edgeModal.edge.id, draft.label);
            } else {
              void addEdge(
                draft as EdgeDraft,
                edgeModal.source,
                edgeModal.target
              );
            }
            setEdgeModal(null);
          }}
        />
      ) : null}
    </div>
  );
}
