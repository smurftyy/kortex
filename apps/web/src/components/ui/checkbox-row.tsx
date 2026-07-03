"use client";

interface CheckboxRowProps {
  label: string;
  checked: boolean;
  onToggle: () => void;
}

/** The design's checkbox row: full-width bordered button with a 16px box. */
export function CheckboxRow({ label, checked, onToggle }: CheckboxRowProps) {
  return (
    <button
      type="button"
      role="checkbox"
      aria-checked={checked}
      onClick={onToggle}
      className="flex w-full items-center gap-2.5 rounded-xl border border-line bg-white px-3.5 py-2.5 text-left focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-accent"
    >
      <span
        className={`flex h-4 w-4 shrink-0 items-center justify-center rounded-[5px] border-[1.5px] ${
          checked ? "border-accent bg-accent" : "border-[#D3D3D0] bg-white"
        }`}
      >
        {checked && (
          <svg
            width="11"
            height="11"
            viewBox="0 0 24 24"
            fill="none"
            stroke="#FFFFFF"
            strokeWidth="3"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <polyline points="20 6 9 17 4 12" />
          </svg>
        )}
      </span>
      <span className="text-[13.5px] text-ink-900">{label}</span>
    </button>
  );
}
