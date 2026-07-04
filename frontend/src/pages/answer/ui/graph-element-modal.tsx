import { useEffect, useRef, useState } from "react";

export type NodeDraft = { type: string; label: string };
export type EdgeDraft = { type: string; label: string };

type NodeProps = {
  kind: "node";
  initial: NodeDraft;
  isComment?: boolean;
  nodeTypeOptions: string[];
  onSubmit: (draft: NodeDraft) => void;
  onClose: () => void;
};

type EdgeProps = {
  kind: "edge";
  initial: EdgeDraft;
  edgeTypeOptions: { value: string; label: string }[];
  disableTypeEdit?: boolean;
  onSubmit: (draft: EdgeDraft) => void;
  onClose: () => void;
};

type Props = NodeProps | EdgeProps;

/**
 * Inline modal for creating/editing a graph node or edge. Replaces the
 * previous `window.prompt` chain — gives us proper type dropdowns, keyboard
 * ergonomics (Enter to submit, Esc to close), and a place to surface the
 * auto-stamped date for comments.
 */
export function GraphElementModal(props: Props) {
  const [type, setType] = useState(props.initial.type);
  const [label, setLabel] = useState(props.initial.label);
  const inputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    inputRef.current?.focus();
    inputRef.current?.select();
  }, []);

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") props.onClose();
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [props]);

  const submit = () => {
    const trimmed = label.trim();
    if (!trimmed) return;
    props.onSubmit({ type, label: trimmed });
  };

  const title =
    props.kind === "node"
      ? props.isComment
        ? "Комментарий"
        : "Узел"
      : "Связь";

  const isEdge = props.kind === "edge";
  const disableType = isEdge && props.disableTypeEdit;

  return (
    <div
      className="fixed inset-0 z-[60] flex items-center justify-center bg-black/40 p-4"
      onClick={(e) => {
        if (e.target === e.currentTarget) props.onClose();
      }}
    >
      <div className="w-full max-w-md rounded-2xl border border-input bg-card p-5 shadow-xl">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-[17px] font-semibold text-foreground">{title}</h2>
          <button
            type="button"
            onClick={props.onClose}
            className="rounded-md px-2 py-1 text-sm text-muted-foreground hover:bg-muted"
            aria-label="Закрыть"
          >
            ✕
          </button>
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            submit();
          }}
          className="flex flex-col gap-3"
        >
          {props.kind === "node" && !props.isComment ? (
            <label className="flex flex-col gap-1 text-xs">
              <span className="text-muted-foreground">Тип</span>
              <select
                value={type}
                onChange={(e) => setType(e.target.value)}
                className="rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground"
              >
                {props.nodeTypeOptions.map((opt) => (
                  <option key={opt} value={opt}>
                    {opt}
                  </option>
                ))}
              </select>
            </label>
          ) : null}

          {props.kind === "edge" ? (
            <label className="flex flex-col gap-1 text-xs">
              <span className="text-muted-foreground">Тип связи</span>
              <select
                value={type}
                onChange={(e) => setType(e.target.value)}
                disabled={disableType}
                className="rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground disabled:opacity-60"
              >
                {props.edgeTypeOptions.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label} ({opt.value})
                  </option>
                ))}
                {/* If we're editing an edge with a type outside our curated list,
                    keep the current value in the dropdown so it doesn't silently
                    switch on save. */}
                {disableType &&
                !props.edgeTypeOptions.some((o) => o.value === type) ? (
                  <option value={type}>{type}</option>
                ) : null}
              </select>
            </label>
          ) : null}

          <label className="flex flex-col gap-1 text-xs">
            <span className="text-muted-foreground">
              {props.kind === "node"
                ? props.isComment
                  ? "Текст комментария"
                  : "Название узла"
                : "Подпись связи"}
            </span>
            <input
              ref={inputRef}
              type="text"
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              placeholder={
                props.kind === "node"
                  ? props.isComment
                    ? "Ваш комментарий…"
                    : "Название"
                  : "Опционально"
              }
              className="rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground"
            />
            {props.kind === "node" && props.isComment ? (
              <span className="text-[11px] text-muted-foreground">
                Дата ({new Date().toISOString().slice(0, 10)}) будет добавлена
                автоматически.
              </span>
            ) : null}
          </label>

          <div className="mt-2 flex justify-end gap-2">
            <button
              type="button"
              onClick={props.onClose}
              className="rounded-lg bg-muted px-3 py-1.5 text-xs font-medium text-foreground hover:bg-muted/80"
            >
              Отмена
            </button>
            <button
              type="submit"
              disabled={!label.trim()}
              className="rounded-lg bg-primary px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-primary/90 disabled:opacity-50"
            >
              Сохранить
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
