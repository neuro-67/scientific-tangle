import type { GeographyOnlyTopic } from "@/entities/dashboard";
import { Badge } from "@/shared/ui";

import { DashboardSection } from "./dashboard-section";
import { EmptyState } from "./empty-state";

type Props = {
  items: GeographyOnlyTopic[];
};

const geographyLabel = (value: string) => {
  if (value === "RU") return "только отечественная";
  if (value === "foreign") return "только зарубежная";
  return value;
};

export function GeographyCard({ items }: Props) {
  const ru = items.filter((item) => item.only_geography === "RU");
  const foreign = items.filter((item) => item.only_geography === "foreign");
  const other = items.filter(
    (item) => item.only_geography !== "RU" && item.only_geography !== "foreign"
  );

  return (
    <DashboardSection
      title="География практик"
      description="Темы, материалы и процессы, найденные только в одной географической группе источников."
    >
      {items.length === 0 ? (
        <EmptyState text="Нет тем с односторонним географическим покрытием." />
      ) : (
        <div className="grid grid-cols-1 gap-3 xl:grid-cols-2">
          <GeographyColumn title="Отечественная практика" items={ru} />
          <GeographyColumn title="Зарубежная практика" items={foreign} />
          {other.length > 0 ? (
            <GeographyColumn title="Другая география" items={other} />
          ) : null}
        </div>
      )}
    </DashboardSection>
  );
}

type GeographyColumnProps = {
  title: string;
  items: GeographyOnlyTopic[];
};

function GeographyColumn({ title, items }: GeographyColumnProps) {
  return (
    <div className="rounded-2xl bg-background/50 p-4">
      <h3 className="mb-3 text-sm font-semibold text-foreground">{title}</h3>
      {items.length === 0 ? (
        <span className="text-sm text-description">Нет данных</span>
      ) : (
        <div className="flex max-h-[260px] flex-col gap-2 overflow-y-auto pr-1">
          {items.map((item) => (
            <div
              key={`${item.type}-${item.entity}-${item.only_geography}`}
              className="flex flex-col gap-1 rounded-xl border border-input bg-card p-3"
            >
              <span className="text-sm font-medium text-foreground">
                {item.entity}
              </span>
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="outline">{item.type}</Badge>
                <span className="text-xs text-description">
                  {geographyLabel(item.only_geography)}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
