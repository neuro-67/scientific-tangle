import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { lazy, Suspense, useMemo } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { toast } from "sonner";

import {
  queryApi,
  regenerateAnswer,
  searchParamsToRequest,
  type AnswerRecord,
  type QueryAnswer,
} from "@/entities/query";
import { toQueryAnswer } from "@/entities/query/api/post-query.helpers";
import { ROUTES } from "@/shared/constants";
import { handleApiError } from "@/shared/lib/api-error";
import { Badge, Skeleton } from "@/shared/ui";

import { AnswerSkeleton } from "./answer-skeleton";
import { ExportButtons } from "./export-buttons";
import { SourceCard } from "./source-card";

const SubgraphView = lazy(() =>
  import("./subgraph-view").then((m) => ({ default: m.SubgraphView }))
);

/**
 * Answer screen supports two modes:
 * - `?question=...&materials=...` (fresh ask): fires POST /query/ask.
 * - `?id=<uuid>` (saved answer): loads the row from GET /answers/{id}.
 */
export function AnswerPage() {
  const [searchParams] = useSearchParams();
  const savedId = searchParams.get("id");
  const request = useMemo(
    () => searchParamsToRequest(searchParams),
    [searchParams]
  );
  const queryClient = useQueryClient();

  // Only one of these two queries actually runs (see `enabled`).
  const freshAsk = useQuery({
    ...queryApi.queries.ask(request),
    enabled: !savedId && request.question.trim().length > 0,
  });
  const savedAnswer = useQuery({
    ...queryApi.queries.answerDetail(savedId),
    enabled: Boolean(savedId),
  });

  const activeQuery = savedId ? savedAnswer : freshAsk;
  const data: QueryAnswer | undefined = useMemo(() => {
    if (savedId) {
      const rec = savedAnswer.data as AnswerRecord | undefined;
      if (!rec) return undefined;
      // Reconstruct the QueryAnswer shape from the saved envelope.
      return toQueryAnswer({
        id: rec.id,
        question: rec.question,
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        query_spec: (rec.query_spec as any) ?? {},
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        synthesis: (rec.synthesis as any) ?? { answer: "" },
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        subgraph: (rec.subgraph as any) ?? null,
      });
    }
    return freshAsk.data;
  }, [savedId, savedAnswer.data, freshAsk.data]);

  const question = savedId
    ? (savedAnswer.data?.question ?? request.question)
    : request.question;
  const currentAnswerId = data?.id ?? savedId ?? undefined;

  const regenerateMutation = useMutation({
    mutationFn: regenerateAnswer,
    onSuccess: (fresh) => {
      queryClient.invalidateQueries({ queryKey: queryApi.queries.all() });
      toast.success("Отчёт перегенерирован");
      // Push the fresh data into the detail cache so the UI updates immediately.
      if (fresh.id) {
        queryClient.setQueryData(
          queryApi.queries.answerDetail(fresh.id).queryKey,
          {
            id: fresh.id,
            question,
            query_spec: fresh.spec,
            synthesis: {
              answer: fresh.answer,
              consensus: fresh.consensus,
              disagreements: fresh.disagreements,
              sources: fresh.sources,
              gaps: fresh.gaps,
              experts: fresh.experts,
              laboratories: fresh.laboratories,
              confidence: fresh.confidence,
            },
            subgraph: fresh.subgraph,
            confidence: fresh.confidence,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          } satisfies AnswerRecord
        );
      }
    },
    onError: (error) => {
      handleApiError(error, { fallback: "Не удалось перегенерировать отчёт" });
    },
  });

  return (
    <div className="flex max-w-[1280px] flex-col gap-4 pb-8">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex flex-col gap-1">
          <Link
            to={ROUTES.search}
            className="flex items-center text-[14px] text-[hsl(var(--answer-back))] transition-colors hover:text-foreground"
          >
            <img
              src="/assets/icon-arrow.png"
              alt=""
              className="mr-2 h-4 w-4 rotate-180 object-contain"
            />
            Новый поиск
          </Link>
          <h1 className="text-[30px] font-bold leading-tight text-foreground">
            {question || "Вопрос не задан"}
          </h1>
        </div>
        <div className="flex items-center gap-2">
          {data ? <ExportButtons question={question} answer={data} /> : null}
          {currentAnswerId ? (
            <button
              type="button"
              onClick={() => regenerateMutation.mutate(currentAnswerId)}
              disabled={regenerateMutation.isPending}
              title="Перегенерировать отчёт — заново прогонит вопрос через пайплайн и обновит запись в БД"
              className="flex h-10 items-center justify-center gap-2 rounded-xl border border-input bg-card px-3 text-sm font-medium text-main transition-colors hover:bg-[hsl(var(--save-hover))] disabled:opacity-50"
            >
              {regenerateMutation.isPending ? "Генерация…" : "↻ Перегенерировать"}
            </button>
          ) : null}
        </div>
      </div>

      {activeQuery.isPending && (savedId || question) ? (
        <AnswerSkeleton />
      ) : null}

      {activeQuery.isError ? (
        <div className="rounded-[20px] border border-input bg-card p-6 text-sm text-destructive">
          {handleApiError(activeQuery.error, {
            fallback: "Не удалось получить ответ",
            showToast: false,
          })}
        </div>
      ) : null}

      {data ? (
        <div className="flex flex-col gap-5">
          {/* Answer card */}
          <section className="rounded-[20px] border border-input bg-card p-5">
            <span className="text-[17px] font-semibold text-foreground">
              Ответ
            </span>
            <p className="mt-3 text-[15px] leading-6 text-main">
              {data.answer}
            </p>
          </section>

          {/* Graph + analytics */}
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-[1fr_200px] lg:grid-rows-[560px_auto]">
            <div className="flex min-h-0 flex-col gap-4">
              {/* Graph */}
              <section className="flex h-[560px] flex-col rounded-[20px] border border-input bg-card p-5">
                <span className="mb-3 text-[17px] font-semibold text-foreground">
                  Граф знаний
                </span>
                <div className="min-h-0 flex-1">
                  <Suspense fallback={<Skeleton className="h-full w-full" />}>
                    <SubgraphView subgraph={data.subgraph} />
                  </Suspense>
                </div>
              </section>

              {/* Sources */}
              <section className="rounded-[20px] border border-input bg-card p-5">
                <div className="mb-3 flex items-center justify-between">
                  <span className="text-[17px] font-semibold text-foreground">
                    Источники
                  </span>
                  <button className="text-sm text-primary hover:underline">
                    Показать все
                  </button>
                </div>
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                  {data.sources.map((source, i) => (
                    <SourceCard key={`${source.title}-${i}`} source={source} />
                  ))}
                </div>
              </section>
            </div>

            {/* Analytics */}
            <aside className="row-span-2 flex h-full min-h-0 flex-col gap-3 overflow-y-auto">
              <AnalyticsCard
                title="Консенсус"
                dotColor="bg-[#22C55E]"
                items={data.consensus}
                emptyText="Нет данных"
              />
              <AnalyticsCard
                title="Противоречия"
                dotColor="bg-[#EC4899]"
                badge={data.disagreements.length}
                items={data.disagreements.map(
                  (d) =>
                    `${d.point}: ${d.sources_a.join(", ")} ↔ ${d.sources_b.join(", ")}`
                )}
                emptyText="Нет противоречий"
              />
              <AnalyticsCard
                title="Пробелы"
                dotColor="bg-[#F59E0B]"
                items={data.gaps}
                emptyText="Нет данных"
              />
              <AnalyticsCard
                title="Эксперты"
                dotColor="bg-[#4F46E5]"
                items={data.experts.map((e) => `${e.name} — ${e.affiliation}`)}
                emptyText="Нет данных"
              />
              <AnalyticsCard
                title="Лаборатории"
                dotColor="bg-[#0EA5E9]"
                items={data.laboratories.map(
                  (l) => `${l.name} — ${l.institution}`
                )}
                emptyText="Нет данных"
              />
            </aside>
          </div>
        </div>
      ) : null}
    </div>
  );
}

type AnalyticsCardProps = {
  title: string;
  dotColor: string;
  badge?: number;
  items: string[];
  emptyText: string;
};

function AnalyticsCard({
  title,
  dotColor,
  badge,
  items,
  emptyText,
}: AnalyticsCardProps) {
  return (
    <div className="rounded-[16px] bg-card p-4">
      <div className="mb-2 flex items-center gap-2 text-[15px] font-semibold text-foreground">
        <span className={`h-2 w-2 rounded-full ${dotColor}`} />
        {title}
        {badge ? (
          <Badge
            variant="confidenceLow"
            className="rounded-full px-2 py-0 text-[10px]"
          >
            {badge}
          </Badge>
        ) : null}
      </div>
      <div className="flex flex-col gap-1.5 text-[13px] leading-5 text-main">
        {items.length > 0 ? (
          items.map((item) => <span key={item}>— {item}</span>)
        ) : (
          <span className="text-description">{emptyText}</span>
        )}
      </div>
    </div>
  );
}
