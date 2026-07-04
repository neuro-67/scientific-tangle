import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { ROUTES } from "@/shared/constants";

import { logout as logoutRequest } from "../api/logout";
import { queries } from "../api/session.queries";

/**
 * Auth state derived from the `GET /auth/me` query. The access token lives in
 * an httpOnly cookie that JS can't read, so "am I logged in?" is answered by
 * whether `me` resolves — a 401 simply means not authenticated.
 */
export function useAuth() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const meQuery = useQuery({ ...queries.me(), retry: false });

  const logoutMutation = useMutation({
    mutationFn: logoutRequest,
    onSettled: () => {
      queryClient.clear();
      navigate(ROUTES.login);
    },
  });

  return {
    user: meQuery.data ?? null,
    isAuthenticated: meQuery.isSuccess && meQuery.data != null,
    isLoadingUser: meQuery.isPending,
    logout: () => logoutMutation.mutate(),
  };
}
