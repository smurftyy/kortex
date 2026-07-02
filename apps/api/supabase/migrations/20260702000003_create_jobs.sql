-- jobs: global table of scraped job listings, one row per unique job.
-- Schema source: SCHEMA_kortex.md section 4 (used verbatim).
--
-- No RLS: public read via the API, writes only from the scraper/worker
-- using the service role key. No user-facing route in this API ever
-- inserts, updates, or deletes a row here.

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
