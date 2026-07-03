import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/api/errors";

import { OnboardingGate } from "./onboarding-gate";

const replaceMock = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: replaceMock, push: vi.fn() }),
}));

const getMe = vi.fn();
vi.mock("@/lib/api/endpoints", () => ({
  getMe: (...args: unknown[]) => getMe(...args),
}));

function renderWithClient(ui: React.ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("OnboardingGate", () => {
  it("redirects to /onboarding when the profile does not exist yet", async () => {
    getMe.mockRejectedValue(
      new ApiError(404, "PROFILE_NOT_FOUND", "No profile"),
    );

    renderWithClient(
      <OnboardingGate>
        <p>dashboard</p>
      </OnboardingGate>,
    );

    await waitFor(() => {
      expect(replaceMock).toHaveBeenCalledWith("/onboarding");
    });
    expect(screen.queryByText("dashboard")).not.toBeInTheDocument();
  });

  it("renders children when the profile exists", async () => {
    getMe.mockResolvedValue({ id: "u1", full_name: "Ada" });

    renderWithClient(
      <OnboardingGate>
        <p>dashboard</p>
      </OnboardingGate>,
    );

    expect(await screen.findByText("dashboard")).toBeInTheDocument();
    expect(replaceMock).not.toHaveBeenCalled();
  });

  it("surfaces non-404 errors instead of redirecting", async () => {
    getMe.mockRejectedValue(new ApiError(500, "UNKNOWN", "boom"));

    renderWithClient(
      <OnboardingGate>
        <p>dashboard</p>
      </OnboardingGate>,
    );

    expect(
      await screen.findByText(/couldn.t load your profile/i),
    ).toBeInTheDocument();
    expect(replaceMock).not.toHaveBeenCalled();
  });
});
