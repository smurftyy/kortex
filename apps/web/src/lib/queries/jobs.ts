import { useInfiniteQuery, useQuery } from "@tanstack/react-query";

import { getJobs, getPreferences } from "@/lib/api/endpoints";
import type { JobsQuery } from "@/lib/api/types";

const PAGE_SIZE = 20;

/**
 * Paged feed under the namespaced key ['jobs', filters] — each filter
 * combination caches its own pages.
 */
export function useJobsFeed(filters: Omit<JobsQuery, "page" | "page_size">) {
  return useInfiniteQuery({
    queryKey: ["jobs", filters],
    queryFn: ({ pageParam }) =>
      getJobs({ ...filters, page: pageParam, page_size: PAGE_SIZE }),
    initialPageParam: 1,
    getNextPageParam: (last) =>
      last.page * last.page_size < last.total ? last.page + 1 : undefined,
  });
}

/** Lightweight total for the sidebar badge (1-item page, 60s fresh). */
export function useJobsCount() {
  return useQuery({
    queryKey: ["jobs", "count"],
    queryFn: () => getJobs({ page: 1, page_size: 1 }),
    select: (data) => data.total,
    staleTime: 60_000,
  });
}

export function usePreferences() {
  return useQuery({
    queryKey: ["preferences"],
    queryFn: () => getPreferences(),
  });
}
