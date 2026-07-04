import { useQuery } from "@tanstack/react-query";
import { lazy, Suspense, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import {
  addQueryHistory,
  getQueryHistory,
  queryApi,
  requestToFilters,
  searchParamsToRequest,
  toggleQueryHistoryFavorite,
} from "@/entities/query";
import { ROUTES } from "@/shared/constants";
import { handleApiError } from "@/shared/lib/api-error";
import { Badge, Skeleton } from "@/shared/ui";

import { AnswerSkeleton } from "./answer-skeleton";
import { ExportButtons } from "./export-buttons";
import { SourceCard } from "./source-card";

const SubgraphView = lazy(() =>
  import("./subgraph-view").then((m) => ({ default: m.SubgraphView }))
);

/** Answer screen styled to the design reference. */
export function AnswerPage() {
  const [searchParams] = useSearchParams();
  const request = useMemo(
    () => searchParamsToRequest(searchParams),
    [searchParams]
  );

  const answerQuery = useQuery(queryApi.queries.ask(request));
  const data = answerQuery.data;

  const [isFavorite, setIsFavorite] = useState(() => {
    const item = getQueryHistory().find((i) => i.question === request.question);
    return item?.favorite ?? false;
  });

  const toggleFavorite = () => {
    const item = getQueryHistory().find((i) => i.question === request.question);
    if (item) {
      toggleQueryHistoryFavorite(item.id);
      setIsFavorite((v) => !v);
    } else {
      addQueryHistory(request.question, requestToFilters(request), true);
      setIsFavorite(true);
    }
  };

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
            {request.question || "Вопрос не задан"}
          </h1>
        </div>
        <div className="flex items-center gap-2">
          {data ? <ExportButtons question={request.question} answer={data} /> : null}
          <button
            type="button"
            onClick={toggleFavorite}
            className={`flex h-10 w-[120px] items-center justify-center gap-2 rounded-xl border text-sm font-medium transition-colors ${
              isFavorite
                ? "border-yellow-400 bg-yellow-50 text-yellow-600"
                : "border-input bg-card text-main hover:bg-[hsl(var(--save-hover))]"
            }`}
          >
            <img
              src="/assets/icon-star.png"
              alt=""
              className={`h-4 w-4 object-contain ${
                isFavorite ? "" : "brightness-0"
              }`}
            />
            {isFavorite ? "Сохранено" : "Сохранить"}
          </button>
        </div>
      </div>

      {answerQuery.isPending && request.question ? <AnswerSkeleton /> : null}

      {answerQuery.isError ? (
        <div className="rounded-[20px] border border-input bg-card p-6 text-sm text-destructive">
          {handleApiError(answerQuery.error, {
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
