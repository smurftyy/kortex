"use client";

import { Label } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";

import type { OnboardingData } from "./onboarding-flow";

interface StepProps {
  data: OnboardingData;
  onPatch: (partial: Partial<OnboardingData>) => void;
  email: string;
}

export function StepPersonal({ data, onPatch, email }: StepProps) {
  return (
    <div>
      <h1 className="mb-1.5 text-[26px] font-bold tracking-[-0.3px] text-ink-900">
        Welcome back, let&rsquo;s set a few things up.
      </h1>
      <p className="mb-8 text-[14.5px] text-ink-500">
        This takes about a minute. You can change any of this later in
        Settings.
      </p>

      <div className="flex flex-col gap-[18px]">
        <div>
          <Label htmlFor="full-name">Full name</Label>
          <Input
            id="full-name"
            placeholder="Alex Rivera"
            autoComplete="name"
            value={data.fullName}
            onChange={(e) => onPatch({ fullName: e.target.value })}
          />
        </div>
        <div>
          <Label htmlFor="ob-email">Email</Label>
          <Input id="ob-email" value={email} disabled readOnly />
          <p className="mt-1.5 text-[12.5px] text-ink-400">
            From your account — applications use this address.
          </p>
        </div>
        <div>
          <Label htmlFor="phone">Phone</Label>
          <Input
            id="phone"
            type="tel"
            placeholder="(415) 555-0148"
            autoComplete="tel"
            value={data.phone}
            onChange={(e) => onPatch({ phone: e.target.value })}
          />
        </div>
        <div>
          <Label htmlFor="location">Location</Label>
          <Input
            id="location"
            placeholder="San Francisco, CA"
            value={data.location}
            onChange={(e) => onPatch({ location: e.target.value })}
          />
        </div>
        <div>
          <Label htmlFor="experience-level">Experience level</Label>
          <Select
            id="experience-level"
            value={data.experienceLevel}
            onChange={(e) =>
              onPatch({
                experienceLevel:
                  e.target.value as OnboardingData["experienceLevel"],
              })
            }
          >
            <option value="" disabled>
              Select your level
            </option>
            <option value="intern">Intern</option>
            <option value="junior">Junior</option>
            <option value="mid">Mid-level</option>
          </Select>
        </div>
        <div>
          <Label htmlFor="github-url">GitHub URL</Label>
          <Input
            id="github-url"
            type="url"
            placeholder="github.com/alexrivera"
            value={data.githubUrl}
            onChange={(e) => onPatch({ githubUrl: e.target.value })}
          />
        </div>
        <div>
          <Label htmlFor="portfolio-url">Portfolio URL</Label>
          <Input
            id="portfolio-url"
            type="url"
            placeholder="alexrivera.dev"
            value={data.portfolioUrl}
            onChange={(e) => onPatch({ portfolioUrl: e.target.value })}
          />
        </div>
        <div>
          <Label htmlFor="linkedin-url">LinkedIn URL</Label>
          <Input
            id="linkedin-url"
            type="url"
            placeholder="linkedin.com/in/alexrivera"
            value={data.linkedinUrl}
            onChange={(e) => onPatch({ linkedinUrl: e.target.value })}
          />
        </div>
      </div>
    </div>
  );
}
