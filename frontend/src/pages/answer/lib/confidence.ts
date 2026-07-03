import type { ConfidenceLevel, Geography } from "@/shared/types";

type BadgeVariant =
  | "confidenceHigh"
  | "confidenceMedium"
  | "confidenceLow"
  | "geoRu"
  | "geoForeign"
  | "outline";

const CONFIDENCE_VARIANT: Record<ConfidenceLevel, BadgeVariant> = {
  high: "confidenceHigh",
  medium: "confidenceMedium",
  low: "confidenceLow",
};

const CONFIDENCE_LABEL: Record<ConfidenceLevel, string> = {
  high: "высокая достоверность",
  medium: "средняя достоверность",
  low: "низкая достоверность",
};

export const confidenceVariant = (level: ConfidenceLevel): BadgeVariant =>
  CONFIDENCE_VARIANT[level];

export const confidenceLabel = (level: ConfidenceLevel): string =>
  CONFIDENCE_LABEL[level];

export const geographyVariant = (geo: Geography): BadgeVariant => {
  if (geo === "RU") return "geoRu";
  if (geo === "foreign") return "geoForeign";
  return "outline";
};

export const geographyLabel = (geo: Geography): string => {
  if (geo === "RU") return "РФ";
  if (geo === "foreign") return "зарубеж";
  return "все";
};
