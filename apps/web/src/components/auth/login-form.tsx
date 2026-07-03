"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { GoogleButton } from "@/components/auth/google-button";
import { Button } from "@/components/ui/button";
import { FormError, Label } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { getSupabaseClient } from "@/lib/supabase/client";

export function LoginForm() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setPending(true);
    const { error: authError } =
      await getSupabaseClient().auth.signInWithPassword({ email, password });
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
        Welcome back.
      </h1>
      <p className="mb-8 text-[14.5px] text-ink-500">
        Sign in to pick up where you left off.
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
          <div className="flex items-baseline justify-between">
            <Label htmlFor="password">Password</Label>
            <Link
              href="/forgot-password"
              className="text-[12.5px] font-semibold text-accent hover:text-accent-deep"
            >
              Forgot password?
            </Link>
          </div>
          <Input
            id="password"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>

        <FormError>{error}</FormError>

        <Button type="submit" disabled={pending} full className="py-3 text-[14.5px]">
          {pending ? "Signing in…" : "Sign in"}
        </Button>
      </form>

      <div className="my-5 flex items-center gap-3">
        <span className="h-px flex-1 bg-line-soft" />
        <span className="text-[12.5px] text-ink-400">or</span>
        <span className="h-px flex-1 bg-line-soft" />
      </div>

      <GoogleButton onError={setError} />

      <p className="mt-7 text-center text-[13.5px] text-ink-500">
        New to Kortex?{" "}
        <Link
          href="/signup"
          className="font-semibold text-accent hover:text-accent-deep"
        >
          Create an account
        </Link>
      </p>
    </div>
  );
}
