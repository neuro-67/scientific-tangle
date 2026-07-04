import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { documentApi, type Document } from "@/entities/document";
import { handleApiError } from "@/shared/lib/api-error";

import { formatBytes, isTerminal } from "../lib/format";
import { StatusBadge } from "./status-badge";

type Props = {
  /** Freshly uploaded document; seeds the cache and is polled for status. */
  document: Document;
};

/** How often to re-check ingestion status while a document is not terminal. */
const POLL_MS = 2000;

/** A single uploaded document with live-polling ingestion status. */
export function DocumentRow({ document }: Props) {
  const queryClient = useQueryClient();

  const query = useQuery({
    ...documentApi.queries.detail(document.id),
    initialData: document,
    refetchInterval: (q) => {
      const status = q.state.data?.status;
      return status && isTerminal(status) ? false : POLL_MS;
    },
  });

  const doc = query.data ?? document;

  const deleteMutation = useMutation({
    mutationFn: documentApi.deleteDocument,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: documentApi.queries.all() });
      toast.success(`«${doc.filename}» удалён`);
    },
    onError: (error) => {
      handleApiError(error, { fallback: "Не удалось удалить документ" });
    },
  });

  const handleDelete = () => {
    // Cascade removes graph nodes + vector chunks + blob — worth confirming.
    const ok = window.confirm(
      `Удалить «${doc.filename}»?\n\nБудут удалены: файл в хранилище, узлы графа с source_document=${doc.filename}, векторные чанки в Qdrant. Отменить нельзя.`
    );
    if (!ok) return;
    deleteMutation.mutate({ id: doc.id });
  };

  return (
    <div className="flex items-start justify-between gap-4 rounded-2xl border border-input bg-card p-5">
      <div className="flex min-w-0 items-start gap-3">
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-accent">
          <img
            src="/assets/icon-document.png"
            alt=""
            className="h-5 w-5 object-contain"
          />
        </span>
        <div className="flex min-w-0 flex-col gap-1">
          <span className="truncate text-[15px] font-semibold text-foreground">
            {doc.filename}
          </span>
          <span className="text-xs text-description">
            {formatBytes(doc.size)}
          </span>
          {doc.status === "failed" && doc.error ? (
            <span className="mt-1 text-xs text-[hsl(var(--confidence-low))]">
              {doc.error}
            </span>
          ) : null}
        </div>
      </div>
      <div className="flex items-center gap-3">
        <StatusBadge status={doc.status} />
        <button
          type="button"
          onClick={handleDelete}
          disabled={deleteMutation.isPending}
          title="Удалить документ вместе с извлечёнными узлами графа и векторами"
          className="rounded-lg border border-input bg-card px-2.5 py-1.5 text-xs font-medium text-destructive transition-colors hover:bg-destructive/10 disabled:opacity-50"
        >
          {deleteMutation.isPending ? "…" : "Удалить"}
        </button>
      </div>
    </div>
  );
}
