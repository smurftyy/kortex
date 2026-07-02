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
```json
// 200 Response
{ "id": "uuid", "email": "string", "profile_complete": true }
```

---

## Profile

### `PUT /profile`
```json
// Request
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
// 200 Response — full profile object
```

### `POST /profile/resume`
`multipart/form-data`, field `file` (PDF, max 5MB)
```json
// 200 Response
{ "resume_url": "string", "parsed_preview": "first 500 chars of extracted text" }
```

### `PUT /profile/preferences`
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
// 200 Response — full preferences object
```

---

## Jobs

### `GET /jobs`
Query params: `board`, `location`, `stack`, `date_from`, `date_to`, `status`, `page`, `page_size` (default 20, max 100)
```json
// 200 Response
{
  "results": [
    {
      "job_id": "uuid",
      "title": "string",
      "company": "string",
      "location": "string",
      "stack_tags": ["string"],
      "source_board": "string",
      "match_score": 7.5,
      "status": "new",
      "posted_at": "iso8601",
      "discovered_at": "iso8601"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total": 143
}
```

### `GET /jobs/{job_id}`
```json
// 200 Response — full job + match record
{
  "job_id": "uuid",
  "title": "string",
  "company": "string",
  "location": "string",
  "description": "string",
  "stack_tags": ["string"],
  "apply_url": "string",
  "source_board": "string",
  "match_score": 7.5,
  "score_breakdown": { "skill_match": 6.0, "location": 1.5 },
  "status": "new"
}
```

### `POST /jobs/{job_id}/approve`
`204 No Content` — sets `job_matches.status = 'approved'`

### `POST /jobs/{job_id}/skip`
`204 No Content` — sets `job_matches.status = 'skipped'`

### `POST /jobs/{job_id}/save`
`204 No Content` — sets `job_matches.status = 'saved'`

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
- Score threshold filtering for `GET /jobs` happens at query time using `preferences.match_score_threshold` unless overridden by query param.
