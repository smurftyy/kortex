"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { FormError, Label } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { getSupabaseClient } from "@/lib/supabase/client";

/**
 * Rendered after the user follows the recovery link from their email —
 * Supabase's session listener has already exchanged the link for a
 * (recovery) session, so updateUser sets the new password directly.
 */
export function ResetPasswordForm() {
  const router = useRouter();
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setPending(true);
    const { error: authError } = await getSupabaseClient().auth.updateUser({
      password,
    });
    if (authError) {
      setError(authError.message);
      setPending(false);
      return;
    }
    router.replace("/");
  };

  return (
    <div>
      <h1 className="mb-1.5 text-[26px] font-bold tracking-[-0.3px] text-ink-900">
        Set a new password.
      </h1>
      <p className="mb-8 text-[14.5px] text-ink-500">
        You&rsquo;re signed in through your reset link — choose a new password
        to finish.
      </p>

      <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-[18px]">
        <div>
          <Label htmlFor="password">New password</Label>
          <Input
            id="password"
            type="password"
            autoComplete="new-password"
            required
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <p className="mt-1.5 text-[12.5px] text-ink-400">
            At least 8 characters.
          </p>
        </div>

        <FormError>{error}</FormError>

        <Button type="submit" disabled={pending} full className="py-3 text-[14.5px]">
          {pending ? "Saving…" : "Save password"}
        </Button>
      </form>
    </div>
  );
}
