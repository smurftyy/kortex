import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { RequireAuth } from "./guards";

const replaceMock = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: replaceMock, push: vi.fn() }),
}));

const useAuthMock = vi.fn();
vi.mock("@/providers/auth-provider", () => ({
  useAuth: () => useAuthMock(),
}));

beforeEach(() => {
  vi.clearAllMocks();
});

describe("RequireAuth", () => {
  it("redirects to /login when unauthenticated", () => {
    useAuthMock.mockReturnValue({ session: null, user: null, isLoading: false });

    render(
      <RequireAuth>
        <p>secret</p>
      </RequireAuth>,
    );

    expect(replaceMock).toHaveBeenCalledWith("/login");
    expect(screen.queryByText("secret")).not.toBeInTheDocument();
  });

  it("renders nothing (no redirect) while the session is still loading", () => {
    useAuthMock.mockReturnValue({ session: null, user: null, isLoading: true });

    render(
      <RequireAuth>
        <p>secret</p>
      </RequireAuth>,
    );

    expect(replaceMock).not.toHaveBeenCalled();
    expect(screen.queryByText("secret")).not.toBeInTheDocument();
  });

  it("renders children when a session exists", () => {
    useAuthMock.mockReturnValue({
      session: { access_token: "t" },
      user: { id: "u1" },
      isLoading: false,
    });

    render(
      <RequireAuth>
        <p>secret</p>
      </RequireAuth>,
    );

    expect(screen.getByText("secret")).toBeInTheDocument();
    expect(replaceMock).not.toHaveBeenCalled();
  });
});
