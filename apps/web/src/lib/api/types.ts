/**
 * Request/response types transcribed from API_CONTRACT_kortex.md v1.0.0.
 * Field names and shapes must match the contract exactly — do not add or
 * rename fields here without a contract change.
 */

export type ExperienceLevel = "intern" | "junior" | "mid";

// GET /auth/me · PATCH /profile (response)
export interface Profile {
  id: string;
  full_name: string;
  phone: string | null;
  location: string | null;
  github_url: string | null;
  portfolio_url: string | null;
  linkedin_url: string | null;
  experience_level: ExperienceLevel;
  target_roles: string[];
  skills: string[];
  resume_url: string | null;
  resume_text: string | null;
  created_at: string;
  updated_at: string;
}

// PATCH /profile (request) — any subset; NOT NULL columns may be omitted
// but never sent as null.
export interface ProfilePatch {
  full_name?: string;
  phone?: string | null;
  location?: string | null;
  github_url?: string | null;
  portfolio_url?: string | null;
  linkedin_url?: string | null;
  experience_level?: ExperienceLevel;
  target_roles?: string[];
  skills?: string[];
}

// POST /profile/resume (response)
export interface ResumeUploadResponse {
  resume_url: string;
}

// POST /profile/resume/parse (response) — always 200 once existence checks
// pass; file-specific failures are a status, not an HTTP error.
export type ResumeParseStatus =
  | "parsed"
  | "no_text_found"
  | "password_protected"
  | "corrupt";

export interface ResumeParseResponse {
  status: ResumeParseStatus;
  resume_text: string | null;
}

// GET /preferences · PUT /preferences (response)
export interface Preferences {
  id: string;
  user_id: string;
  boards_enabled: string[];
  location_filter: string[];
  excluded_keywords: string[];
  digest_time_local: string;
  digest_timezone: string;
  match_score_threshold: number;
  created_at: string;
  updated_at: string;
}

// PUT /preferences (request) — full upsert, all six fields required.
export interface PreferencesPut {
  boards_enabled: string[];
  location_filter: string[];
  excluded_keywords: string[];
  digest_time_local: string;
  digest_timezone: string;
  match_score_threshold: number;
}

// GET /jobs (list items) — jobs-table fields only; no per-user match data
// exists on this public endpoint.
export interface JobListItem {
  job_id: string;
  title: string;
  company: string;
  location: string | null;
  stack_tags: string[];
  source_board: string;
  posted_at: string | null;
  discovered_at: string;
}

export interface JobListResponse {
  results: JobListItem[];
  page: number;
  page_size: number;
  total: number;
}

// GET /jobs query params.
export interface JobsQuery {
  board?: string;
  location?: string;
  stack?: string;
  date_from?: string;
  date_to?: string;
  page?: number;
  page_size?: number;
}

// GET /jobs/{job_id}
export interface JobDetail {
  job_id: string;
  title: string;
  company: string;
  location: string | null;
  description: string;
  stack_tags: string[];
  apply_url: string;
  source_board: string;
  posted_at: string | null;
  discovered_at: string;
}

// POST /jobs/{id}/approve | /skip | /save — 204 No Content.
export type MatchAction = "approve" | "skip" | "save";
