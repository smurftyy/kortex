"use client";

import { forwardRef, type SelectHTMLAttributes } from "react";

export const Select = forwardRef<
  HTMLSelectElement,
  SelectHTMLAttributes<HTMLSelectElement>
>(function Select({ className = "", ...props }, ref) {
  return (
    <select
      ref={ref}
      className={
        "w-full rounded-xl border border-line bg-white px-3.5 py-[11px] " +
        "text-[14px] text-ink-900 focus:border-accent focus:outline-none " +
        "focus:ring-2 focus:ring-accent/20 " +
        className
      }
      {...props}
    />
  );
});
