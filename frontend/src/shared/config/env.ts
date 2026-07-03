/**
 * Typed access to build-time environment variables.
 * Keep all `import.meta.env` reads here so the rest of the app stays testable.
 */
export const env = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL ?? "/api",
} as const;
