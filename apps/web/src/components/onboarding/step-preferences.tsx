"use client";

import { ChipInput } from "@/components/ui/chip-input";
import { CheckboxRow } from "@/components/ui/checkbox-row";
import { Label } from "@/components/ui/field";
import { Select } from "@/components/ui/select";
import { BOARDS } from "@/lib/boards";

import type { OnboardingData } from "./onboarding-flow";

// Design's scan-time options mapped to the contract's HH:MM format.
const SCAN_TIMES = [
  { value: "06:00", label: "6:00 AM" },
  { value: "08:00", label: "8:00 AM" },
  { value: "10:00", label: "10:00 AM" },
  { value: "15:00", label: "3:00 PM" },
  { value: "18:00", label: "6:00 PM" },
];

interface StepProps {
  data: OnboardingData;
  onPatch: (partial: Partial<OnboardingData>) => void;
}

export function StepPreferences({ data, onPatch }: StepProps) {
  const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;

  const toggleBoard = (slug: string) => {
    const next = data.boards.includes(slug)
      ? data.boards.filter((b) => b !== slug)
      : BOARDS.map((b) => b.slug).filter(
          (s) => data.boards.includes(s) || s === slug,
        );
    onPatch({ boards: next });
  };

  return (
    <div>
      <h1 className="mb-1.5 text-[26px] font-bold tracking-[-0.3px] text-ink-900">
        A few search preferences.
      </h1>
      <p className="mb-7 text-[14.5px] text-ink-500">
        This controls exactly what we scan for and when.
      </p>

      <div className="mb-[22px]">
        <Label htmlFor="target-roles" className="mb-2">
          Target roles
        </Label>
        <ChipInput
          id="target-roles"
          value={data.targetRoles}
          onChange={(targetRoles) => onPatch({ targetRoles })}
          placeholder="Type a role and press Enter"
          tone="accent"
        />
      </div>

      <div className="mb-[22px]">
        <Label htmlFor="locations" className="mb-2">
          Locations
        </Label>
        <ChipInput
          id="locations"
          value={data.locations}
          onChange={(locations) => onPatch({ locations })}
          placeholder="Type a location and press Enter"
          tone="neutral"
        />
        <p className="mt-1.5 text-[12.5px] text-ink-400">
          e.g. remote, lagos, nigeria &mdash; jobs matching any of these pass
          the filter.
        </p>
      </div>

      <div className="mb-[22px]">
        <Label className="mb-2">Job boards to monitor</Label>
        <div className="flex flex-col gap-2">
          {BOARDS.map((board) => (
            <CheckboxRow
              key={board.slug}
              label={board.label}
              checked={data.boards.includes(board.slug)}
              onToggle={() => toggleBoard(board.slug)}
            />
          ))}
        </div>
      </div>

      <div className="mb-[22px]">
        <Label htmlFor="excluded-keywords" className="mb-2">
          Excluded keywords{" "}
          <span className="font-normal text-ink-400">(optional)</span>
        </Label>
        <ChipInput
          id="excluded-keywords"
          value={data.excludedKeywords}
          onChange={(excludedKeywords) => onPatch({ excludedKeywords })}
          placeholder="Type a keyword and press Enter"
          tone="neutral"
        />
        <p className="mt-1.5 text-[12.5px] text-ink-400">
          Listings containing these words are skipped &mdash; e.g. senior,
          staff.
        </p>
      </div>

      <div>
        <Label htmlFor="scan-time">Daily scan time</Label>
        <Select
          id="scan-time"
          value={data.scanTime}
          onChange={(e) => onPatch({ scanTime: e.target.value })}
        >
          {SCAN_TIMES.map((t) => (
            <option key={t.value} value={t.value}>
              {t.label}
            </option>
          ))}
        </Select>
        <p className="mt-1.5 text-[12.5px] text-ink-400">
          Times are in {timezone}.
        </p>
      </div>
    </div>
  );
}
