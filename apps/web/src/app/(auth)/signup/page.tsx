import type { Metadata } from "next";

import { RedirectIfAuthed } from "@/components/auth/guards";
import { SignupForm } from "@/components/auth/signup-form";

export const metadata: Metadata = { title: "Create account — Kortex" };

export default function SignupPage() {
  return (
    <RedirectIfAuthed>
      <SignupForm />
    </RedirectIfAuthed>
  );
}
