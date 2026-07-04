import type { DocumentStatus } from "@/entities/document";

/** Human-readable file size, e.g. 1536 -> "1.5 КБ". */
export function formatBytes(bytes: number): string {
  if (bytes <= 0) return "0 Б";
  const units = ["Б", "КБ", "МБ", "ГБ"];
  const i = Math.min(
    units.length - 1,
    Math.floor(Math.log(bytes) / Math.log(1024))
  );
  const value = bytes / 1024 ** i;
  return `${i === 0 ? value : value.toFixed(1)} ${units[i]}`;
}

/** Russian label for an ingestion status. */
export function statusLabel(status: DocumentStatus): string {
  switch (status) {
    case "pending":
      return "В очереди";
    case "processing":
      return "Обработка";
    case "processed":
      return "Готово";
    case "failed":
      return "Ошибка";
  }
}

/** Whether a status is terminal (no further polling needed). */
export function isTerminal(status: DocumentStatus): boolean {
  return status === "processed" || status === "failed";
}
