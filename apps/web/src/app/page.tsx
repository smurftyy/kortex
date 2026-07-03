import { RequireAuth } from "@/components/auth/guards";
import { OnboardingGate } from "@/components/onboarding/onboarding-gate";

export default function Home() {
  return (
    <RequireAuth>
      <OnboardingGate>
        <main className="flex min-h-screen items-center justify-center bg-surface">
          <p className="text-sm text-ink-400">
            Kortex — dashboard lands in the next commit.
          </p>
        </main>
      </OnboardingGate>
    </RequireAuth>
  );
}
