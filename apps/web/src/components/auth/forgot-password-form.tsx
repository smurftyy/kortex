"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { FormError, Label } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { getSupabaseClient } from "@/lib/supabase/client";

export function ForgotPasswordForm() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [sent, setSent] = useState(false);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setPending(true);
    const { error: authError } =
      await getSupabaseClient().auth.resetPasswordForEmail(email, {
        redirectTo: `${window.location.origin}/reset-password`,
      });
    if (authError) {
      setError(authError.message);
      setPending(false);
      return;
    }
    setSent(true);
  };

  if (sent) {
    return (
      <div className="text-center">
        <h1 className="mb-2 text-[20px] font-bold text-ink-900">
          Reset link sent.
        </h1>
        <p className="mx-auto mb-7 max-w-[340px] text-[14.5px] leading-relaxed text-ink-500">
          If an account exists for <strong>{email}</strong>, you&rsquo;ll get an
          email with a link to set a new password.
        </p>
        <Link
          href="/login"
          className="text-[13.5px] font-semibold text-accent hover:text-accent-deep"
        >
          Back to sign in
        </Link>
      </div>
    );
  }

  return (
    <div>
      <h1 className="mb-1.5 text-[26px] font-bold tracking-[-0.3px] text-ink-900">
        Reset your password.
      </h1>
      <p className="mb-8 text-[14.5px] text-ink-500">
        Enter your email and we&rsquo;ll send you a reset link.
      </p>

      <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-[18px]">
        <div>
          <Label htmlFor="email">Email</Label>
          <Input
            id="email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </div>

        <FormError>{error}</FormError>

        <Button type="submit" disabled={pending} full className="py-3 text-[14.5px]">
          {pending ? "Sending…" : "Send reset link"}
        </Button>
      </form>

      <p className="mt-7 text-center text-[13.5px] text-ink-500">
        Remembered it?{" "}
        <Link
          href="/login"
          className="font-semibold text-accent hover:text-accent-deep"
        >
          Sign in
        </Link>
      </p>
    </div>
  );
}
