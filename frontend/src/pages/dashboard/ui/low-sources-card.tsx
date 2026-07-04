import type { LowSourceEntity } from "@/entities/dashboard";
import { Badge } from "@/shared/ui";

import { DashboardSection } from "./dashboard-section";
import { EmptyState } from "./empty-state";

type Props = {
  items: LowSourceEntity[];
};

const sourceText = (count: number) => {
  if (count === 0) return "нет источников";
  if (count === 1) return "1 источник";
  return `${count} источника`;
};

export function LowSourcesCard({ items }: Props) {
  return (
    <DashboardSection
      title="Темы с малым числом источников"
      description="Сущности, по которым нет источников или найден только один источник."
    >
      {items.length === 0 ? (
        <EmptyState text="Слабоподтверждённые темы не найдены." />
      ) : (
        <div className="flex max-h-[420px] flex-col gap-2 overflow-y-auto pr-1">
          {items.map((item) => (
            <div
              key={`${item.type}-${item.entity}-${item.source_count}`}
              className="flex items-center justify-between gap-3 rounded-2xl border border-input bg-background/50 p-3"
            >
              <div className="flex min-w-0 flex-col gap-1">
                <span className="truncate text-sm font-medium text-foreground">
                  {item.entity}
                </span>
                <span className="text-xs text-description">{item.type}</span>
              </div>
              <Badge variant={item.source_count === 0 ? "confidenceLow" : "gap"}>
                {sourceText(item.source_count)}
              </Badge>
            </div>
          ))}
        </div>
      )}
    </DashboardSection>
  );
}
