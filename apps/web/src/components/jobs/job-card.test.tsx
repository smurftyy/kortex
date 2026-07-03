import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { JobListItem } from "@/lib/api/types";

import { JobCard } from "./job-card";

const job: JobListItem = {
  job_id: "j-1",
  title: "Backend Engineering Intern",
  company: "Loop Logistics",
  location: "Remote — Europe",
  stack_tags: ["python", "postgresql"],
  source_board: "lever",
  posted_at: "2026-07-01T00:00:00Z",
  discovered_at: "2026-07-03T09:00:00Z",
};

describe("JobCard", () => {
  it("renders title, company, location, tags, and board", () => {
    render(<JobCard job={job} />);

    expect(
      screen.getByRole("heading", { name: /backend engineering intern/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/loop logistics · remote — europe/i),
    ).toBeInTheDocument();
    expect(screen.getByText("python")).toBeInTheDocument();
    expect(screen.getByText("postgresql")).toBeInTheDocument();
    expect(screen.getByText(/via lever/i)).toBeInTheDocument();
  });

  it("shows the Remote pill only for remote locations", () => {
    const { rerender } = render(<JobCard job={job} />);
    expect(screen.getByText("Remote")).toBeInTheDocument();

    rerender(<JobCard job={{ ...job, location: "Lagos, Nigeria" }} />);
    expect(screen.queryByText("Remote")).not.toBeInTheDocument();
  });

  it("exposes keyboard-reachable Approve / Skip / Save actions", async () => {
    const onAction = vi.fn();
    const user = userEvent.setup();
    render(<JobCard job={job} onAction={onAction} />);

    await user.tab(); // Skip
    await user.keyboard("{Enter}");
    expect(onAction).toHaveBeenLastCalledWith(job, "skip");

    await user.click(screen.getByRole("button", { name: /^save/i }));
    expect(onAction).toHaveBeenLastCalledWith(job, "save");

    await user.click(screen.getByRole("button", { name: /^approve/i }));
    expect(onAction).toHaveBeenLastCalledWith(job, "approve");
  });
});
