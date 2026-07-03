"use client";

import { forwardRef, type InputHTMLAttributes } from "react";

export const Input = forwardRef<
  HTMLInputElement,
  InputHTMLAttributes<HTMLInputElement>
>(function Input({ className = "", ...props }, ref) {
  return (
    <input
      ref={ref}
      className={
        "w-full rounded-xl border border-line px-3.5 py-[11px] text-[14.5px] " +
        "text-ink-900 placeholder:text-ink-400 focus:border-accent " +
        "focus:outline-none focus:ring-2 focus:ring-accent/20 " +
        className
      }
      {...props}
    />
  );
});
