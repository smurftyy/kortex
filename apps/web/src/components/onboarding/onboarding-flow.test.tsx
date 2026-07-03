import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { OnboardingFlow } from "./onboarding-flow";

const replaceMock = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: replaceMock, push: vi.fn() }),
}));

vi.mock("@/providers/auth-provider", () => ({
  useAuth: () => ({
    user: { id: "user-1", email: "ada@example.com" },
    session: { access_token: "t" },
    isLoading: false,
  }),
}));

const putPreferences = vi.fn();
vi.mock("@/lib/api/endpoints", () => ({
  putPreferences: (...args: unknown[]) => putPreferences(...args),
  uploadResume: vi.fn(),
  parseResume: vi.fn(),
}));

const upsertMock = vi.fn();
const fromMock = vi.fn(() => ({ upsert: upsertMock }));
vi.mock("@/lib/supabase/client", () => ({
  getSupabaseClient: () => ({ from: fromMock }),
}));

function renderFlow() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <OnboardingFlow />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  upsertMock.mockResolvedValue({ error: null });
  putPreferences.mockResolvedValue({ id: "p1" });
});

describe("OnboardingFlow", () => {
  it("walks all steps and submits the contract-shaped payloads", { timeout: 15_000 }, async () => {
    const user = userEvent.setup();
    renderFlow();

    // Step 1 — personal info (Continue persists the profile row so the
    // resume endpoints on step 3 don't 404).
    await user.type(screen.getByLabelText(/full name/i), "Ada Lovelace");
    await user.type(screen.getByLabelText(/phone/i), "+2348000000");
    await user.type(screen.getByLabelText(/^location/i), "Lagos, Nigeria");
    await user.selectOptions(
      screen.getByLabelText(/experience level/i),
      "junior",
    );
    await user.click(screen.getByRole("button", { name: /continue/i }));

    // Step 2 — skills
    expect(
      await screen.findByRole("heading", { name: /what are your skills/i }),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Python" }));
    await user.click(screen.getByRole("button", { name: "React" }));
    await user.click(screen.getByRole("button", { name: /continue/i }));

    // Step 3 — resume (optional, skip past it)
    expect(
      await screen.findByRole("heading", { name: /upload your master resume/i }),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /continue/i }));

    // Step 4 — preferences
    expect(
      await screen.findByRole("heading", { name: /search preferences/i }),
    ).toBeInTheDocument();
    const rolesInput = screen.getByPlaceholderText(/type a role/i);
    await user.type(rolesInput, "Backend Intern{Enter}");
    const locationsInput = screen.getByPlaceholderText(/type a location/i);
    await user.type(locationsInput, "remote{Enter}lagos{Enter}");

    // Boards default to all enabled — disable one.
    await user.click(screen.getByRole("checkbox", { name: /web3\.career/i }));

    await user.click(screen.getByRole("button", { name: /finish setup/i }));

    await waitFor(() => {
      expect(fromMock).toHaveBeenCalledWith("profiles");
    });
    // Once on step-1 Continue, once with the complete data on finish.
    expect(upsertMock).toHaveBeenCalledTimes(2);
    expect(upsertMock).toHaveBeenLastCalledWith(
      {
        id: "user-1",
        full_name: "Ada Lovelace",
        phone: "+2348000000",
        location: "Lagos, Nigeria",
        github_url: null,
        portfolio_url: null,
        linkedin_url: null,
        experience_level: "junior",
        target_roles: ["Backend Intern"],
        skills: ["Python", "React"],
      },
      { onConflict: "id" },
    );

    expect(putPreferences).toHaveBeenCalledWith({
      boards_enabled: [
        "greenhouse",
        "lever",
        "workable",
        "remoteok",
        "cryptojobslist",
        "linkedin",
      ],
      location_filter: ["remote", "lagos"],
      excluded_keywords: [],
      digest_time_local: "08:00",
      digest_timezone: expect.any(String),
      match_score_threshold: 2.0,
    });

    await waitFor(() => {
      expect(replaceMock).toHaveBeenCalledWith("/");
    });
  });

  it("keeps Continue disabled until required step-1 fields are filled", async () => {
    const user = userEvent.setup();
    renderFlow();

    const continueBtn = screen.getByRole("button", { name: /continue/i });
    expect(continueBtn).toBeDisabled();

    await user.type(screen.getByLabelText(/full name/i), "Ada");
    await user.selectOptions(
      screen.getByLabelText(/experience level/i),
      "intern",
    );
    expect(continueBtn).toBeEnabled();
  });

  it("shows the API error when finishing fails", { timeout: 15_000 }, async () => {
    putPreferences.mockRejectedValue(new Error("network down"));
    const user = userEvent.setup();
    renderFlow();

    await user.type(screen.getByLabelText(/full name/i), "Ada");
    await user.selectOptions(
      screen.getByLabelText(/experience level/i),
      "intern",
    );
    await user.click(screen.getByRole("button", { name: /continue/i }));
    await user.click(await screen.findByRole("button", { name: /continue/i }));
    await user.click(await screen.findByRole("button", { name: /continue/i }));
    const rolesInput = await screen.findByPlaceholderText(/type a role/i);
    await user.type(rolesInput, "SWE Intern{Enter}");
    await user.click(screen.getByRole("button", { name: /finish setup/i }));

    expect(await screen.findByText(/network down/i)).toBeInTheDocument();
    expect(replaceMock).not.toHaveBeenCalled();
  });
});
