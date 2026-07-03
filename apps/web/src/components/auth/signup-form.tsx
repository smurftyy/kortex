"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";

import { GoogleButton } from "@/components/auth/google-button";
import { Button } from "@/components/ui/button";
import { FormError, Label } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { getSupabaseClient } from "@/lib/supabase/client";

export function SignupForm() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [sent, setSent] = useState(false);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setPending(true);
    const { error: authError } = await getSupabaseClient().auth.signUp({
      email,
      password,
      options: {
        emailRedirectTo: `${window.location.origin}/auth/callback`,
      },
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
        <div className="mx-auto mb-5 flex h-[52px] w-[52px] items-center justify-center rounded-full bg-success-tint text-success">
          <svg
            width="26"
            height="26"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
            <polyline points="22 4 12 14.01 9 11.01" />
          </svg>
        </div>
        <h1 className="mb-2 text-[20px] font-bold text-ink-900">
          Check your inbox.
        </h1>
        <p className="mx-auto max-w-[340px] text-[14.5px] leading-relaxed text-ink-500">
          We sent a verification link to <strong>{email}</strong>. Follow it to
          finish creating your account.
        </p>
      </div>
    );
  }

  return (
    <div>
      <h1 className="mb-1.5 text-[26px] font-bold tracking-[-0.3px] text-ink-900">
        Create your account.
      </h1>
      <p className="mb-8 text-[14.5px] text-ink-500">
        Kortex finds and prepares opportunities. You approve every step.
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
        <div>
          <Label htmlFor="password">Password</Label>
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
          {pending ? "Creating account…" : "Create account"}
        </Button>
      </form>

      <div className="my-5 flex items-center gap-3">
        <span className="h-px flex-1 bg-line-soft" />
        <span className="text-[12.5px] text-ink-400">or</span>
        <span className="h-px flex-1 bg-line-soft" />
      </div>

      <GoogleButton onError={setError} />

      <p className="mt-7 text-center text-[13.5px] text-ink-500">
        Already have an account?{" "}
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
