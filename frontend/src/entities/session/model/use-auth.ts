import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { ROUTES } from "@/shared/constants";
import { getAccessToken, setAccessToken } from "@/shared/lib/axios";

import { queries } from "../api/session.queries";

/**
 * Auth state derived from the stored JWT + the `me` query.
 * Provides a `logout` that clears the token and query cache.
 */
export function useAuth() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const hasToken = Boolean(getAccessToken());

  const meQuery = useQuery({ ...queries.me(), enabled: hasToken });

  const logout = () => {
    setAccessToken(null);
    queryClient.clear();
    navigate(ROUTES.login);
  };

  return {
    user: meQuery.data ?? null,
    isAuthenticated: hasToken,
    isLoadingUser: meQuery.isLoading,
    logout,
  };
}
