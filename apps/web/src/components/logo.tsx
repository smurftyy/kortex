export function Logo() {
  return (
    <div className="flex items-center gap-2">
      <div className="flex h-[26px] w-[26px] shrink-0 items-center justify-center rounded-lg bg-accent">
        <svg
          width="15"
          height="15"
          viewBox="0 0 24 24"
          fill="none"
          stroke="#FFFFFF"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <path d="M13 2 3 14h7l-1 8 10-12h-7l1-8z" />
        </svg>
      </div>
      <span className="text-[15px] font-bold tracking-[-0.2px] text-ink-900">
        Kortex
      </span>
    </div>
  );
}
