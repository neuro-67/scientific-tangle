import type { ContradictionPair } from "@/entities/dashboard";
import { Badge } from "@/shared/ui";

import { DashboardSection } from "./dashboard-section";
import { EmptyState } from "./empty-state";

type Props = {
  items: ContradictionPair[];
};

export function ContradictionsCard({ items }: Props) {
  return (
    <DashboardSection
      title="Противоречивые данные"
      description="Пары узлов графа, связанные отношением CONTRADICTS."
      className="xl:col-span-2"
    >
      {items.length === 0 ? (
        <EmptyState text="Противоречия в текущем графе не найдены." />
      ) : (
        <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
          {items.map((item, index) => (
            <div
              key={`${item.node_a}-${item.node_b}-${index}`}
              className="rounded-2xl border border-input bg-background/50 p-4"
            >
              <div className="mb-3 flex items-center justify-between gap-2">
                <Badge variant="contradiction">противоречие</Badge>
                <span className="text-xs text-description">#{index + 1}</span>
              </div>
              <div className="grid grid-cols-1 gap-3 md:grid-cols-[1fr_auto_1fr] md:items-center">
                <ContradictionNode
                  type={item.type_a}
                  name={item.node_a}
                  source={item.source_a}
                />
                <span className="text-center text-sm font-semibold text-contradiction">
                  ↔
                </span>
                <ContradictionNode
                  type={item.type_b}
                  name={item.node_b}
                  source={item.source_b}
                />
              </div>
            </div>
          ))}
        </div>
      )}
    </DashboardSection>
  );
}

type ContradictionNodeProps = {
  type: string;
  name: string;
  source: string | null;
};

function ContradictionNode({ type, name, source }: ContradictionNodeProps) {
  return (
    <div className="rounded-xl bg-card p-3">
      <Badge variant="outline">{type}</Badge>
      <p className="mt-2 text-sm font-medium leading-5 text-foreground">
        {name}
      </p>
      <p className="mt-2 text-xs text-description">
        Источник: {source ?? "не указан"}
      </p>
    </div>
  );
}
