import type { LabelHTMLAttributes, ReactNode } from "react";

export function Label({
  className = "",
  ...props
}: LabelHTMLAttributes<HTMLLabelElement>) {
  return (
    // eslint-disable-next-line jsx-a11y/label-has-associated-control
    <label
      className={`mb-1.5 block text-[13px] font-semibold text-ink-700 ${className}`}
      {...props}
    />
  );
}

export function FormError({ children }: { children: ReactNode }) {
  if (!children) return null;
  return (
    <p
      role="alert"
      className="rounded-xl border border-danger-line bg-danger-tint px-3.5 py-2.5 text-[13px] font-medium text-danger"
    >
      {children}
    </p>
  );
}
