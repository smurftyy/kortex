import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/api/errors";
import type { JobDetail } from "@/lib/api/types";
import { _resetActedJobs } from "@/lib/acted-jobs";
import { ToastProvider } from "@/providers/toast-provider";

import { JobDetailScreen } from "./job-detail-screen";

const pushMock = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock, replace: vi.fn(), back: vi.fn() }),
}));

const getJob = vi.fn();
const actOnJob = vi.fn();
vi.mock("@/lib/api/endpoints", () => ({
  getJob: (...args: unknown[]) => getJob(...args),
  actOnJob: (...args: unknown[]) => actOnJob(...args),
}));

const job: JobDetail = {
  job_id: "j-1",
  title: "Backend Engineering Intern",
  company: "Loop Logistics",
  location: "Austin, TX",
  description: "Build routing software.\n\nWork with PostgreSQL daily.",
  stack_tags: ["node", "postgresql"],
  apply_url: "https://jobs.example.com/loop/backend-intern",
  source_board: "lever",
  posted_at: "2026-07-01T00:00:00Z",
  discovered_at: "2026-07-03T09:00:00Z",
};

function renderScreen() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <JobDetailScreen jobId="j-1" />
      </ToastProvider>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  _resetActedJobs();
});

describe("JobDetailScreen", () => {
  it("renders the listing from GET /jobs/{id}", async () => {
    getJob.mockResolvedValue(job);
    renderScreen();

    expect(
      await screen.findByRole(
        "heading",
        { name: /backend engineering intern/i },
        { timeout: 5000 },
      ),
    ).toBeInTheDocument();
    expect(getJob).toHaveBeenCalledWith("j-1");
    expect(screen.getByText(/loop logistics · austin, tx/i)).toBeInTheDocument();
    expect(screen.getByText(/build routing software/i)).toBeInTheDocument();
    expect(screen.getByText("node")).toBeInTheDocument();

    const applyLink = screen.getByRole("link", {
      name: /open original listing/i,
    });
    expect(applyLink).toHaveAttribute("href", job.apply_url);
    expect(applyLink).toHaveAttribute("target", "_blank");
  });

  it("shows the closed-listing state on JOB_NOT_FOUND", async () => {
    getJob.mockRejectedValue(
      new ApiError(404, "JOB_NOT_FOUND", "Job not found"),
    );
    renderScreen();

    expect(
      await screen.findByText(
        /this listing is no longer available/i,
        {},
        { timeout: 5000 },
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /back to inbox/i }),
    ).toBeInTheDocument();
  });

  it("approves from the detail CTA and returns to the inbox", async () => {
    getJob.mockResolvedValue(job);
    actOnJob.mockResolvedValue(undefined);
    const user = userEvent.setup();
    renderScreen();
    await screen.findByRole(
      "heading",
      { name: /backend engineering intern/i },
      { timeout: 5000 },
    );

    await user.click(
      screen.getByRole("button", { name: /approve application/i }),
    );

    await waitFor(() => {
      expect(actOnJob).toHaveBeenCalledWith("j-1", "approve");
      expect(pushMock).toHaveBeenCalledWith("/");
    });
  });
});
