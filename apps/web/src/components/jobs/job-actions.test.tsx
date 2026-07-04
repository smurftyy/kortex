import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/api/errors";
import type { JobListResponse } from "@/lib/api/types";
import { _resetActedJobs } from "@/lib/acted-jobs";
import { ToastProvider } from "@/providers/toast-provider";

import { InboxScreen } from "./inbox-screen";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

const getJobs = vi.fn();
const getPreferences = vi.fn();
const actOnJob = vi.fn();
vi.mock("@/lib/api/endpoints", () => ({
  getJobs: (...args: unknown[]) => getJobs(...args),
  getPreferences: (...args: unknown[]) => getPreferences(...args),
  actOnJob: (...args: unknown[]) => actOnJob(...args),
}));

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

function renderScreen() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <InboxScreen />
      </ToastProvider>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  _resetActedJobs();
  getPreferences.mockResolvedValue({
    boards_enabled: ["greenhouse"],
    digest_time_local: "08:00",
  });
  getJobs.mockResolvedValue(jobsPage);
});

describe("Approve / Skip / Save", () => {
  it("optimistically removes the card before the request resolves, then toasts", async () => {
    let resolveAction!: () => void;
    actOnJob.mockImplementation(
      () =>
        new Promise<void>((resolve) => {
          resolveAction = resolve;
        }),
    );
    const user = userEvent.setup();
    renderScreen();
    await screen.findByText("Frontend Intern", {}, { timeout: 5000 });

    const card = screen
      .getByRole("heading", { name: "Frontend Intern" })
      .closest("article") as HTMLElement;
    await user.click(within(card).getByRole("button", { name: /approve/i }));

    // Optimistic: gone while the request is still in flight.
    expect(screen.queryByText("Frontend Intern")).not.toBeInTheDocument();
    expect(screen.getByText("Data Intern")).toBeInTheDocument();
    expect(actOnJob).toHaveBeenCalledWith("j-1", "approve");

    resolveAction();
    expect(
      await screen.findByRole("status", {}, { timeout: 5000 }),
    ).toHaveTextContent(
      "Approved — preparing application materials for Northlight.",
    );
    // Success invalidation refetches the public feed (which still contains
    // the job) — the acted-set must keep it hidden.
    await waitFor(() => {
      expect(screen.queryByText("Frontend Intern")).not.toBeInTheDocument();
    });
  });

  it("rolls the card back and explains when the API says MATCH_NOT_FOUND", async () => {
    actOnJob.mockRejectedValue(
      new ApiError(404, "MATCH_NOT_FOUND", "No match for this job"),
    );
    const user = userEvent.setup();
    renderScreen();
    await screen.findByText("Frontend Intern", {}, { timeout: 5000 });

    await user.click(screen.getAllByRole("button", { name: /^skip/i })[0]);

    expect(
      await screen.findByRole("status", {}, { timeout: 5000 }),
    ).toHaveTextContent(/hasn.t been matched to your profile yet/i);
    // Rolled back.
    expect(
      await screen.findByText("Frontend Intern", {}, { timeout: 5000 }),
    ).toBeInTheDocument();
  });

  it("fires the right endpoint and toast for save and skip", async () => {
    actOnJob.mockResolvedValue(undefined);
    const user = userEvent.setup();
    renderScreen();
    await screen.findByText("Frontend Intern", {}, { timeout: 5000 });

    await user.click(screen.getAllByRole("button", { name: /^save/i })[0]);
    expect(actOnJob).toHaveBeenCalledWith("j-1", "save");
    expect(
      await screen.findByRole("status", {}, { timeout: 5000 }),
    ).toHaveTextContent("Saved for later.");

    await user.click(screen.getAllByRole("button", { name: /^skip/i })[0]);
    expect(actOnJob).toHaveBeenCalledWith("j-2", "skip");
    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent("Skipped.");
    });
  });
});
