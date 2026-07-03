"use client";

import { Button } from "@/components/ui/button";
import { JobCard } from "@/components/jobs/job-card";
import { formatLocalTime } from "@/lib/format";
import { useJobsFeed, usePreferences } from "@/lib/queries/jobs";

function greeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning.";
  if (hour < 18) return "Good afternoon.";
  return "Good evening.";
}

export function InboxScreen() {
  // Filter state arrives with the filter bar (3.7); {} = unfiltered feed.
  const filters = {};
  const feed = useJobsFeed(filters);
  const { data: prefs } = usePreferences();

  const jobs = feed.data?.pages.flatMap((p) => p.results) ?? [];
  const total = feed.data?.pages[0]?.total ?? 0;
  const nextScan = prefs ? formatLocalTime(prefs.digest_time_local) : null;

  return (
    <div className="mx-auto max-w-[720px] px-10 pb-20 pt-14">
      <div className="mb-1.5 flex items-start justify-between">
        <h1 className="text-[30px] font-bold tracking-[-0.4px] text-ink-900">
          {greeting()}
        </h1>
        {prefs && (
          <div className="flex items-center gap-1.5 pt-2 text-[12.5px] text-ink-400">
            <svg
              width="13"
              height="13"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.75"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <circle cx="12" cy="12" r="10" />
              <polyline points="12 6 12 12 16 14" />
            </svg>
            <span>
              {prefs.boards_enabled.length} boards monitored &middot; next scan
              at {nextScan}
            </span>
          </div>
        )}
      </div>

      {total > 0 && (
        <p className="mb-9 text-[15px] text-ink-500">
          {total} {total === 1 ? "opportunity" : "opportunities"} discovered
          &mdash; newest first.
        </p>
      )}

      {feed.isPending && (
        <div className="mt-9 flex flex-col gap-3.5" aria-hidden="true">
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className="h-[120px] animate-pulse rounded-xl border border-line bg-white"
            />
          ))}
        </div>
      )}

      {feed.isError && (
        <div className="mt-16 flex flex-col items-center gap-4 text-center">
          <p className="text-[14.5px] text-ink-500">
            We couldn&rsquo;t load your inbox.
          </p>
          <Button
            variant="secondary"
            onClick={() => feed.refetch()}
            className="px-4 py-2 text-[13px]"
          >
            Try again
          </Button>
        </div>
      )}

      {feed.isSuccess && jobs.length === 0 && (
        <div
          className="flex flex-col items-center px-5 py-[90px] text-center"
          style={{ animation: "fadeIn 0.3s ease-out" }}
        >
          <div className="mb-5 flex h-[52px] w-[52px] items-center justify-center rounded-full bg-success-tint text-success">
            <svg
              width="26"
              height="26"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
              <polyline points="22 4 12 14.01 9 11.01" />
            </svg>
          </div>
          <h2 className="mb-2 text-[20px] font-bold text-ink-900">
            You&rsquo;re caught up.
          </h2>
          <p className="max-w-[340px] text-[14.5px] leading-relaxed text-ink-500">
            {nextScan
              ? `We'll notify you after the next scheduled search, at ${nextScan}.`
              : "We'll notify you after the next scheduled search."}
          </p>
        </div>
      )}

      {jobs.length > 0 && (
        <div className="flex flex-col gap-3.5">
          {jobs.map((job) => (
            <JobCard key={job.job_id} job={job} />
          ))}
        </div>
      )}

      {feed.hasNextPage && (
        <div className="mt-6 flex justify-center">
          <Button
            variant="secondary"
            onClick={() => feed.fetchNextPage()}
            disabled={feed.isFetchingNextPage}
            className="px-4 py-2 text-[13px]"
          >
            {feed.isFetchingNextPage ? "Loading…" : "Load more"}
          </Button>
        </div>
      )}
    </div>
  );
}
