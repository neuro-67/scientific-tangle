/** Lifecycle states of a document in the backend ingestion pipeline. */
export type DocumentStatus = "pending" | "processing" | "processed" | "failed";

/** Public view of a document and its ingestion status (mirrors DocumentResponse). */
export type Document = {
  id: string;
  filename: string;
  content_type: string;
  size: number;
  status: DocumentStatus;
  error: string | null;
  created_at: string;
  updated_at: string;
};
