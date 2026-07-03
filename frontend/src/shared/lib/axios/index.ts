import axios from "axios";

import { env } from "@/shared/config/env";

const TOKEN_STORAGE_KEY = "st_access_token";

/** Read the persisted JWT (set on login). */
export const getAccessToken = () => localStorage.getItem(TOKEN_STORAGE_KEY);

/** Persist or clear the JWT. */
export const setAccessToken = (token: string | null) => {
  if (token) {
    localStorage.setItem(TOKEN_STORAGE_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
  }
};

/**
 * Shared axios instance. Every API file must import `API` from here and call
 * `API.get/post/patch/put/delete` directly (see docs/frontend/AGENTS.md).
 */
export const API = axios.create({
  baseURL: env.apiBaseUrl,
  headers: { "Content-Type": "application/json" },
});

API.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});
