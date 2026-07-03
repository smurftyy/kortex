"use client";

import { Select } from "@/components/ui/select";
import { BOARDS } from "@/lib/boards";

/**
 * UI state for the filter bar. Not in the design file (the inbox ships
 * without filters there — flagged); built from the design's control
 * vocabulary instead.
 */
export interface FilterUiState {
  board: string;
  location: string;
  stack: string;
  preset: "" | "today" | "week" | "month";
}

export const EMPTY_FILTERS: FilterUiState = {
  board: "",
  location: "",
  stack: "",
  preset: "",
};

const inputClass =
  "rounded-xl border border-line bg-white px-3 py-2 text-[13px] text-ink-900 " +
  "placeholder:text-ink-400 focus:border-accent focus:outline-none " +
  "focus:ring-2 focus:ring-accent/20";

interface FilterBarProps {
  value: FilterUiState;
  onChange: (next: FilterUiState) => void;
}

export function FilterBar({ value, onChange }: FilterBarProps) {
  const active =
    value.board || value.location.trim() || value.stack.trim() || value.preset;

  return (
    <div className="mb-5 flex flex-wrap items-center gap-2">
      <Select
        aria-label="Board"
        value={value.board}
        onChange={(e) => onChange({ ...value, board: e.target.value })}
        className="w-auto py-2 text-[13px]"
      >
        <option value="">All boards</option>
        {BOARDS.map((b) => (
          <option key={b.slug} value={b.slug}>
            {b.label}
          </option>
        ))}
      </Select>

      <input
        aria-label="Location"
        placeholder="Location"
        value={value.location}
        onChange={(e) => onChange({ ...value, location: e.target.value })}
        className={`${inputClass} w-[130px]`}
      />

      <input
        aria-label="Stack"
        placeholder="Stack, e.g. react"
        value={value.stack}
        onChange={(e) => onChange({ ...value, stack: e.target.value })}
        className={`${inputClass} w-[140px]`}
      />

      <Select
        aria-label="Posted"
        value={value.preset}
        onChange={(e) =>
          onChange({
            ...value,
            preset: e.target.value as FilterUiState["preset"],
          })
        }
        className="w-auto py-2 text-[13px]"
      >
        <option value="">Any time</option>
        <option value="today">Today</option>
        <option value="week">Past week</option>
        <option value="month">Past month</option>
      </Select>

      {active && (
        <button
          type="button"
          onClick={() => onChange(EMPTY_FILTERS)}
          className="ml-1 text-[12.5px] font-semibold text-accent hover:text-accent-deep focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
        >
          Clear
        </button>
      )}
    </div>
  );
}

/** Translate UI state into GET /jobs query params (empty → omitted). */
export function toJobsQuery(ui: FilterUiState): {
  board?: string;
  location?: string;
  stack?: string;
  date_from?: string;
} {
  // Day-boundary anchored so the derived query key is stable across
  // renders within the same day (no spurious refetches).
  const startOfDayAgo = (days: number) => {
    const d = new Date();
    d.setDate(d.getDate() - days);
    d.setHours(0, 0, 0, 0);
    return d.toISOString();
  };

  let dateFrom: string | undefined;
  if (ui.preset === "today") dateFrom = startOfDayAgo(0);
  else if (ui.preset === "week") dateFrom = startOfDayAgo(7);
  else if (ui.preset === "month") dateFrom = startOfDayAgo(30);

  return {
    board: ui.board || undefined,
    location: ui.location.trim() || undefined,
    stack: ui.stack.trim() || undefined,
    date_from: dateFrom,
  };
}
