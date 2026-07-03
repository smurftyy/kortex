import { ApiError } from "./errors";

/**
 * Base URL defaults to the same-origin `/api/v1`, which next.config.mjs
 * rewrites to the FastAPI backend — the API currently ships no CORS
 * middleware, so cross-origin calls from the browser would be blocked.
 */
const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "/api/v1";

type TokenProvider = () => Promise<string | null>;

let tokenProvider: TokenProvider = async () => null;

/**
 * Wired up once by the AuthProvider to read the current Supabase session's
 * access token. Kept as an injection point so tests (and the client itself)
 * never import Supabase.
 */
export function setTokenProvider(provider: TokenProvider): void {
  tokenProvider = provider;
}

export type QueryValue = string | number | boolean | undefined | null;

export interface ApiFetchOptions {
  method?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  body?: unknown;
  query?: Record<string, QueryValue>;
  signal?: AbortSignal;
}

function buildUrl(path: string, query?: Record<string, QueryValue>): string {
  const url = `${API_BASE}${path}`;
  if (!query) return url;

  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined || value === null || value === "") continue;
    params.set(key, String(value));
  }
  const qs = params.toString();
  return qs ? `${url}?${qs}` : url;
}

export async function apiFetch<T>(
  path: string,
  options: ApiFetchOptions = {},
): Promise<T> {
  const { method = "GET", body, query, signal } = options;

  const headers = new Headers();
  const token = await tokenProvider();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  let requestBody: BodyInit | undefined;
  if (body instanceof FormData) {
    // Let the browser set the multipart boundary itself.
    requestBody = body;
  } else if (body !== undefined) {
    headers.set("Content-Type", "application/json");
    requestBody = JSON.stringify(body);
  }

  const response = await fetch(buildUrl(path, query), {
    method,
    headers,
    body: requestBody,
    signal,
  });

  if (!response.ok) {
    let parsed: unknown = null;
    try {
      parsed = await response.json();
    } catch {
      // Non-JSON error body (proxy error page, empty body, …) — fall
      // through to the status-only ApiError.
    }
    throw ApiError.fromResponseBody(response.status, parsed);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}
