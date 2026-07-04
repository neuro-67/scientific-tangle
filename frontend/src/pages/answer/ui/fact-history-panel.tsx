import { useQuery } from "@tanstack/react-query";

import { factApi, type FactRevision } from "@/entities/fact";
import { handleApiError } from "@/shared/lib/api-error";
import { Badge, Skeleton } from "@/shared/ui";

import {
  formatPropertyValue,
  formatRevisionDate,
  revisionTitle,
} from "../lib/fact-history";

type Props = {
  factId: string;
  factType: string;
};

export function FactHistoryPanel({ factId, factType }: Props) {
  const historyQuery = useQuery(factApi.queries.history({ factId }));

  if (historyQuery.isLoading) {
    return (
      <div className="mt-3 rounded-2xl border border-input bg-card p-4">
        <div className="mb-3 flex items-center justify-between gap-2">
          <Skeleton className="h-4 w-40" />
          <Skeleton className="h-5 w-16" />
        </div>
        <Skeleton className="h-16 w-full rounded-xl" />
      </div>
    );
  }

  if (historyQuery.isError) {
    return (
      <div className="mt-3 rounded-2xl border border-input bg-card p-4 text-xs text-destructive">
        {handleApiError(historyQuery.error, {
          fallback: "Не удалось загрузить версии факта",
          showToast: false,
        })}
      </div>
    );
  }

  const revisions = historyQuery.data ?? [];

  return (
    <div className="mt-3 rounded-2xl border border-input bg-card p-4">
      <div className="mb-3 flex items-center justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-foreground">
            Версии факта
          </h3>
          <p className="text-xs text-description">
            История прошлых значений для {factType}
          </p>
        </div>
        <Badge variant={revisions.length > 0 ? "gap" : "secondary"}>
          {revisions.length}
        </Badge>
      </div>

      {revisions.length === 0 ? (
        <p className="rounded-xl bg-muted/60 p-3 text-xs leading-5 text-description">
          Предыдущих версий нет. Они появятся после повторного импорта, если у
          Measurement изменятся value/min/max/unit/operator или у Finding —
          confidence.
        </p>
      ) : (
        <div className="flex max-h-[260px] flex-col gap-3 overflow-y-auto pr-1">
          {revisions.map((revision, index) => (
            <RevisionCard
              key={`${revision.superseded_at}-${index}`}
              revision={revision}
              index={index}
            />
          ))}
        </div>
      )}
    </div>
  );
}

type RevisionCardProps = {
  revision: FactRevision;
  index: number;
};

function RevisionCard({ revision, index }: RevisionCardProps) {
  const entries = Object.entries(revision.previous_properties).filter(
    ([key]) => !["id", "name", "description"].includes(key)
  );

  return (
    <div className="rounded-xl border border-input bg-background/50 p-3">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <div className="flex min-w-0 flex-col">
          <span className="truncate text-sm font-medium text-foreground">
            {revisionTitle(revision)}
          </span>
          <span className="text-xs text-description">
            superseded: {formatRevisionDate(revision.superseded_at)}
          </span>
        </div>
        <Badge variant="outline">v-{index + 1}</Badge>
      </div>

      {revision.superseded_by_document ? (
        <p className="mb-2 truncate text-xs text-description">
          Новый источник: {revision.superseded_by_document}
        </p>
      ) : null}

      <div className="grid grid-cols-1 gap-1.5 sm:grid-cols-2">
        {entries.slice(0, 8).map(([key, value]) => (
          <div key={key} className="rounded-lg bg-card px-2 py-1.5">
            <span className="block text-[11px] text-description">{key}</span>
            <span className="block truncate text-xs font-medium text-main">
              {formatPropertyValue(value)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
