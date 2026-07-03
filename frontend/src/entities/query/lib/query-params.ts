import type { ConfidenceLevel, Geography } from "@/shared/types";

import type { Req as PostQueryReq } from "../api/post-query";
import type { QueryFilters } from "../model/query.types";

/** Empty filter state for the search form. */
export const emptyQueryFilters = (): QueryFilters => ({
  question: "",
  materials: [],
  processes: [],
  geography: "any",
  yearFrom: null,
  yearTo: null,
  confidence: "any",
});

/** Map the search form state to a POST /query request body. */
export const filtersToRequest = (filters: QueryFilters): PostQueryReq => ({
  question: filters.question.trim(),
  materials: filters.materials.length ? filters.materials : undefined,
  processes: filters.processes.length ? filters.processes : undefined,
  geography: filters.geography !== "any" ? filters.geography : undefined,
  year_from: filters.yearFrom ?? undefined,
  year_to: filters.yearTo ?? undefined,
  confidence: filters.confidence !== "any" ? filters.confidence : undefined,
});

/** Serialize a request into readable, shareable URL search params. */
export const requestToSearchParams = (req: PostQueryReq): URLSearchParams => {
  const params = new URLSearchParams();
  params.set("q", req.question);
  if (req.materials?.length) params.set("materials", req.materials.join(","));
  if (req.processes?.length) params.set("processes", req.processes.join(","));
  if (req.geography) params.set("geo", req.geography);
  if (req.year_from !== undefined) params.set("yf", String(req.year_from));
  if (req.year_to !== undefined) params.set("yt", String(req.year_to));
  if (req.confidence) params.set("conf", req.confidence);
  return params;
};

const num = (raw: string | null): number | undefined =>
  raw === null || raw === "" ? undefined : Number(raw);

const list = (raw: string | null): string[] | undefined =>
  raw ? raw.split(",").map((s) => s.trim()).filter(Boolean) : undefined;

/** Reconstruct a request from URL search params (answer screen entry point). */
export const searchParamsToRequest = (
  params: URLSearchParams
): PostQueryReq => ({
  question: params.get("q") ?? "",
  materials: list(params.get("materials")),
  processes: list(params.get("processes")),
  geography: (params.get("geo") as Geography | null) ?? undefined,
  year_from: num(params.get("yf")),
  year_to: num(params.get("yt")),
  confidence: (params.get("conf") as ConfidenceLevel | null) ?? undefined,
});
