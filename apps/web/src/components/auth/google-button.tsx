"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { getSupabaseClient } from "@/lib/supabase/client";

export function GoogleButton({ onError }: { onError: (msg: string) => void }) {
  const [pending, setPending] = useState(false);

  const handleClick = async () => {
    setPending(true);
    const { error } = await getSupabaseClient().auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: `${window.location.origin}/auth/callback` },
    });
    // On success the browser navigates away; we only ever see errors.
    if (error) {
      onError(error.message);
      setPending(false);
    }
  };

  return (
    <Button
      type="button"
      variant="secondary"
      full
      disabled={pending}
      onClick={handleClick}
      className="py-[11px] text-[14px] text-ink-700"
    >
      <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true">
        <path
          fill="#4285F4"
          d="M23.5 12.27c0-.85-.08-1.66-.22-2.45H12v4.64h6.46a5.53 5.53 0 0 1-2.4 3.62v3h3.88c2.27-2.1 3.56-5.18 3.56-8.81z"
        />
        <path
          fill="#34A853"
          d="M12 24c3.24 0 5.96-1.07 7.94-2.91l-3.88-3c-1.08.72-2.45 1.15-4.06 1.15-3.13 0-5.78-2.11-6.72-4.95H1.27v3.1A12 12 0 0 0 12 24z"
        />
        <path
          fill="#FBBC05"
          d="M5.28 14.29a7.2 7.2 0 0 1 0-4.58v-3.1H1.27a12 12 0 0 0 0 10.78l4.01-3.1z"
        />
        <path
          fill="#EA4335"
          d="M12 4.76c1.76 0 3.34.6 4.59 1.8l3.44-3.44A11.97 11.97 0 0 0 12 0 12 12 0 0 0 1.27 6.61l4.01 3.1C6.22 6.87 8.87 4.76 12 4.76z"
        />
      </svg>
      Continue with Google
    </Button>
  );
}
