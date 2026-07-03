"use client";

import { useRef, useState, type DragEvent } from "react";

import { FormError } from "@/components/ui/field";
import { parseResume, uploadResume } from "@/lib/api/endpoints";
import type { ResumeParseResponse } from "@/lib/api/types";

const MAX_BYTES = 5 * 1024 * 1024;

// Per-status copy for the parse outcomes the contract defines — all are
// 200s, not errors; only "parsed" stores text server-side.
const STATUS_COPY: Record<
  Exclude<ResumeParseResponse["status"], "parsed">,
  string
> = {
  no_text_found:
    "We couldn’t find any text in this PDF — it may be a scanned image. You can continue; matching will rely on your profile until you upload a text-based copy.",
  password_protected:
    "This PDF is password-protected, so we couldn’t read it. Remove the password and upload it again.",
  corrupt:
    "This file looks corrupted. Try re-exporting the PDF and uploading again.",
};

type Phase = "idle" | "busy" | "done";

export function ResumeUpload() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [phase, setPhase] = useState<Phase>("idle");
  const [fileName, setFileName] = useState("");
  const [result, setResult] = useState<ResumeParseResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);

  const handleFile = async (file: File) => {
    setError(null);
    const isPdf =
      file.type === "application/pdf" ||
      file.name.toLowerCase().endsWith(".pdf");
    if (!isPdf) {
      setError("Only PDF files are supported.");
      return;
    }
    if (file.size > MAX_BYTES) {
      setError("That file is over the 5MB limit.");
      return;
    }

    setFileName(file.name);
    setPhase("busy");
    try {
      await uploadResume(file);
      const parsed = await parseResume();
      setResult(parsed);
      setPhase("done");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.");
      setPhase("idle");
    }
  };

  const reset = () => {
    setPhase("idle");
    setResult(null);
    setFileName("");
    setError(null);
    if (inputRef.current) inputRef.current.value = "";
  };

  const handleDrop = (event: DragEvent) => {
    event.preventDefault();
    setDragging(false);
    const file = event.dataTransfer.files[0];
    if (file && phase === "idle") void handleFile(file);
  };

  return (
    <div>
      <input
        ref={inputRef}
        type="file"
        accept="application/pdf,.pdf"
        aria-label="Resume file"
        className="sr-only"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) void handleFile(file);
        }}
      />

      {phase === "idle" && (
        <div
          role="button"
          tabIndex={0}
          aria-label="Drag and drop your resume, or press Enter to browse"
          onClick={() => inputRef.current?.click()}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              inputRef.current?.click();
            }
          }}
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={handleDrop}
          className={`flex cursor-pointer flex-col items-center rounded-xl border-[1.5px] border-dashed bg-raised px-5 py-14 text-center focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent ${
            dragging ? "border-accent bg-accent-tint" : "border-[#D3D3D0]"
          }`}
        >
          <div className="mb-3.5 flex h-11 w-11 items-center justify-center rounded-full bg-accent-tint text-accent-deep">
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.75"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
          </div>
          <div className="mb-1 text-[14.5px] font-semibold text-ink-900">
            Drag and drop your resume
          </div>
          <div className="text-[13px] text-ink-400">
            or click to browse &middot; PDF, up to 5MB
          </div>
        </div>
      )}

      {phase === "busy" && (
        <div className="flex flex-col items-center rounded-xl border-[1.5px] border-line bg-raised px-5 py-14 text-center">
          <div className="mb-3 text-[14.5px] font-semibold text-ink-900">
            Uploading {fileName}&hellip;
          </div>
          <div className="h-1.5 w-[220px] overflow-hidden rounded-full bg-line-soft">
            <div className="h-full w-[70%] animate-pulse rounded-full bg-accent" />
          </div>
        </div>
      )}

      {phase === "done" && result && (
        <div>
          <div className="mb-4 flex items-center gap-2.5 rounded-xl border border-line bg-white px-[18px] py-4">
            {result.status === "parsed" ? (
              <svg
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="#3F7D4E"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
                className="shrink-0"
              >
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                <polyline points="22 4 12 14.01 9 11.01" />
              </svg>
            ) : (
              <svg
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="#B98A2E"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
                className="shrink-0"
              >
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
            )}
            <div className="min-w-0">
              <div className="text-[14px] font-semibold text-ink-900">
                {fileName} uploaded
              </div>
              <div className="text-[12.5px] text-ink-400">
                {result.status === "parsed"
                  ? "Text extracted — this powers your tailored applications."
                  : STATUS_COPY[result.status]}
              </div>
            </div>
          </div>

          {result.status === "parsed" && result.resume_text && (
            <div className="mb-4 max-h-40 overflow-y-auto whitespace-pre-wrap rounded-xl border border-line bg-white px-[18px] py-4 text-[13px] leading-relaxed text-ink-600">
              {result.resume_text.slice(0, 600)}
              {result.resume_text.length > 600 && "…"}
            </div>
          )}

          <button
            type="button"
            onClick={reset}
            className="text-[12.5px] font-semibold text-accent hover:text-accent-deep"
          >
            Upload a different file
          </button>
        </div>
      )}

      {error && (
        <div className="mt-4">
          <FormError>{error}</FormError>
        </div>
      )}
    </div>
  );
}
