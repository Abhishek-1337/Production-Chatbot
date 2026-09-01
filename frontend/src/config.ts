export const API_URL =
  (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, "") ??
  "http://localhost:8000/api/v1";

export const GOOGLE_OAUTH_URL =
  (import.meta.env.VITE_GOOGLE_OAUTH_URL as string | undefined)?.replace(/\/$/, "") ??
  `${API_URL}/auth/google/login`;

if (!import.meta.env.VITE_API_URL) {
  console.warn(
    "[config] VITE_API_URL not set — falling back to http://localhost:8000/api/v1. " +
      "Set it in frontend/.env (local) or Vercel Environment Variables (production)."
  );
}
