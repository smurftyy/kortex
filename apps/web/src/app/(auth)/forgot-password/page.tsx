import type { Metadata } from "next";

import { ForgotPasswordForm } from "@/components/auth/forgot-password-form";

export const metadata: Metadata = { title: "Reset password — Kortex" };

export default function ForgotPasswordPage() {
  return <ForgotPasswordForm />;
}
