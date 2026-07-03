"use client";

import { ResumeUpload } from "@/components/resume/resume-upload";

export function StepResume() {
  return (
    <div>
      <h1 className="mb-1.5 text-[26px] font-bold tracking-[-0.3px] text-ink-900">
        Upload your master resume.
      </h1>
      <p className="mb-6 text-[14.5px] text-ink-500">
        We tailor a copy for every application. Your master version is never
        edited directly.
      </p>
      <ResumeUpload />
    </div>
  );
}
