-- resumes: private Storage bucket for user resumes, one object per user at
-- {user_id}/resume.pdf (re-uploads overwrite via upsert).
--
-- Not documented in SCHEMA_kortex.md (profiles.resume_url just says
-- "Supabase Storage signed path" with no bucket name) — name and path
-- convention confirmed directly with the user for Commit 7
-- (POST /profile/resume).
--
-- `storage.objects` already has RLS enabled by the Supabase platform, and
-- `storage.foldername()` is a built-in helper — neither is (re)declared
-- here, only the bucket and its policies.

INSERT INTO storage.buckets (id, name, public)
VALUES ('resumes', 'resumes', false)
ON CONFLICT (id) DO NOTHING;

-- Row Level Security: a user may only read/write objects under their own
-- {user_id}/ prefix within the resumes bucket. storage.objects.name is the
-- full object path (e.g. '<user_id>/resume.pdf'); storage.foldername()
-- splits it into path segments so the first segment can be compared to
-- auth.uid().
CREATE POLICY "Users can select their own resume"
    ON storage.objects
    FOR SELECT
    TO authenticated
    USING (bucket_id = 'resumes' AND (storage.foldername(name))[1] = auth.uid()::text);

CREATE POLICY "Users can upload their own resume"
    ON storage.objects
    FOR INSERT
    TO authenticated
    WITH CHECK (bucket_id = 'resumes' AND (storage.foldername(name))[1] = auth.uid()::text);

CREATE POLICY "Users can replace their own resume"
    ON storage.objects
    FOR UPDATE
    TO authenticated
    USING (bucket_id = 'resumes' AND (storage.foldername(name))[1] = auth.uid()::text)
    WITH CHECK (bucket_id = 'resumes' AND (storage.foldername(name))[1] = auth.uid()::text);

-- No DELETE policy: resume objects are overwritten (upsert), not deleted
-- directly by users — consistent with the no-DELETE convention used
-- throughout this project (Commits 2 and 5).
