import type { ReactNode } from "react";

import { RequireAuth } from "@/components/auth/guards";
import { Sidebar } from "@/components/dashboard/sidebar";
import { OnboardingGate } from "@/components/onboarding/onboarding-gate";
import { ToastProvider } from "@/providers/toast-provider";

export default function DashboardLayout({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <RequireAuth>
      <OnboardingGate>
        <ToastProvider>
          <div className="flex h-screen bg-white">
            <Sidebar />
            <main className="relative min-w-0 flex-1 overflow-y-auto bg-surface">
              {children}
            </main>
          </div>
        </ToastProvider>
      </OnboardingGate>
    </RequireAuth>
  );
}
