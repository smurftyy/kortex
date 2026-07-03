/**
 * Typed error thrown by the API client for any non-2xx response.
 *
 * The API normally answers with the envelope from API_CONTRACT_kortex.md
 * (`{"error": {"code", "message", "field"}}`), but malformed UUID path
 * params currently fall back to FastAPI's default `{"detail": ...}` shape
 * (open bug, deferred to Phase 6). `fromResponseBody` accepts both — and
 * anything else — without ever assuming a field exists.
 */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly field: string | null;

  constructor(status: number, code: string, message: string, field: string | null = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.field = field;
  }

  static fromResponseBody(status: number, body: unknown): ApiError {
    const fallbackMessage = `Request failed with status ${status}`;

    if (typeof body === "object" && body !== null) {
      const record = body as Record<string, unknown>;

      const envelope = record.error;
      if (typeof envelope === "object" && envelope !== null) {
        const err = envelope as Record<string, unknown>;
        return new ApiError(
          status,
          typeof err.code === "string" ? err.code : "UNKNOWN",
          typeof err.message === "string" ? err.message : fallbackMessage,
          typeof err.field === "string" ? err.field : null,
        );
      }

      const detail = record.detail;
      if (typeof detail === "string") {
        return new ApiError(status, "UNKNOWN", detail);
      }
      if (Array.isArray(detail) && detail.length > 0) {
        const first = detail[0] as Record<string, unknown>;
        const loc = Array.isArray(first?.loc) ? first.loc : [];
        const lastLoc = loc[loc.length - 1];
        return new ApiError(
          status,
          "UNKNOWN",
          typeof first?.msg === "string" ? first.msg : fallbackMessage,
          typeof lastLoc === "string" ? lastLoc : null,
        );
      }
    }

    return new ApiError(status, "UNKNOWN", fallbackMessage);
  }
}
