import type { DocumentStatus } from "@/entities/document";
import { Badge } from "@/shared/ui";

import { statusLabel } from "../lib/format";

type Props = {
  status: DocumentStatus;
};

const VARIANT: Record<
  DocumentStatus,
  "outline" | "confidenceHigh" | "confidenceMedium" | "confidenceLow"
> = {
  pending: "outline",
  processing: "confidenceMedium",
  processed: "confidenceHigh",
  failed: "confidenceLow",
};

/** Colored pill reflecting a document's ingestion status. */
export function StatusBadge({ status }: Props) {
  const active = status === "pending" || status === "processing";
  return (
    <Badge variant={VARIANT[status]} className="gap-1.5">
      {active ? (
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-current" />
      ) : null}
      {statusLabel(status)}
    </Badge>
  );
}
