# Kortex — API Contract
**Version:** 1.0.0
**Covers:** Phase 1 (Foundation) + Phase 2 (Job Discovery)
**Base URL:** `/api/v1`
**Auth:** Bearer JWT in `Authorization` header unless noted public

---

## Auth

### `POST /auth/signup`
```json
// Request
{ "email": "string", "password": "string" }
// 201 Response
{ "user_id": "uuid", "email": "string", "verification_sent": true }
```

### `POST /auth/login`
```json
// Request
{ "email": "string", "password": "string" }
// 200 Response
{ "access_token": "string", "refresh_token": "string", "expires_in": 900 }
```

### `POST /auth/refresh`
```json
// Request
{ "refresh_token": "string" }
// 200 Response
{ "access_token": "string", "expires_in": 900 }
```

### `GET /auth/me`
Returns the caller's own `profiles` row (matched via RLS against the JWT's `sub`
claim, not an application-level filter).
```json
// 200 Response
{
  "id": "uuid",
  "full_name": "string",
  "phone": "string | null",
  "location": "string | null",
  "github_url": "string | null",
  "portfolio_url": "string | null",
  "linkedin_url": "string | null",
  "experience_level": "intern | junior | mid",
  "target_roles": ["string"],
  "skills": ["string"],
  "resume_url": "string | null",
  "resume_text": "string | null",
  "created_at": "iso8601",
  "updated_at": "iso8601"
}
```
`404` (`PROFILE_NOT_FOUND`) if the JWT is valid but no `profiles` row exists yet
for that user (edge case: signed up but never completed `PATCH /profile`).

---

## Profile

### `PATCH /profile`
Partial update of the caller's own `profiles` row (RLS-scoped, same as
`GET /auth/me`). Only fields present in the body are changed; omitted fields
are left untouched. `full_name`, `experience_level`, `target_roles`, and
`skills` are NOT NULL columns — they may be omitted, but may not be set to
`null` (`422` if attempted). Unknown fields are rejected (`422`).
```json
// Request — any subset of:
{
  "full_name": "string",
  "phone": "string | null",
  "location": "string | null",
  "github_url": "string | null",
  "portfolio_url": "string | null",
  "linkedin_url": "string | null",
  "experience_level": "intern | junior | mid",
  "target_roles": ["string"],
  "skills": ["string"]
}
// 200 Response — full profile object (same shape as `GET /auth/me`)
```
`404` (`PROFILE_NOT_FOUND`) if the JWT is valid but no `profiles` row exists yet.

### `POST /profile/resume`
`multipart/form-data`, field `file` (PDF, max 5MB)
```json
// 200 Response
{ "resume_url": "string", "parsed_preview": "first 500 chars of extracted text" }
```

---

## Preferences

### `GET /preferences`
Returns the caller's own `preferences` row (RLS-scoped by `user_id`).
```json
// 200 Response
{
  "id": "uuid",
  "user_id": "uuid",
  "boards_enabled": ["string"],
  "location_filter": ["string"],
  "excluded_keywords": ["string"],
  "digest_time_local": "08:00",
  "digest_timezone": "string",
  "match_score_threshold": 2.0,
  "created_at": "iso8601",
  "updated_at": "iso8601"
}
```
`404` (`PREFERENCES_NOT_FOUND`) if the JWT is valid but no `preferences` row
exists yet (mirrors the `GET /auth/me` edge case) — i.e. before the first
`PUT /preferences` call.

### `PUT /preferences`
Full upsert — creates the row on first call, replaces it entirely on
subsequent calls (matched on the `user_id` unique constraint). All six
fields are required; unknown fields are rejected (`422`).
```json
// Request
{
  "boards_enabled": ["greenhouse", "lever"],
  "location_filter": ["remote", "lagos"],
  "excluded_keywords": ["senior"],
  "digest_time_local": "08:00",
  "digest_timezone": "Africa/Lagos",
  "match_score_threshold": 2.0
}
// 201 Response if this is the first call for this user — full preferences object
// 200 Response if an existing row was replaced — full preferences object
```

---

## Jobs

### `GET /jobs`
**Public** — no `Authorization` header required (the `jobs` table has no RLS;
see SCHEMA_kortex.md section 4). Only active listings (`is_active = true`)
are returned. Because this endpoint has no caller identity, results carry
`jobs` table fields only — no per-user `job_matches` fields (`match_score`,
`status`, `score_breakdown`); a `status` (match-status) filter is dropped
for the same reason.

Query params: `board`, `location` (case-insensitive partial match), `stack`
(single tag), `date_from`, `date_to` (both bound `posted_at`), `page`,
`page_size` (default 20, max 100).
```json
// 200 Response
{
  "results": [
    {
      "job_id": "uuid",
      "title": "string",
      "company": "string",
      "location": "string | null",
      "stack_tags": ["string"],
      "source_board": "string",
      "posted_at": "iso8601 | null",
      "discovered_at": "iso8601"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total": 143
}
```

### `GET /jobs/{job_id}`
**Public** — same as above. `404` (`JOB_NOT_FOUND`) if the id doesn't exist
*or* the job is soft-deleted (`is_active = false`) — a closed listing isn't
individually fetchable even though it may still appear in a user's match
history via `job_matches`.
```json
// 200 Response
{
  "job_id": "uuid",
  "title": "string",
  "company": "string",
  "location": "string | null",
  "description": "string",
  "stack_tags": ["string"],
  "apply_url": "string",
  "source_board": "string",
  "posted_at": "iso8601 | null",
  "discovered_at": "iso8601"
}
```

### `POST /jobs/{job_id}/approve`
Requires auth. RLS-scoped `UPDATE` on the caller's own `job_matches` row —
never creates one (`job_matches` has no INSERT policy; rows are created by
the scoring worker only). `204 No Content` on success; `404`
(`MATCH_NOT_FOUND`) if no existing match row for this `(user, job)` pair,
whether because the job doesn't exist or because it exists but was never
matched to this user — both collapse to the same response. Sets
`job_matches.status = 'approved'`.

### `POST /jobs/{job_id}/skip`
Same as above; sets `job_matches.status = 'skipped'`.

### `POST /jobs/{job_id}/save`
Same as above; sets `job_matches.status = 'saved'`.

---

## Error Format (all endpoints)
```json
{
  "error": {
    "code": "string",       // e.g. "INVALID_CREDENTIALS", "RESUME_TOO_LARGE"
    "message": "string",    // human-readable
    "field": "string | null"
  }
}
```
HTTP status codes: 400 (validation), 401 (auth), 403 (RLS/ownership), 404, 429 (rate limit), 500.

---

## Notes
- `applications/*` endpoints (Phase 4) deliberately excluded — not in scope tonight.
- Score-threshold filtering on `GET /jobs` (via `preferences.match_score_threshold`)
  is **not implemented** as of this commit — it requires a per-user
  `job_matches` join, which conflicts with `GET /jobs` being a public,
  unauthenticated endpoint. Revisit if/when a personalized (authenticated)
  jobs view is added.
