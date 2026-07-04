import type { DomainCoverage } from "@/entities/dashboard";
import { Badge } from "@/shared/ui";

import { maxCoverageProcesses } from "../lib/dashboard-metrics";
import { DashboardSection } from "./dashboard-section";
import { EmptyState } from "./empty-state";

type Props = {
  items: DomainCoverage[];
};

export function CoverageCard({ items }: Props) {
  const max = maxCoverageProcesses({
    coverage_by_domain: items,
    gaps: [],
    geography_only_topics: [],
    risk_low_sources: [],
    risk_contradictions: [],
  });

  return (
    <DashboardSection
      title="Покрытие по направлениям"
      description="Сколько технологических процессов и источников уже связано с каждым доменом."
    >
      {items.length === 0 ? (
        <EmptyState text="В графе пока нет процессов с указанным доменом." />
      ) : (
        <div className="flex flex-col gap-4">
          {items.map((item) => {
            const width = Math.max(8, (item.n_processes / max) * 100);
            return (
              <div key={item.domain} className="flex flex-col gap-2">
                <div className="flex items-center justify-between gap-3">
                  <span className="truncate text-sm font-medium text-foreground">
                    {item.domain}
                  </span>
                  <Badge variant="secondary">
                    {item.n_publications} источников
                  </Badge>
                </div>
                <div className="h-3 overflow-hidden rounded-full bg-muted">
                  <div
                    className="h-full rounded-full bg-primary"
                    style={{ width: `${width}%` }}
                  />
                </div>
                <span className="text-xs text-description">
                  {item.n_processes} процессов
                </span>
              </div>
            );
          })}
        </div>
      )}
    </DashboardSection>
  );
}
