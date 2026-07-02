-- profiles: extends auth.users with application-level profile fields.
-- Schema source: SCHEMA_kortex.md section 2 (used verbatim).

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

-- Row Level Security: a user may only see and modify their own profile row.
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can select their own profile"
    ON profiles
    FOR SELECT
    TO authenticated
    USING (auth.uid() = id);

CREATE POLICY "Users can update their own profile"
    ON profiles
    FOR UPDATE
    TO authenticated
    USING (auth.uid() = id)
    WITH CHECK (auth.uid() = id);

CREATE POLICY "Users can insert their own profile"
    ON profiles
    FOR INSERT
    TO authenticated
    WITH CHECK (auth.uid() = id);

-- No DELETE policy: profile rows are removed via the auth.users FK
-- (ON DELETE CASCADE), not deleted directly by users.
