"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api/errors";
import { boardLabel } from "@/lib/boards";
import { relativeTime } from "@/lib/format";
import { useJobAction } from "@/lib/mutations/job-actions";
import { useJob } from "@/lib/queries/jobs";

function BackToInbox() {
  return (
    <Link
      href="/"
      className="mb-[22px] flex w-fit items-center gap-[5px] text-[13.5px] font-medium text-ink-500 hover:text-ink-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
    >
      <svg
        width="16"
        height="16"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <polyline points="15 18 9 12 15 6" />
      </svg>
      Back to Inbox
    </Link>
  );
}

/**
 * The design's two-pane detail screen, driven by GET /jobs/{id}. The
 * right rail's "Application prep" widgets (match %, tailored resume,
 * cover letter, readiness checklist) have no backing endpoints until
 * Phase 4 — the rail carries the listing facts the contract provides.
 */
export function JobDetailScreen({ jobId }: { jobId: string }) {
  const router = useRouter();
  const { data: job, isPending, error } = useJob(jobId);
  const jobAction = useJobAction();

  if (isPending) {
    return (
      <div className="px-12 pt-10" aria-hidden="true">
        <div className="mb-6 h-4 w-24 animate-pulse rounded bg-line" />
        <div className="mb-3 h-8 w-2/3 animate-pulse rounded bg-line" />
        <div className="h-4 w-1/3 animate-pulse rounded bg-line" />
      </div>
    );
  }

  if (error) {
    const closed = error instanceof ApiError && error.status === 404;
    return (
      <div className="flex h-full flex-col items-center justify-center gap-4 px-8 text-center">
        <p className="text-[14.5px] text-ink-500">
          {closed
            ? "This listing is no longer available."
            : "We couldn’t load this listing."}
        </p>
        <Link
          href="/"
          className="text-[13.5px] font-semibold text-accent hover:text-accent-deep"
        >
          Back to Inbox
        </Link>
      </div>
    );
  }

  const isRemote = (job.location ?? "").toLowerCase().includes("remote");
  const act = (action: "approve" | "skip" | "save") =>
    jobAction.mutate(
      { job, action },
      { onSuccess: () => router.push("/") },
    );

  return (
    <div className="flex h-full">
      <div className="min-w-0 flex-[1.5] overflow-y-auto border-r border-line-soft px-12 pb-20 pt-10">
        <BackToInbox />

        <div className="mb-1 flex items-center gap-2.5">
          <h1 className="text-[26px] font-bold tracking-[-0.3px] text-ink-900">
            {job.title}
          </h1>
          {isRemote && (
            <span className="rounded-full bg-chip px-2 py-0.5 text-[11px] font-semibold text-ink-600">
              Remote
            </span>
          )}
        </div>
        <p className="mb-8 text-[15px] text-ink-500">
          {job.company}
          {job.location ? ` · ${job.location}` : ""}
        </p>

        <div className="max-w-[560px] whitespace-pre-wrap text-[15.5px] leading-[1.7] text-ink-700">
          {job.description}
        </div>
      </div>

      <div className="h-full min-w-[340px] max-w-[400px] flex-1 overflow-y-auto bg-raised px-8 py-10">
        <div className="mb-[18px] flex items-center justify-between">
          <span className="text-[12.5px] font-semibold uppercase tracking-[0.4px] text-ink-400">
            Listing
          </span>
        </div>

        {job.stack_tags.length > 0 && (
          <div className="mb-3.5 rounded-xl border border-line bg-white px-[18px] py-4">
            <div className="mb-2.5 text-[13px] font-semibold text-ink-900">
              Stack
            </div>
            <div className="flex flex-wrap gap-1.5">
              {job.stack_tags.map((tag) => (
                <span
                  key={tag}
                  className="rounded-full bg-accent-tint px-2.5 py-1 text-[12.5px] font-medium text-accent-deep"
                >
                  {tag}
                </span>
              ))}
            </div>
          </div>
        )}

        <div className="mb-[22px] rounded-xl border border-line bg-white px-[18px] py-4">
          <div className="mb-2.5 text-[13px] font-semibold text-ink-900">
            Details
          </div>
          <dl className="flex flex-col gap-2 text-[13px] text-ink-700">
            <div className="flex justify-between gap-3">
              <dt className="text-ink-400">Source</dt>
              <dd>{boardLabel(job.source_board)}</dd>
            </div>
            {job.posted_at && (
              <div className="flex justify-between gap-3">
                <dt className="text-ink-400">Posted</dt>
                <dd>
                  {new Date(job.posted_at).toLocaleDateString("en-US", {
                    month: "short",
                    day: "numeric",
                  })}
                </dd>
              </div>
            )}
            <div className="flex justify-between gap-3">
              <dt className="text-ink-400">Discovered</dt>
              <dd>{relativeTime(job.discovered_at)}</dd>
            </div>
          </dl>
        </div>

        <a
          href={job.apply_url}
          target="_blank"
          rel="noopener noreferrer"
          className="mb-2.5 flex w-full items-center justify-center gap-1.5 rounded-xl border border-line bg-white py-3 text-[14px] font-medium text-ink-700 hover:bg-white/60 focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
        >
          Open original listing
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
            <polyline points="15 3 21 3 21 9" />
            <line x1="10" y1="14" x2="21" y2="3" />
          </svg>
        </a>

        <Button
          full
          disabled={jobAction.isPending}
          onClick={() => act("approve")}
          className="py-[13px] text-[15px]"
        >
          Approve Application
        </Button>

        <div className="mt-2.5 flex gap-2">
          <Button
            variant="secondary"
            disabled={jobAction.isPending}
            onClick={() => act("skip")}
            className="flex-1 py-2.5 text-[13px]"
          >
            Skip
          </Button>
          <Button
            variant="secondary"
            disabled={jobAction.isPending}
            onClick={() => act("save")}
            className="flex-1 py-2.5 text-[13px]"
          >
            Save for later
          </Button>
        </div>
      </div>
    </div>
  );
}
