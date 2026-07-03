import type { ReactNode } from "react";

import { Logo } from "@/components/logo";

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-surface px-4 py-10">
      <div className="mb-8">
        <Logo />
      </div>
      <div className="w-full max-w-[400px] rounded-2xl border border-line bg-white p-8 shadow-card">
        {children}
      </div>
    </div>
  );
}
