import { useSyncExternalStore } from "react";

/**
 * Session-level set of job ids the user has approved/skipped/saved.
 *
 * Needed because the public GET /jobs carries no per-user match status
 * (flagged contract gap): after a successful action we invalidate and
 * refetch the feed, and without this filter the acted-on job would
 * reappear. Lives for the browser session only — acted jobs resurface
 * after a full reload until a personalized feed endpoint exists.
 */
const acted = new Set<string>();
const listeners = new Set<() => void>();
let snapshot: ReadonlySet<string> = new Set();

function emit() {
  snapshot = new Set(acted);
  listeners.forEach((listener) => listener());
}

export function markActed(jobId: string): void {
  acted.add(jobId);
  emit();
}

export function unmarkActed(jobId: string): void {
  acted.delete(jobId);
  emit();
}

export function _resetActedJobs(): void {
  acted.clear();
  emit();
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function useActedJobs(): ReadonlySet<string> {
  return useSyncExternalStore(
    subscribe,
    () => snapshot,
    () => snapshot,
  );
}
