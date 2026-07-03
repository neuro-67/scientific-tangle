/// <reference types="vite/client" />

type ImportMetaEnv = {
  readonly VITE_API_BASE_URL?: string;
  /** Set to "false" to hit the real backend instead of the MSW mock in dev. */
  readonly VITE_ENABLE_MOCKS?: string;
};

type ImportMeta = {
  readonly env: ImportMetaEnv;
};
