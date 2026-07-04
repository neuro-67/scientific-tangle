import { useQuery } from "@tanstack/react-query";

import { dashboardApi } from "@/entities/dashboard";
import { handleApiError } from "@/shared/lib/api-error";
import { Skeleton } from "@/shared/ui";

import { buildDashboardKpis } from "../lib/dashboard-metrics";
import { ContradictionsCard } from "./contradictions-card";
import { CoverageCard } from "./coverage-card";
import { GapsCard } from "./gaps-card";
import { GeographyCard } from "./geography-card";
import { KpiCard } from "./kpi-card";
import { LowSourcesCard } from "./low-sources-card";

/** Management dashboard: knowledge coverage, gaps and risk zones. */
export function DashboardPage() {
  const summaryQuery = useQuery(dashboardApi.queries.summary());
  const data = summaryQuery.data;

  return (
    <div className="mx-auto flex w-full max-w-[1280px] flex-col gap-6 pb-8">
      <div className="flex flex-col gap-1">
        <h1 className="text-[34px] font-bold leading-tight text-foreground">
          Дашборд знаний
        </h1>
        <p className="max-w-3xl text-base leading-6 text-description">
          Покрытие корпуса, пробелы Material × Process × Condition,
          география практик и зоны риска по данным графа знаний.
        </p>
      </div>

      {summaryQuery.isLoading ? <DashboardSkeleton /> : null}

      {summaryQuery.isError ? (
        <div className="rounded-[20px] border border-input bg-card p-6 text-sm text-destructive">
          {handleApiError(summaryQuery.error, {
            fallback: "Не удалось загрузить дашборд",
            showToast: false,
          })}
        </div>
      ) : null}

      {data ? (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {buildDashboardKpis(data).map((item) => (
              <KpiCard key={item.title} item={item} />
            ))}
          </div>

          <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
            <CoverageCard items={data.coverage_by_domain} />
            <GeographyCard items={data.geography_only_topics} />
            <GapsCard items={data.gaps} />
            <LowSourcesCard items={data.risk_low_sources} />
            <ContradictionsCard items={data.risk_contradictions} />
          </div>
        </>
      ) : null}
    </div>
  );
}

function DashboardSkeleton() {
  return (
    <div className="flex flex-col gap-5">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <Skeleton key={index} className="h-[140px] rounded-[20px]" />
        ))}
      </div>
      <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
        {Array.from({ length: 4 }).map((_, index) => (
          <Skeleton key={index} className="h-[360px] rounded-[20px]" />
        ))}
      </div>
    </div>
  );
}
