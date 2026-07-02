# Kortex — Database Schema
**Version:** 1.0.0
**Covers:** Phase 1 (Foundation) + Phase 2 (Job Discovery)
**DB:** PostgreSQL via Supabase

---

## 1. `users`
Managed by Supabase Auth (`auth.users`). We extend via `profiles`, not by duplicating auth fields.

---

## 2. `profiles`
```sql
CREATE TABLE profiles (
    id              UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    full_name       TEXT NOT NULL,
    phone           TEXT,
    location        TEXT,
    github_url      TEXT,
    portfolio_url   TEXT,
    linkedin_url    TEXT,
    experience_level TEXT NOT NULL CHECK (experience_level IN ('intern', 'junior', 'mid')),
    target_roles    TEXT[] NOT NULL DEFAULT '{}',       -- ['Backend', 'DevOps', ...]
    skills          TEXT[] NOT NULL DEFAULT '{}',       -- tagged skill list
    resume_url      TEXT,                               -- Supabase Storage signed path
    resume_text     TEXT,                               -- parsed text, cached for cover letters
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_profiles_experience_level ON profiles(experience_level);
```

**RLS:** user can only select/update their own row (`auth.uid() = id`).

---

## 3. `preferences`
```sql
CREATE TABLE preferences (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    boards_enabled      TEXT[] NOT NULL DEFAULT '{greenhouse,lever,workable,remoteok,web3career,cryptojobslist,linkedin}',
    location_filter     TEXT[] NOT NULL DEFAULT '{remote}',   -- e.g. ['remote', 'lagos', 'nigeria']
    excluded_keywords   TEXT[] NOT NULL DEFAULT '{}',
    digest_time_local   TIME NOT NULL DEFAULT '08:00',
    digest_timezone     TEXT NOT NULL DEFAULT 'Africa/Lagos',
    match_score_threshold NUMERIC(4,1) NOT NULL DEFAULT 2.0,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(user_id)
);
```

**RLS:** same as profiles, scoped by `user_id`.

---

## 4. `jobs`
Global table — one row per unique job, not per user.
```sql
CREATE TABLE jobs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_board    TEXT NOT NULL,          -- 'greenhouse' | 'lever' | ...
    external_id     TEXT,                   -- board's own job id if available
    title           TEXT NOT NULL,
    company         TEXT NOT NULL,
    location        TEXT,
    description     TEXT NOT NULL,
    stack_tags      TEXT[] NOT NULL DEFAULT '{}',
    apply_url       TEXT NOT NULL,
    dedup_hash      TEXT NOT NULL,          -- hash(url + title + company)
    posted_at       TIMESTAMPTZ,
    discovered_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    is_active       BOOLEAN NOT NULL DEFAULT true,  -- false if scraper detects it's closed/gone
    UNIQUE(dedup_hash)
);

CREATE INDEX idx_jobs_source_board ON jobs(source_board);
CREATE INDEX idx_jobs_discovered_at ON jobs(discovered_at DESC);
CREATE INDEX idx_jobs_dedup_hash ON jobs(dedup_hash);
```

**RLS:** none needed — public read via API, writes only from service role (scraper worker).

---

## 5. `job_matches`
Per-user scored relationship to a job.
```sql
CREATE TABLE job_matches (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    job_id          UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    match_score     NUMERIC(6,1) NOT NULL,
    score_breakdown JSONB,                  -- {"skill_match": 6.0, "location": 3.0, ...} for debugging/tuning
    status          TEXT NOT NULL DEFAULT 'new'
                    CHECK (status IN ('new', 'approved', 'skipped', 'saved')),
    notified_at     TIMESTAMPTZ,            -- when included in a digest email
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(user_id, job_id)
);

CREATE INDEX idx_job_matches_user_status ON job_matches(user_id, status);
CREATE INDEX idx_job_matches_score ON job_matches(user_id, match_score DESC);
```

**RLS:** user can only select/update rows where `user_id = auth.uid()`.

---

## Notes / Open Decisions Carried From PRD
- `applications` table (Phase 4) and Gmail response-detection tables (Phase 5) deliberately excluded from this pass — out of scope for tonight's backend focus (auth + profile + discovery only).
- `score_breakdown` as JSONB chosen over separate columns so the scoring engine can evolve weights without a migration.
- Soft delete via `is_active` on `jobs` rather than hard delete, since `job_matches` references it and users may still want to see a match history even if the listing closed.
