"use client";

import { useMutation } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { StepPersonal } from "@/components/onboarding/step-personal";
import { StepPreferences } from "@/components/onboarding/step-preferences";
import { StepResume } from "@/components/onboarding/step-resume";
import { StepSkills } from "@/components/onboarding/step-skills";
import { Button } from "@/components/ui/button";
import { FormError } from "@/components/ui/field";
import { putPreferences } from "@/lib/api/endpoints";
import { BOARDS } from "@/lib/boards";
import { getSupabaseClient } from "@/lib/supabase/client";
import { useAuth } from "@/providers/auth-provider";

export interface OnboardingData {
  fullName: string;
  phone: string;
  location: string;
  githubUrl: string;
  portfolioUrl: string;
  linkedinUrl: string;
  experienceLevel: "" | "intern" | "junior" | "mid";
  skills: string[];
  targetRoles: string[];
  locations: string[];
  excludedKeywords: string[];
  boards: string[];
  scanTime: string;
}

const INITIAL: OnboardingData = {
  fullName: "",
  phone: "",
  location: "",
  githubUrl: "",
  portfolioUrl: "",
  linkedinUrl: "",
  experienceLevel: "",
  skills: [],
  targetRoles: [],
  locations: [],
  excludedKeywords: [],
  boards: BOARDS.map((b) => b.slug),
  scanTime: "08:00",
};

const TOTAL_STEPS = 4;

/**
 * No API endpoint creates the profiles row (PATCH /profile 404s without
 * one) — the migration's "insert own profile" RLS policy is the intended
 * creation path, so this one write goes via Supabase. Runs when leaving
 * step 1 so the resume endpoints (which 404 without a profile) work on
 * step 3, then again with the complete data on finish.
 */
async function upsertProfile(userId: string, data: OnboardingData) {
  const { error } = await getSupabaseClient()
    .from("profiles")
    .upsert(
      {
        id: userId,
        full_name: data.fullName.trim(),
        phone: data.phone.trim() || null,
        location: data.location.trim() || null,
        github_url: data.githubUrl.trim() || null,
        portfolio_url: data.portfolioUrl.trim() || null,
        linkedin_url: data.linkedinUrl.trim() || null,
        experience_level: data.experienceLevel,
        target_roles: data.targetRoles,
        skills: data.skills,
      },
      { onConflict: "id" },
    );
  if (error) throw new Error(error.message);
}

export function OnboardingFlow() {
  const router = useRouter();
  const { user } = useAuth();
  const [step, setStep] = useState(1);
  const [data, setData] = useState(INITIAL);

  const patch = (partial: Partial<OnboardingData>) =>
    setData((d) => ({ ...d, ...partial }));

  const saveProfile = useMutation({
    mutationFn: async () => {
      if (!user) throw new Error("Not signed in.");
      await upsertProfile(user.id, data);
    },
    onSuccess: () => setStep(2),
  });

  const finish = useMutation({
    mutationFn: async () => {
      if (!user) throw new Error("Not signed in.");
      await upsertProfile(user.id, data);
      await putPreferences({
        boards_enabled: data.boards,
        location_filter: data.locations,
        excluded_keywords: data.excludedKeywords,
        digest_time_local: data.scanTime,
        digest_timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        match_score_threshold: 2.0,
      });
    },
    onSuccess: () => router.replace("/"),
  });

  const pending = saveProfile.isPending || finish.isPending;
  const mutationError = saveProfile.error ?? finish.error;

  const canContinue =
    step === 1
      ? data.fullName.trim().length > 0 && data.experienceLevel !== ""
      : step === TOTAL_STEPS
        ? data.targetRoles.length > 0
        : true;

  const handlePrimary = () => {
    if (step === 1) {
      saveProfile.mutate();
      return;
    }
    if (step < TOTAL_STEPS) {
      setStep(step + 1);
      return;
    }
    finish.mutate();
  };

  const primaryLabel =
    step === 1 && saveProfile.isPending
      ? "Saving…"
      : step < TOTAL_STEPS
        ? "Continue"
        : finish.isPending
          ? "Finishing…"
          : "Finish setup";

  return (
    <div>
      {/* Progress segments — design's 4px filled bars */}
      <div className="mb-7 flex items-center gap-2.5">
        {Array.from({ length: TOTAL_STEPS }, (_, i) => (
          <div
            key={i}
            className={`h-1 flex-1 rounded-full ${
              step >= i + 1 ? "bg-accent" : "bg-line-soft"
            }`}
          />
        ))}
      </div>
      <div className="mb-[30px] flex items-center justify-between">
        {step > 1 ? (
          <button
            type="button"
            onClick={() => setStep(step - 1)}
            className="flex items-center gap-[5px] text-[13.5px] font-medium text-ink-500 hover:text-ink-700"
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <polyline points="15 18 9 12 15 6" />
            </svg>
            Back
          </button>
        ) : (
          <span />
        )}
        <span className="text-[12.5px] font-semibold text-ink-400">
          Step {step} of {TOTAL_STEPS}
        </span>
      </div>

      {step === 1 && (
        <StepPersonal data={data} onPatch={patch} email={user?.email ?? ""} />
      )}
      {step === 2 && <StepSkills data={data} onPatch={patch} />}
      {step === 3 && <StepResume />}
      {step === 4 && <StepPreferences data={data} onPatch={patch} />}

      {mutationError && (
        <div className="mt-6">
          <FormError>{(mutationError as Error).message}</FormError>
        </div>
      )}

      <div className="mt-8 flex justify-end">
        <Button
          onClick={handlePrimary}
          disabled={!canContinue || pending}
          className="px-6 py-3 text-[14.5px]"
        >
          {primaryLabel}
        </Button>
      </div>
    </div>
  );
}
