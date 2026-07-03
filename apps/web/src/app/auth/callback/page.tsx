"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { useAuth } from "@/providers/auth-provider";

/**
 * Landing point for OAuth and email-verification redirects. supabase-js
 * (detectSessionInUrl) consumes the tokens from the URL; we just wait for
 * the session to appear, then hand off to the app.
 */
export default function AuthCallbackPage() {
  const router = useRouter();
  const { session, isLoading } = useAuth();
  const [timedOut, setTimedOut] = useState(false);

  useEffect(() => {
    if (session) router.replace("/");
  }, [session, router]);

  useEffect(() => {
    const timer = setTimeout(() => setTimedOut(true), 8000);
    return () => clearTimeout(timer);
  }, []);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-surface px-4">
      {!isLoading && !session && timedOut ? (
        <div className="text-center">
          <p className="mb-4 text-[14.5px] text-ink-500">
            We couldn&rsquo;t finish signing you in.
          </p>
          <Link
            href="/login"
            className="text-[13.5px] font-semibold text-accent hover:text-accent-deep"
          >
            Back to sign in
          </Link>
        </div>
      ) : (
        <p className="text-[14.5px] text-ink-500">Signing you in…</p>
      )}
    </div>
  );
}
