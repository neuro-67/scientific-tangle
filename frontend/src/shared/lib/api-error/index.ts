import { isAxiosError } from "axios";
import { toast } from "sonner";

type ApiErrorPayload = {
  details?: Array<{ message?: string }>;
  detail?: string;
  message?: string;
  error?: string;
};

type HandleApiErrorOptions = {
  /** Message shown when no backend message can be extracted. */
  fallback?: string;
  /** Show a sonner error toast. Defaults to `true`. */
  showToast?: boolean;
};

const extractMessage = (error: unknown, fallback: string): string => {
  if (isAxiosError<ApiErrorPayload>(error)) {
    const data = error.response?.data;
    const fromDetails = data?.details?.find((d) => d.message)?.message;
    return (
      fromDetails ??
      data?.detail ??
      data?.message ??
      data?.error ??
      error.message ??
      fallback
    );
  }
  if (error instanceof Error) return error.message || fallback;
  return fallback;
};

/**
 * Normalize an API error into a user-facing string and (by default) show a
 * toast. Reuse this everywhere instead of writing local error parsers.
 */
export const handleApiError = (
  error: unknown,
  options: HandleApiErrorOptions = {}
): string => {
  const { fallback = "Что-то пошло не так", showToast = true } = options;
  const message = extractMessage(error, fallback);
  if (showToast) toast.error(message);
  return message;
};
