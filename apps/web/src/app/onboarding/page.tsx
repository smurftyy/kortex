import type { Metadata } from "next";

import { RequireAuth } from "@/components/auth/guards";
import { OnboardingFlow } from "@/components/onboarding/onboarding-flow";

export const metadata: Metadata = { title: "Set up — Kortex" };

export default function OnboardingPage() {
  return (
    <RequireAuth>
      <div className="min-h-screen bg-surface">
        <div className="mx-auto max-w-[560px] px-10 pb-[100px] pt-14">
          <OnboardingFlow />
        </div>
      </div>
    </RequireAuth>
  );
}
