-- job_matches: per-user scored relationship to a job.
-- Schema source: SCHEMA_kortex.md section 5 (used verbatim).

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

-- Row Level Security: a user may only see and modify their own match rows.
ALTER TABLE job_matches ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can select their own job matches"
    ON job_matches
    FOR SELECT
    TO authenticated
    USING (auth.uid() = user_id);

CREATE POLICY "Users can update their own job matches"
    ON job_matches
    FOR UPDATE
    TO authenticated
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- No INSERT policy: match rows are created by the scoring worker (service
-- role), not by users directly — unlike profiles/preferences, a user never
-- creates their own job_matches row via the API.
--
-- No DELETE policy: match rows are removed via the profiles/jobs FK
-- (ON DELETE CASCADE), not deleted directly by users.
