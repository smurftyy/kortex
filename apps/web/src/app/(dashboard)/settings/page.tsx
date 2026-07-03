import type { Metadata } from "next";

export const metadata: Metadata = { title: "Settings — Kortex" };

// Placeholder — the full settings screens (General/Automation/…) ship in a
// later phase.
export default function SettingsPage() {
  return (
    <div className="px-8 pt-10">
      <h1 className="text-2xl font-bold tracking-[-0.3px] text-ink-900">
        Settings
      </h1>
      <p className="mt-2 text-[14.5px] text-ink-500">
        You can change your profile and preferences here in a later phase.
      </p>
    </div>
  );
}
