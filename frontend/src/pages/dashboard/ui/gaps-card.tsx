import type { KnowledgeGap } from "@/entities/dashboard";
import { Badge } from "@/shared/ui";

import { DashboardSection } from "./dashboard-section";
import { EmptyState } from "./empty-state";

type Props = {
  items: KnowledgeGap[];
};

export function GapsCard({ items }: Props) {
  return (
    <DashboardSection
      title="Неисследованные комбинации"
      description="Material × Process × Condition без связанного эксперимента в графе."
    >
      {items.length === 0 ? (
        <EmptyState text="Пробелы по комбинациям не найдены." />
      ) : (
        <div className="flex max-h-[420px] flex-col gap-3 overflow-y-auto pr-1">
          {items.map((item, index) => (
            <div
              key={`${item.material}-${item.process}-${item.condition}-${index}`}
              className="rounded-2xl border border-input bg-background/50 p-4"
            >
              <div className="mb-3 flex items-center justify-between gap-2">
                <Badge variant="gap">нет эксперимента</Badge>
                <span className="text-xs text-description">#{index + 1}</span>
              </div>
              <div className="flex flex-wrap items-center gap-2 text-sm text-main">
                <span className="rounded-xl bg-muted px-3 py-1.5">
                  {item.material}
                </span>
                <span className="text-description">→</span>
                <span className="rounded-xl bg-muted px-3 py-1.5">
                  {item.process}
                </span>
                <span className="text-description">→</span>
                <span className="rounded-xl bg-muted px-3 py-1.5">
                  {item.condition}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </DashboardSection>
  );
}
