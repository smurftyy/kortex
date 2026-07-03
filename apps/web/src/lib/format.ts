const MINUTE = 60_000;
const HOUR = 60 * MINUTE;

/** "34 min ago" / "2 hr ago" / "Yesterday" / "Jun 20" — the design's buckets. */
export function relativeTime(iso: string, now: Date = new Date()): string {
  const then = new Date(iso);
  const diff = now.getTime() - then.getTime();

  if (diff < MINUTE) return "Just now";
  if (diff < HOUR) return `${Math.floor(diff / MINUTE)} min ago`;

  const startOfDay = (d: Date) =>
    new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
  const dayDelta = Math.round(
    (startOfDay(now) - startOfDay(then)) / (24 * HOUR),
  );

  if (dayDelta === 0) return `${Math.floor(diff / HOUR)} hr ago`;
  if (dayDelta === 1) return "Yesterday";
  return then.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

/** Contract "HH:MM" → the design's 12-hour label ("15:00" → "3:00 PM"). */
export function formatLocalTime(hhmm: string): string {
  const [h, m] = hhmm.split(":").map(Number);
  const period = h < 12 ? "AM" : "PM";
  const hour12 = h % 12 === 0 ? 12 : h % 12;
  return `${hour12}:${String(m).padStart(2, "0")} ${period}`;
}
