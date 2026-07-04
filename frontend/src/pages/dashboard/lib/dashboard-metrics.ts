import type { DashboardSummary } from "@/entities/dashboard";

export type DashboardKpi = {
  title: string;
  value: number;
  description: string;
  icon: string;
};

export function buildDashboardKpis(data: DashboardSummary): DashboardKpi[] {
  const totalProcesses = data.coverage_by_domain.reduce(
    (sum, item) => sum + item.n_processes,
    0
  );
  const totalPublications = data.coverage_by_domain.reduce(
    (sum, item) => sum + item.n_publications,
    0
  );
  const riskCount = data.risk_low_sources.length + data.risk_contradictions.length;

  return [
    {
      title: "Направления",
      value: data.coverage_by_domain.length,
      description: "домены с процессами",
      icon: "/assets/icon-overview.png",
    },
    {
      title: "Процессы",
      value: totalProcesses,
      description: `${totalPublications} источников`,
      icon: "/assets/icon-settings.png",
    },
    {
      title: "Пробелы знаний",
      value: data.gaps.length,
      description: "комбинации без эксперимента",
      icon: "/assets/icon-warning.png",
    },
    {
      title: "Зоны риска",
      value: riskCount,
      description: "слабые источники и противоречия",
      icon: "/assets/icon-error.png",
    },
  ];
}

export function maxCoverageProcesses(data: DashboardSummary): number {
  return Math.max(
    1,
    ...data.coverage_by_domain.map((item) => item.n_processes)
  );
}
