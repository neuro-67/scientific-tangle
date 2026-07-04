import type { ConfidenceLevel, Geography } from "@/shared/types";

import type { Req as PostQueryReq } from "../api/post-query";
import type { QueryFilters } from "../model/query.types";

/** Empty filter state for the search form. */
export const emptyQueryFilters = (): QueryFilters => ({
  question: "",
  materials: [],
  processes: [],
  geography: "any",
  dateFrom: null,
  dateTo: null,
  confidence: "any",
});

/** Map the search form state to a POST /query request body. */
export const filtersToRequest = (filters: QueryFilters): PostQueryReq => ({
  question: filters.question.trim(),
  materials: filters.materials.length ? filters.materials : undefined,
  processes: filters.processes.length ? filters.processes : undefined,
  geography: filters.geography !== "any" ? filters.geography : undefined,
  date_from: filters.dateFrom ?? undefined,
  date_to: filters.dateTo ?? undefined,
  confidence: filters.confidence !== "any" ? filters.confidence : undefined,
});

/** Serialize a request into readable, shareable URL search params. */
export const requestToSearchParams = (req: PostQueryReq): URLSearchParams => {
  const params = new URLSearchParams();
  params.set("q", req.question);
  if (req.materials?.length) params.set("materials", req.materials.join(","));
  if (req.processes?.length) params.set("processes", req.processes.join(","));
  if (req.geography) params.set("geo", req.geography);
  if (req.date_from) params.set("df", req.date_from);
  if (req.date_to) params.set("dt", req.date_to);
  if (req.confidence) params.set("conf", req.confidence);
  return params;
};

const list = (raw: string | null): string[] | undefined =>
  raw
    ? raw
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean)
    : undefined;

/** Reconstruct a request from URL search params (answer screen entry point). */
export const searchParamsToRequest = (
  params: URLSearchParams
): PostQueryReq => ({
  question: params.get("q") ?? "",
  materials: list(params.get("materials")),
  processes: list(params.get("processes")),
  geography: (params.get("geo") as Geography | null) ?? undefined,
  date_from: params.get("df") ?? undefined,
  date_to: params.get("dt") ?? undefined,
  confidence: (params.get("conf") as ConfidenceLevel | null) ?? undefined,
});

/** Convert an API request back to the search form filter state. */
export const requestToFilters = (req: PostQueryReq): QueryFilters => ({
  question: req.question,
  materials: req.materials ?? [],
  processes: req.processes ?? [],
  geography: req.geography ?? "any",
  dateFrom: req.date_from ?? null,
  dateTo: req.date_to ?? null,
  confidence: req.confidence ?? "any",
});
