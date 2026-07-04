import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { JobListResponse } from "@/lib/api/types";
import { ToastProvider } from "@/providers/toast-provider";

import { InboxScreen } from "./inbox-screen";

let searchParamsString = "";
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(searchParamsString),
}));

const getJobs = vi.fn();
const getPreferences = vi.fn();
vi.mock("@/lib/api/endpoints", () => ({
  getJobs: (...args: unknown[]) => getJobs(...args),
  getPreferences: (...args: unknown[]) => getPreferences(...args),
  actOnJob: vi.fn(),
}));

function renderScreen() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <InboxScreen />
      </ToastProvider>
    </QueryClientProvider>,
  );
}

const jobsPage: JobListResponse = {
  results: [
    {
      job_id: "j-1",
      title: "Frontend Intern",
      company: "Northlight",
      location: "Remote",
      stack_tags: ["react"],
      source_board: "greenhouse",
      posted_at: null,
      discovered_at: "2026-07-03T09:00:00Z",
    },
    {
      job_id: "j-2",
      title: "Data Intern",
      company: "Fathom",
      location: null,
      stack_tags: [],
      source_board: "remoteok",
      posted_at: null,
      discovered_at: "2026-07-03T08:00:00Z",
    },
  ],
  page: 1,
  page_size: 20,
  total: 2,
};

beforeEach(() => {
  vi.clearAllMocks();
  searchParamsString = "";
  getPreferences.mockResolvedValue({
    boards_enabled: ["greenhouse", "lever", "remoteok"],
    digest_time_local: "15:00",
  });
});

describe("InboxScreen", () => {
  it("renders a card per job and the preferences-driven meta line", async () => {
    getJobs.mockResolvedValue(jobsPage);
    renderScreen();

    expect(
      await screen.findByText("Frontend Intern", {}, { timeout: 5000 }),
    ).toBeInTheDocument();
    expect(screen.getByText("Data Intern")).toBeInTheDocument();
    expect(
      screen.getByText(/2 opportunities discovered/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/3 boards monitored · next scan at 3:00 PM/i),
    ).toBeInTheDocument();
  });

  it("shows the caught-up empty state when there are no jobs", async () => {
    getJobs.mockResolvedValue({ ...jobsPage, results: [], total: 0 });
    renderScreen();

    expect(
      await screen.findByRole(
        "heading",
        { name: /you.re caught up/i },
        { timeout: 5000 },
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/after the next scheduled search, at 3:00 PM/i),
    ).toBeInTheDocument();
  });

  it("greets a just-onboarded user with the first-scan state and toast", async () => {
    searchParamsString = "welcome=1";
    getJobs.mockResolvedValue({ ...jobsPage, results: [], total: 0 });
    renderScreen();

    expect(
      await screen.findByRole(
        "heading",
        { name: /you.re all set/i },
        { timeout: 5000 },
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/your first scan runs at 3:00 PM/i),
    ).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent(
      "Setup complete. We'll start scanning today.",
    );
    expect(screen.queryByText(/you.re caught up/i)).not.toBeInTheDocument();
  });

  it("shows an error state with retry when the feed fails", async () => {
    getJobs.mockRejectedValue(new Error("boom"));
    renderScreen();

    expect(
      await screen.findByText(/couldn.t load your inbox/i, {}, { timeout: 5000 }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /try again/i }),
    ).toBeInTheDocument();
  });
});
