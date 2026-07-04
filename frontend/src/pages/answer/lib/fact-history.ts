import type { FactRevision } from "@/entities/fact";
import type { GraphNode } from "@/entities/query";

import { FACT_VERSIONED_TYPES } from "./fact-history.constants";

export function canShowFactHistory(node: GraphNode | null): node is GraphNode {
  return Boolean(node && FACT_VERSIONED_TYPES.includes(node.type as never));
}

export function formatRevisionDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;

  return new Intl.DateTimeFormat("ru-RU", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

export function formatPropertyValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return JSON.stringify(value);
}

export function revisionTitle(revision: FactRevision): string {
  const props = revision.previous_properties;
  const value = props.value ?? props.confidence ?? props.description ?? props.id;
  return formatPropertyValue(value);
}
