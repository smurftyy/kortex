"use client";

import { useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api/errors";
import { useProfile } from "@/lib/queries/profile";

/**
 * Blocks the dashboard until onboarding is complete. A 404
 * (PROFILE_NOT_FOUND) from GET /auth/me is the "never onboarded" signal
 * per API_CONTRACT_kortex.md; anything else is a real error.
 */
export function OnboardingGate({ children }: { children: ReactNode }) {
  const router = useRouter();
  const { error, isPending, isSuccess, refetch } = useProfile();

  const profileMissing = error instanceof ApiError && error.status === 404;

  useEffect(() => {
    if (profileMissing) router.replace("/onboarding");
  }, [profileMissing, router]);

  if (isSuccess) return <>{children}</>;
  if (isPending || profileMissing) return null;

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-surface px-4 text-center">
      <p className="text-[14.5px] text-ink-500">
        We couldn&rsquo;t load your profile.
      </p>
      <Button
        variant="secondary"
        onClick={() => refetch()}
        className="px-4 py-2 text-[13px]"
      >
        Try again
      </Button>
    </div>
  );
}
