import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "./errors";
import { apiFetch, setTokenProvider } from "./client";

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

const fetchMock = vi.fn();

beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
  setTokenProvider(async () => null);
});

afterEach(() => {
  fetchMock.mockReset();
  vi.unstubAllGlobals();
});

describe("apiFetch", () => {
  it("returns parsed JSON on 200", async () => {
    fetchMock.mockResolvedValue(jsonResponse(200, { results: [], total: 0 }));

    const data = await apiFetch<{ results: unknown[]; total: number }>("/jobs");

    expect(data).toEqual({ results: [], total: 0 });
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/jobs",
      expect.objectContaining({ method: "GET" }),
    );
  });

  it("returns undefined on 204 without reading a body", async () => {
    fetchMock.mockResolvedValue(new Response(null, { status: 204 }));

    const data = await apiFetch<void>("/jobs/abc/approve", { method: "POST" });

    expect(data).toBeUndefined();
  });

  it("attaches the JWT as a Bearer token when the provider returns one", async () => {
    setTokenProvider(async () => "jwt-123");
    fetchMock.mockResolvedValue(jsonResponse(200, {}));

    await apiFetch("/auth/me");

    const headers = new Headers(fetchMock.mock.calls[0][1].headers);
    expect(headers.get("Authorization")).toBe("Bearer jwt-123");
  });

  it("omits the Authorization header when no token is available", async () => {
    fetchMock.mockResolvedValue(jsonResponse(200, {}));

    await apiFetch("/jobs");

    const headers = new Headers(fetchMock.mock.calls[0][1].headers);
    expect(headers.get("Authorization")).toBeNull();
  });

  it("serializes query params and skips undefined ones", async () => {
    fetchMock.mockResolvedValue(jsonResponse(200, {}));

    await apiFetch("/jobs", {
      query: { board: "lever", location: undefined, page: 2 },
    });

    expect(fetchMock.mock.calls[0][0]).toBe("/api/v1/jobs?board=lever&page=2");
  });

  it("sends JSON bodies with the right content type", async () => {
    fetchMock.mockResolvedValue(jsonResponse(200, {}));

    await apiFetch("/profile", {
      method: "PATCH",
      body: { full_name: "Ada" },
    });

    const [, init] = fetchMock.mock.calls[0];
    expect(init.body).toBe(JSON.stringify({ full_name: "Ada" }));
    expect(new Headers(init.headers).get("Content-Type")).toBe(
      "application/json",
    );
  });

  it("passes FormData through without forcing a content type", async () => {
    fetchMock.mockResolvedValue(jsonResponse(200, { resume_url: "signed" }));
    const form = new FormData();

    await apiFetch("/profile/resume", { method: "POST", body: form });

    const [, init] = fetchMock.mock.calls[0];
    expect(init.body).toBe(form);
    expect(new Headers(init.headers).get("Content-Type")).toBeNull();
  });

  describe("error parsing", () => {
    it("parses the standard error envelope", async () => {
      fetchMock.mockResolvedValue(
        jsonResponse(404, {
          error: {
            code: "PROFILE_NOT_FOUND",
            message: "No profile yet",
            field: null,
          },
        }),
      );

      const err = await apiFetch("/auth/me").catch((e: unknown) => e);

      expect(err).toBeInstanceOf(ApiError);
      expect(err).toMatchObject({
        status: 404,
        code: "PROFILE_NOT_FOUND",
        message: "No profile yet",
        field: null,
      });
    });

    it("parses the FastAPI fallback shape with a string detail", async () => {
      // Known open bug: malformed UUID path params return FastAPI's default
      // shape, not the envelope. The client must not crash on it.
      fetchMock.mockResolvedValue(
        jsonResponse(422, { detail: "Input should be a valid UUID" }),
      );

      const err = await apiFetch("/jobs/not-a-uuid").catch((e: unknown) => e);

      expect(err).toBeInstanceOf(ApiError);
      expect(err).toMatchObject({
        status: 422,
        code: "UNKNOWN",
        message: "Input should be a valid UUID",
      });
    });

    it("parses the FastAPI validation-array shape", async () => {
      fetchMock.mockResolvedValue(
        jsonResponse(422, {
          detail: [
            {
              loc: ["path", "job_id"],
              msg: "value is not a valid uuid",
              type: "type_error.uuid",
            },
          ],
        }),
      );

      const err = await apiFetch("/jobs/oops").catch((e: unknown) => e);

      expect(err).toBeInstanceOf(ApiError);
      expect(err).toMatchObject({
        status: 422,
        code: "UNKNOWN",
        message: "value is not a valid uuid",
        field: "job_id",
      });
    });

    it("never assumes error.code exists — envelope missing fields", async () => {
      fetchMock.mockResolvedValue(jsonResponse(500, { error: {} }));

      const err = await apiFetch("/jobs").catch((e: unknown) => e);

      expect(err).toBeInstanceOf(ApiError);
      expect(err).toMatchObject({ status: 500, code: "UNKNOWN" });
    });

    it("survives a non-JSON error body", async () => {
      fetchMock.mockResolvedValue(
        new Response("<html>Bad gateway</html>", { status: 502 }),
      );

      const err = await apiFetch("/jobs").catch((e: unknown) => e);

      expect(err).toBeInstanceOf(ApiError);
      expect(err).toMatchObject({ status: 502, code: "UNKNOWN" });
    });
  });
});
