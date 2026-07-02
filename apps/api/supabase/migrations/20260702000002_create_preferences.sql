-- preferences: per-user job-discovery settings.
-- Schema source: SCHEMA_kortex.md section 3 (used verbatim).

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

-- Row Level Security: a user may only see and modify their own preferences row.
ALTER TABLE preferences ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can select their own preferences"
    ON preferences
    FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can update their own preferences"
    ON preferences
    FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can insert their own preferences"
    ON preferences
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- No DELETE policy: preferences rows are removed via the profiles FK
-- (ON DELETE CASCADE, which itself cascades from auth.users), not deleted
-- directly by users.
