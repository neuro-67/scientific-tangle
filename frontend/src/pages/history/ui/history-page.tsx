import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { toast } from "sonner";

import { deleteAnswer, queryApi } from "@/entities/query";
import { ROUTES } from "@/shared/constants";
import { handleApiError } from "@/shared/lib/api-error";
import { Skeleton } from "@/shared/ui";

function formatDate(iso: string) {
  const d = new Date(iso);
  return d.toLocaleDateString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** Query history screen — loaded from the backend /answers endpoint. */
export function HistoryPage() {
  const queryClient = useQueryClient();
  const answersQuery = useQuery(queryApi.queries.answersList({ limit: 100 }));

  const deleteMutation = useMutation({
    mutationFn: deleteAnswer,
    onSuccess: () => {
      // Invalidate the list — the detail cache for this id is intentionally
      // left; if the user re-opens it they'll see a 404 and can navigate away.
      queryClient.invalidateQueries({ queryKey: queryApi.queries.all() });
      toast.success("Запрос удалён");
    },
    onError: (error) => {
      handleApiError(error, { fallback: "Не удалось удалить запрос" });
    },
  });

  const items = answersQuery.data ?? [];

  return (
    <div className="mx-auto flex w-full max-w-[1200px] flex-col gap-6">
      <div>
        <h1 className="text-[34px] font-bold leading-tight text-foreground">
          История запросов
        </h1>
        <p className="mt-1 text-base text-description">
          Все сохранённые ответы из базы
        </p>
      </div>

      {answersQuery.isPending ? (
        <div className="grid grid-cols-1 gap-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-[92px] w-full rounded-2xl" />
          ))}
        </div>
      ) : answersQuery.isError ? (
        <div className="rounded-2xl border border-input bg-card p-6 text-sm text-destructive">
          {handleApiError(answersQuery.error, {
            fallback: "Не удалось загрузить историю",
            showToast: false,
          })}
        </div>
      ) : items.length === 0 ? (
        <div className="flex flex-col items-center gap-4 rounded-2xl border border-input bg-card p-10 text-center">
          <span className="text-description">История запросов пуста.</span>
          <Link
            to={ROUTES.search}
            className="text-sm font-medium text-primary hover:underline"
          >
            Перейти к поиску
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {items.map((item) => (
            <div
              key={item.id}
              className="flex items-start justify-between gap-4 rounded-2xl border border-input bg-card p-5"
            >
              <div className="flex flex-col gap-1">
                <Link
                  to={`${ROUTES.answer}?id=${item.id}`}
                  className="text-[17px] font-semibold text-foreground hover:text-primary"
                >
                  {item.question}
                </Link>
                <span className="text-xs text-description">
                  {formatDate(item.created_at)}
                  {item.confidence ? ` · ${item.confidence}` : ""}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => deleteMutation.mutate(item.id)}
                  disabled={deleteMutation.isPending}
                  title="Удалить"
                  className="flex h-9 w-9 items-center justify-center rounded-xl border border-input bg-card text-muted-foreground transition-colors hover:bg-destructive hover:text-destructive-foreground disabled:opacity-50"
                >
                  ×
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
