import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { JobListResponse, JobsQuery } from "@/lib/api/types";
import { ToastProvider } from "@/providers/toast-provider";

import { InboxScreen } from "./inbox-screen";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}));

const getJobs = vi.fn();
const getPreferences = vi.fn();
vi.mock("@/lib/api/endpoints", () => ({
  getJobs: (...args: unknown[]) => getJobs(...args),
  getPreferences: (...args: unknown[]) => getPreferences(...args),
  actOnJob: vi.fn(),
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
  ],
  page: 1,
  page_size: 20,
  total: 1,
};

const emptyPage: JobListResponse = {
  results: [],
  page: 1,
  page_size: 20,
  total: 0,
};

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

beforeEach(() => {
  vi.clearAllMocks();
  getPreferences.mockResolvedValue({
    boards_enabled: ["greenhouse"],
    digest_time_local: "08:00",
  });
  // Unfiltered feed has results; any filter narrows to zero.
  getJobs.mockImplementation((params: JobsQuery) =>
    Promise.resolve(
      params.board || params.location || params.stack || params.date_from
        ? emptyPage
        : jobsPage,
    ),
  );
});

describe("FilterBar (via InboxScreen)", () => {
  it("passes the board filter through to GET /jobs", async () => {
    const user = userEvent.setup();
    renderScreen();
    await screen.findByText("Frontend Intern", {}, { timeout: 5000 });

    await user.selectOptions(screen.getByLabelText(/board/i), "lever");

    await waitFor(
      () => {
        expect(getJobs).toHaveBeenCalledWith(
          expect.objectContaining({ board: "lever" }),
        );
      },
      { timeout: 5000 },
    );
  });

  it("debounces the location input into the location param", async () => {
    const user = userEvent.setup();
    renderScreen();
    await screen.findByText("Frontend Intern", {}, { timeout: 5000 });

    await user.type(screen.getByLabelText(/location/i), "lagos");

    await waitFor(
      () => {
        expect(getJobs).toHaveBeenCalledWith(
          expect.objectContaining({ location: "lagos" }),
        );
      },
      { timeout: 5000 },
    );
  });

  it("maps the date preset onto date_from", async () => {
    const user = userEvent.setup();
    renderScreen();
    await screen.findByText("Frontend Intern", {}, { timeout: 5000 });

    await user.selectOptions(screen.getByLabelText(/posted/i), "week");

    await waitFor(
      () => {
        expect(getJobs).toHaveBeenCalledWith(
          expect.objectContaining({ date_from: expect.any(String) }),
        );
      },
      { timeout: 5000 },
    );
  });

  it("shows the zero-results state with working clear-filters", async () => {
    const user = userEvent.setup();
    renderScreen();
    await screen.findByText("Frontend Intern", {}, { timeout: 5000 });

    await user.selectOptions(screen.getByLabelText(/board/i), "lever");

    expect(
      await screen.findByText(
        /nothing matches these filters/i,
        {},
        { timeout: 5000 },
      ),
    ).toBeInTheDocument();
    // Must be the filtered empty state, not the caught-up one.
    expect(screen.queryByText(/you.re caught up/i)).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /clear filters/i }));

    expect(
      await screen.findByText("Frontend Intern", {}, { timeout: 5000 }),
    ).toBeInTheDocument();
  });
});
