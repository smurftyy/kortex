import type { Metadata } from "next";

export const metadata: Metadata = { title: "Tracker — Kortex" };

// Placeholder — the Application Tracker board ships with Phase 4
// (applications endpoints don't exist yet).
export default function TrackerPage() {
  return (
    <div className="px-8 pt-10">
      <h1 className="text-2xl font-bold tracking-[-0.3px] text-ink-900">
        Application Tracker
      </h1>
      <p className="mt-2 text-[14.5px] text-ink-500">
        Tracking begins once you submit your first application.
      </p>
    </div>
  );
}
