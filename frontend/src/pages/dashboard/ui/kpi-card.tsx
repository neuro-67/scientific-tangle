import type { DashboardKpi } from "../lib/dashboard-metrics";

type Props = {
  item: DashboardKpi;
};

export function KpiCard({ item }: Props) {
  return (
    <div className="rounded-[20px] border border-input bg-card p-5">
      <div className="flex items-start justify-between gap-4">
        <div className="flex flex-col gap-1">
          <span className="text-sm font-medium text-description">
            {item.title}
          </span>
          <span className="text-[34px] font-bold leading-none text-foreground">
            {item.value}
          </span>
        </div>
        <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-muted">
          <img src={item.icon} alt="" className="h-5 w-5 object-contain" />
        </div>
      </div>
      <p className="mt-3 text-sm text-main">{item.description}</p>
    </div>
  );
}
