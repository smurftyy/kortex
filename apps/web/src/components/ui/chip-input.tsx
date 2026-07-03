"use client";

import { useState, type KeyboardEvent } from "react";

interface ChipInputProps {
  id: string;
  value: string[];
  onChange: (next: string[]) => void;
  placeholder: string;
  /** accent = indigo tint chips (design's target-roles pattern); neutral = grey chips. */
  tone?: "accent" | "neutral";
}

const chipTones = {
  accent: "bg-accent-tint text-accent-deep",
  neutral: "bg-chip text-ink-700",
};

export function ChipInput({
  id,
  value,
  onChange,
  placeholder,
  tone = "accent",
}: ChipInputProps) {
  const [query, setQuery] = useState("");

  const handleKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key !== "Enter") return;
    event.preventDefault();
    const next = query.trim();
    if (!next || value.includes(next)) {
      setQuery("");
      return;
    }
    onChange([...value, next]);
    setQuery("");
  };

  return (
    <div>
      {value.length > 0 && (
        <div className="mb-2.5 flex flex-wrap gap-1.5">
          {value.map((item, index) => (
            <span
              key={item}
              className={`flex items-center gap-1.5 rounded-full py-[5px] pl-[11px] pr-1.5 text-[12.5px] font-medium ${chipTones[tone]}`}
            >
              {item}
              <button
                type="button"
                aria-label={`Remove ${item}`}
                onClick={() =>
                  onChange(value.filter((_, i) => i !== index))
                }
                className="flex items-center rounded-full p-0.5 hover:opacity-70 focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
              >
                <svg
                  width="12"
                  height="12"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </span>
          ))}
        </div>
      )}
      <input
        id={id}
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        className="w-full rounded-xl border border-line px-3.5 py-[11px] text-[14px] text-ink-900 placeholder:text-ink-400 focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/20"
      />
    </div>
  );
}
