"use client";

import type { JobListItem, MatchAction } from "@/lib/api/types";
import { boardLabel } from "@/lib/boards";
import { relativeTime } from "@/lib/format";

export interface JobCardProps {
  job: JobListItem;
  onAction?: (job: JobListItem, action: MatchAction) => void;
  onOpen?: (job: JobListItem) => void;
  /** Dim + disable while a mutation for this card is in flight. */
  busy?: boolean;
}

/**
 * The design's inbox card. Its match-% slot has no data source — the
 * public GET /jobs carries no job_matches fields (flagged contract gap) —
 * so the right edge shows the source board and the "Matches:" line is
 * replaced by stack tags.
 */
export function JobCard({ job, onAction, onOpen, busy }: JobCardProps) {
  const isRemote = (job.location ?? "").toLowerCase().includes("remote");

  const actionButton = (
    action: MatchAction,
    label: string,
    icon: React.ReactNode,
    primary = false,
  ) => (
    <button
      type="button"
      disabled={busy}
      onClick={(e) => {
        e.stopPropagation();
        onAction?.(job, action);
      }}
      className={`flex items-center gap-[5px] rounded-xl px-3 py-[7px] text-[13px] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-accent disabled:opacity-50 ${
        primary
          ? "bg-accent px-3.5 font-semibold text-white hover:bg-accent-deep"
          : "border border-line bg-white font-medium text-ink-600 hover:bg-raised"
      }`}
    >
      {icon}
      {label}
    </button>
  );

  return (
    <article
      onClick={() => onOpen?.(job)}
      className={`rounded-xl border border-line bg-white px-[22px] py-5 shadow-card ${
        onOpen ? "cursor-pointer" : ""
      } ${busy ? "opacity-60" : ""}`}
    >
      <div className="mb-1.5 flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h3 className="mb-[3px] text-[17px] font-semibold text-ink-900">
            {onOpen ? (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onOpen(job);
                }}
                className="text-left hover:text-accent-deep focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
              >
                {job.title}
              </button>
            ) : (
              job.title
            )}
          </h3>
          <div className="flex items-center gap-2 text-[13.5px] text-ink-500">
            <span className="truncate">
              {job.company}
              {job.location ? ` · ${job.location}` : ""}
            </span>
            {isRemote && (
              <span className="shrink-0 rounded-full bg-chip px-2 py-0.5 text-[11px] font-semibold text-ink-600">
                Remote
              </span>
            )}
          </div>
        </div>
      </div>

      {job.stack_tags.length > 0 && (
        <div className="mb-3 mt-2 flex flex-wrap gap-1.5">
          {job.stack_tags.slice(0, 6).map((tag) => (
            <span
              key={tag}
              className="rounded-full bg-chip px-2 py-0.5 text-[11.5px] font-medium text-ink-600"
            >
              {tag}
            </span>
          ))}
        </div>
      )}

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3 text-[12.5px] text-ink-400">
          <span>
            Discovered {relativeTime(job.discovered_at)} &middot; via{" "}
            {boardLabel(job.source_board)}
          </span>
        </div>
        <div className="flex items-center gap-2">
          {actionButton(
            "skip",
            "Skip",
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.75"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>,
          )}
          {actionButton(
            "save",
            "Save",
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.75"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" />
            </svg>,
          )}
          {actionButton(
            "approve",
            "Approve",
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
              <polyline points="20 6 9 17 4 12" />
            </svg>,
            true,
          )}
        </div>
      </div>
    </article>
  );
}
