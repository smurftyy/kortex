"use client";

import { useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";

import { useAuth } from "@/providers/auth-provider";

/**
 * Client-side route guard: renders children only with a live session,
 * otherwise redirects to /login once the initial session read settles.
 * (RLS on the backend remains the real enforcement boundary.)
 */
export function RequireAuth({ children }: { children: ReactNode }) {
  const router = useRouter();
  const { session, isLoading } = useAuth();

  useEffect(() => {
    if (!isLoading && !session) router.replace("/login");
  }, [isLoading, session, router]);

  if (isLoading || !session) return null;
  return <>{children}</>;
}

/** Inverse guard for auth pages — signed-in users go straight to the app. */
export function RedirectIfAuthed({ children }: { children: ReactNode }) {
  const router = useRouter();
  const { session, isLoading } = useAuth();

  useEffect(() => {
    if (!isLoading && session) router.replace("/");
  }, [isLoading, session, router]);

  if (isLoading || session) return null;
  return <>{children}</>;
}
