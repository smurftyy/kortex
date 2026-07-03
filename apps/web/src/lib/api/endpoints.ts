import { apiFetch } from "./client";
import type {
  JobDetail,
  JobListResponse,
  JobsQuery,
  MatchAction,
  Preferences,
  PreferencesPut,
  Profile,
  ProfilePatch,
  ResumeParseResponse,
  ResumeUploadResponse,
} from "./types";

export function getMe(): Promise<Profile> {
  return apiFetch<Profile>("/auth/me");
}

export function patchProfile(patch: ProfilePatch): Promise<Profile> {
  return apiFetch<Profile>("/profile", { method: "PATCH", body: patch });
}

export function uploadResume(file: File): Promise<ResumeUploadResponse> {
  const form = new FormData();
  form.append("file", file);
  return apiFetch<ResumeUploadResponse>("/profile/resume", {
    method: "POST",
    body: form,
  });
}

export function parseResume(): Promise<ResumeParseResponse> {
  return apiFetch<ResumeParseResponse>("/profile/resume/parse", {
    method: "POST",
  });
}

export function getPreferences(): Promise<Preferences> {
  return apiFetch<Preferences>("/preferences");
}

export function putPreferences(prefs: PreferencesPut): Promise<Preferences> {
  return apiFetch<Preferences>("/preferences", { method: "PUT", body: prefs });
}

export function getJobs(query: JobsQuery = {}): Promise<JobListResponse> {
  return apiFetch<JobListResponse>("/jobs", {
    query: { ...query },
  });
}

export function getJob(jobId: string): Promise<JobDetail> {
  return apiFetch<JobDetail>(`/jobs/${jobId}`);
}

export function actOnJob(jobId: string, action: MatchAction): Promise<void> {
  return apiFetch<void>(`/jobs/${jobId}/${action}`, { method: "POST" });
}
