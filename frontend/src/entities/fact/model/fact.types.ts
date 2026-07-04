export type FactRevision = {
  superseded_at: string;
  superseded_by_document: string | null;
  previous_properties: Record<string, unknown>;
};
