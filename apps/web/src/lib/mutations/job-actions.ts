import {
  useMutation,
  useQueryClient,
  type InfiniteData,
} from "@tanstack/react-query";

import { markActed, unmarkActed } from "@/lib/acted-jobs";
import { actOnJob } from "@/lib/api/endpoints";
import { ApiError } from "@/lib/api/errors";
import type {
  JobListItem,
  JobListResponse,
  MatchAction,
} from "@/lib/api/types";
import { useToast } from "@/providers/toast-provider";

interface JobActionVariables {
  job: JobListItem;
  action: MatchAction;
}

type FeedCache = InfiniteData<JobListResponse> | JobListResponse | undefined;

function stripJob(page: JobListResponse, jobId: string): JobListResponse {
  return {
    ...page,
    results: page.results.filter((job) => job.job_id !== jobId),
    total: Math.max(0, page.total - 1),
  };
}

function withoutJob(cache: FeedCache, jobId: string): FeedCache {
  if (!cache) return cache;
  if ("pages" in cache) {
    return { ...cache, pages: cache.pages.map((p) => stripJob(p, jobId)) };
  }
  return stripJob(cache, jobId);
}

// Design copy for the success toasts.
function successToast(action: MatchAction, job: JobListItem): string {
  switch (action) {
    case "approve":
      return `Approved — preparing application materials for ${job.company}.`;
    case "save":
      return "Saved for later.";
    case "skip":
      return "Skipped.";
  }
}

/**
 * The core interaction loop (3.8): optimistic cache update on click,
 * rollback on error, invalidate/refetch on success. The acted-jobs set
 * keeps refetched public-feed copies of acted jobs hidden.
 */
export function useJobAction() {
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  return useMutation({
    mutationFn: ({ job, action }: JobActionVariables) =>
      actOnJob(job.job_id, action),

    onMutate: async ({ job }) => {
      await queryClient.cancelQueries({ queryKey: ["jobs"] });
      const snapshots = queryClient.getQueriesData<FeedCache>({
        queryKey: ["jobs"],
      });
      queryClient.setQueriesData<FeedCache>({ queryKey: ["jobs"] }, (old) =>
        withoutJob(old, job.job_id),
      );
      markActed(job.job_id);
      return { snapshots };
    },

    onError: (error, { job }, context) => {
      context?.snapshots.forEach(([key, data]) =>
        queryClient.setQueryData(key, data),
      );
      unmarkActed(job.job_id);
      if (error instanceof ApiError && error.code === "MATCH_NOT_FOUND") {
        showToast(
          "We couldn't update this one — it hasn't been matched to your profile yet.",
        );
      } else {
        showToast("Something went wrong — the card is back in your inbox.");
      }
    },

    onSuccess: (_, { job, action }) => {
      showToast(successToast(action, job));
      void queryClient.invalidateQueries({ queryKey: ["jobs"] });
    },
  });
}
