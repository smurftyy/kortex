"use client";

import { useState, type KeyboardEvent } from "react";

import type { OnboardingData } from "./onboarding-flow";

// Skill groups exactly as the design file defines them.
const SKILL_GROUPS = [
  {
    label: "Languages",
    items: ["JavaScript", "Python", "TypeScript", "Java", "C++", "Go"],
  },
  {
    label: "Frameworks",
    items: ["React", "Node.js", "Django", "Spring", "Next.js"],
  },
  {
    label: "Tools",
    items: ["Git", "Docker", "PostgreSQL", "AWS", "Figma"],
  },
];

interface StepProps {
  data: OnboardingData;
  onPatch: (partial: Partial<OnboardingData>) => void;
}

export function StepSkills({ data, onPatch }: StepProps) {
  const [query, setQuery] = useState("");
  const q = query.trim().toLowerCase();

  const toggle = (skill: string) => {
    onPatch({
      skills: data.skills.includes(skill)
        ? data.skills.filter((s) => s !== skill)
        : [...data.skills, skill],
    });
  };

  // The design only offers curated chips; Enter-to-add covers skills
  // outside the curated list since `profiles.skills` is free text.
  const handleSearchKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key !== "Enter") return;
    event.preventDefault();
    const custom = query.trim();
    if (!custom) return;
    if (!data.skills.includes(custom)) {
      onPatch({ skills: [...data.skills, custom] });
    }
    setQuery("");
  };

  return (
    <div>
      <h1 className="mb-1.5 text-[26px] font-bold tracking-[-0.3px] text-ink-900">
        What are your skills?
      </h1>
      <p className="mb-5 text-[14.5px] text-ink-500">
        Select what applies. This drives how we score matches &mdash; not a
        black box, just a checklist.
      </p>

      <div className="mb-5 flex items-center gap-2 rounded-xl border border-line bg-white px-3.5 py-2.5">
        <svg
          width="15"
          height="15"
          viewBox="0 0 24 24"
          fill="none"
          stroke="#9A9A96"
          strokeWidth="1.75"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <circle cx="11" cy="11" r="8" />
          <line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>
        <input
          aria-label="Search skills"
          placeholder="Search skills"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleSearchKeyDown}
          className="flex-1 bg-transparent text-[14px] text-ink-900 placeholder:text-ink-400 focus:outline-none"
        />
      </div>

      {data.skills.length > 0 && (
        <div className="mb-[22px] flex flex-wrap gap-1.5">
          {data.skills.map((skill) => (
            <span
              key={skill}
              className="flex items-center gap-1.5 rounded-full bg-accent py-[5px] pl-[11px] pr-1.5 text-[12.5px] font-medium text-white"
            >
              {skill}
              <button
                type="button"
                aria-label={`Remove ${skill}`}
                onClick={() => toggle(skill)}
                className="flex items-center rounded-full p-0.5 hover:opacity-70 focus-visible:outline focus-visible:outline-2 focus-visible:outline-white"
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

      {SKILL_GROUPS.map((group) => {
        const visible = group.items.filter(
          (item) => !q || item.toLowerCase().includes(q),
        );
        if (visible.length === 0) return null;
        return (
          <div key={group.label} className="mb-5">
            <div className="mb-2.5 text-[12.5px] font-semibold uppercase tracking-[0.4px] text-ink-400">
              {group.label}
            </div>
            <div className="flex flex-wrap gap-2">
              {visible.map((item) => {
                const selected = data.skills.includes(item);
                return (
                  <button
                    key={item}
                    type="button"
                    aria-pressed={selected}
                    onClick={() => toggle(item)}
                    className={`rounded-xl border px-3.5 py-[7px] text-[13px] font-medium focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-accent ${
                      selected
                        ? "border-accent bg-accent text-white"
                        : "border-line bg-white text-ink-700 hover:bg-raised"
                    }`}
                  >
                    {item}
                  </button>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}
