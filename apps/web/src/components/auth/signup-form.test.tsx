import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { SignupForm } from "./signup-form";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
}));

const signUp = vi.fn();
const signInWithOAuth = vi.fn();
vi.mock("@/lib/supabase/client", () => ({
  getSupabaseClient: () => ({
    auth: {
      signUp: (...args: unknown[]) => signUp(...args),
      signInWithOAuth: (...args: unknown[]) => signInWithOAuth(...args),
    },
  }),
}));

beforeEach(() => {
  vi.clearAllMocks();
});

describe("SignupForm", () => {
  it("creates the account and shows the verification-sent state", async () => {
    signUp.mockResolvedValue({ data: { user: { id: "u1" } }, error: null });
    const user = userEvent.setup();
    render(<SignupForm />);

    await user.type(screen.getByLabelText(/email/i), "new@example.com");
    await user.type(screen.getByLabelText(/password/i), "s3cure-pass");
    await user.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() => {
      expect(signUp).toHaveBeenCalledWith({
        email: "new@example.com",
        password: "s3cure-pass",
        options: {
          emailRedirectTo: `${window.location.origin}/auth/callback`,
        },
      });
    });
    expect(await screen.findByText(/check your inbox/i)).toBeInTheDocument();
  });

  it("shows the auth error on failure and keeps the form", async () => {
    signUp.mockResolvedValue({
      data: {},
      error: { message: "User already registered" },
    });
    const user = userEvent.setup();
    render(<SignupForm />);

    await user.type(screen.getByLabelText(/email/i), "dupe@example.com");
    await user.type(screen.getByLabelText(/password/i), "s3cure-pass");
    await user.click(screen.getByRole("button", { name: /create account/i }));

    expect(
      await screen.findByText(/user already registered/i),
    ).toBeInTheDocument();
    expect(screen.queryByText(/check your inbox/i)).not.toBeInTheDocument();
  });
});
