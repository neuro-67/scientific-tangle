import { API } from "@/shared/lib/axios";

import type { DashboardSummary } from "../model/dashboard.types";

export type Req = void;

type Res = DashboardSummary;

export const getDashboardSummary = () =>
  API.get<Res>("/dashboard/summary").then((r) => r.data);
