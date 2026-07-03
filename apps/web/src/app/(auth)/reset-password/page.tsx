import type { Metadata } from "next";

import { ResetPasswordForm } from "@/components/auth/reset-password-form";

export const metadata: Metadata = { title: "Set new password — Kortex" };

export default function ResetPasswordPage() {
  return <ResetPasswordForm />;
}
