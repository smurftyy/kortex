import { describe, expect, it } from "vitest";

import { formatLocalTime, relativeTime } from "./format";

const NOW = new Date("2026-07-03T12:00:00Z");

describe("relativeTime", () => {
  it("formats the design's buckets", () => {
    expect(relativeTime("2026-07-03T11:59:40Z", NOW)).toBe("Just now");
    expect(relativeTime("2026-07-03T11:26:00Z", NOW)).toBe("34 min ago");
    expect(relativeTime("2026-07-03T10:00:00Z", NOW)).toBe("2 hr ago");
    expect(relativeTime("2026-07-02T09:00:00Z", NOW)).toBe("Yesterday");
    expect(relativeTime("2026-06-20T09:00:00Z", NOW)).toBe("Jun 20");
  });
});

describe("formatLocalTime", () => {
  it("renders contract HH:MM times as the design's 12-hour labels", () => {
    expect(formatLocalTime("08:00")).toBe("8:00 AM");
    expect(formatLocalTime("15:00")).toBe("3:00 PM");
    expect(formatLocalTime("00:30")).toBe("12:30 AM");
    expect(formatLocalTime("12:00")).toBe("12:00 PM");
  });
});
