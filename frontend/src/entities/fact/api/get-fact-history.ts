import { API } from "@/shared/lib/axios";

import type { FactRevision } from "../model/fact.types";

export type Req = {
  factId: string;
};

type Res = FactRevision[];

export const getFactHistory = ({ factId }: Req) =>
  API.get<Res>(`/graph/facts/${encodeURIComponent(factId)}/history`).then(
    (r) => r.data
  );
