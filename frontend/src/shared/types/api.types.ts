/** Generic paginated envelope returned by list endpoints. */
export type PaginatedResponse<T> = {
  items: T[];
  total: number;
  page: number;
  size: number;
};

/** Confidence level attached to answers, findings and sources. */
export type ConfidenceLevel = "high" | "medium" | "low";

/** Geography scope of a source or query filter. */
export type Geography = "RU" | "foreign" | "any";
