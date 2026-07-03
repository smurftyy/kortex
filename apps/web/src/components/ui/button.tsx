"use client";

import { forwardRef, type ButtonHTMLAttributes } from "react";

type Variant = "primary" | "secondary" | "ghost";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  full?: boolean;
}

const base =
  "inline-flex items-center justify-center gap-1.5 rounded-xl font-medium " +
  "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 " +
  "focus-visible:outline-accent disabled:cursor-not-allowed transition-colors";

const variants: Record<Variant, string> = {
  primary:
    "bg-accent text-white font-semibold hover:bg-accent-deep " +
    "disabled:bg-chip disabled:text-ink-400",
  secondary:
    "border border-line bg-white text-ink-600 hover:bg-raised " +
    "disabled:text-ink-400",
  ghost: "bg-transparent text-ink-500 hover:text-ink-700",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  function Button({ variant = "primary", full, className = "", ...props }, ref) {
    return (
      <button
        ref={ref}
        className={`${base} ${variants[variant]} ${full ? "w-full" : ""} ${className}`}
        {...props}
      />
    );
  },
);
