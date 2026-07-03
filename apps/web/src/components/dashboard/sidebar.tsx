"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { Logo } from "@/components/logo";
import { useJobsCount } from "@/lib/queries/jobs";
import { useProfile } from "@/lib/queries/profile";

function NavLink({
  href,
  active,
  icon,
  label,
  badge,
}: {
  href: string;
  active: boolean;
  icon: ReactNode;
  label: string;
  badge?: number;
}) {
  return (
    <Link
      href={href}
      aria-current={active ? "page" : undefined}
      className={`mb-0.5 flex items-center gap-2.5 rounded-[10px] px-2.5 py-[9px] text-[14px] font-medium focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent ${
        active
          ? "bg-accent-tint text-accent-deep"
          : "text-ink-600 hover:bg-chip/60"
      }`}
    >
      {icon}
      <span className="flex-1">{label}</span>
      {badge !== undefined && badge > 0 && (
        <span className="min-w-2 rounded-full bg-accent-tint px-[7px] py-px text-center text-[11px] font-semibold text-accent-deep">
          {badge}
        </span>
      )}
    </Link>
  );
}

function initialsOf(name: string): string {
  const parts = name.trim().split(/\s+/);
  return ((parts[0]?.[0] ?? "") + (parts[1]?.[0] ?? "")).toUpperCase();
}

export function Sidebar() {
  const pathname = usePathname();
  const { data: profile } = useProfile();
  const { data: inboxCount } = useJobsCount();

  return (
    <div className="flex w-[232px] shrink-0 flex-col border-r border-line-soft bg-raised px-3.5 py-5">
      <div className="flex items-center gap-2 px-2 pb-6 pt-1.5">
        <Logo />
      </div>

      <nav aria-label="Main">
        <NavLink
          href="/"
          active={pathname === "/"}
          label="Inbox"
          badge={inboxCount}
          icon={
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.75"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="M22 12h-6l-2 3h-4l-2-3H2" />
              <path d="M5.45 5.11L2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z" />
            </svg>
          }
        />
        <NavLink
          href="/tracker"
          active={pathname === "/tracker"}
          label="Tracker"
          icon={
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.75"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <rect x="3" y="4" width="5" height="16" rx="1" />
              <rect x="10" y="4" width="5" height="10" rx="1" />
              <rect x="17" y="4" width="4" height="13" rx="1" />
            </svg>
          }
        />
      </nav>

      <div className="flex-1" />

      <NavLink
        href="/settings"
        active={pathname === "/settings"}
        label="Settings"
        icon={
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.75"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <circle cx="12" cy="12" r="3" />
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
          </svg>
        }
      />

      <Link
        href="/settings"
        className="mt-1 flex items-center gap-[9px] border-t border-line-soft p-2 pt-4 focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
      >
        <div className="flex h-[26px] w-[26px] shrink-0 items-center justify-center rounded-full bg-[#E4E4F5] text-[11px] font-semibold text-accent-deep">
          {profile ? initialsOf(profile.full_name) : "·"}
        </div>
        <div className="truncate text-[13px] font-medium text-ink-600">
          {profile?.full_name ?? ""}
        </div>
      </Link>
    </div>
  );
}
