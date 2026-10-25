-- Storage RLS policies.
--
-- `pg_dump` of the public schema does not carry storage.objects policies, so
-- these did not come across with the rest of the migration. Without them every
-- storage call made with the anon key + a user session is denied, which breaks
-- daily recap upload and playback in the therapist dashboard.
--
-- Apply with:
--   docker exec -i supabase_db_ReachyVoiceCode psql -U postgres -d postgres -f - < storage_policies.sql

-- daily-recap-audio: therapists own the folder named after their user id,
-- matching the upload path built in therapist_dashboard.py
-- (f"{USER_ID}/{timestamp}_{filename}").
DROP POLICY IF EXISTS "Therapists read own recap audio" ON "storage"."objects";
CREATE POLICY "Therapists read own recap audio" ON "storage"."objects"
    FOR SELECT TO "authenticated"
    USING ("bucket_id" = 'daily-recap-audio'
           AND ("storage"."foldername"("name"))[1] = ("auth"."uid"())::"text");

DROP POLICY IF EXISTS "Therapists upload own recap audio" ON "storage"."objects";
CREATE POLICY "Therapists upload own recap audio" ON "storage"."objects"
    FOR INSERT TO "authenticated"
    WITH CHECK ("bucket_id" = 'daily-recap-audio'
                AND ("storage"."foldername"("name"))[1] = ("auth"."uid"())::"text");

DROP POLICY IF EXISTS "Therapists update own recap audio" ON "storage"."objects";
CREATE POLICY "Therapists update own recap audio" ON "storage"."objects"
    FOR UPDATE TO "authenticated"
    USING ("bucket_id" = 'daily-recap-audio'
           AND ("storage"."foldername"("name"))[1] = ("auth"."uid"())::"text")
    WITH CHECK ("bucket_id" = 'daily-recap-audio'
                AND ("storage"."foldername"("name"))[1] = ("auth"."uid"())::"text");

DROP POLICY IF EXISTS "Therapists delete own recap audio" ON "storage"."objects";
CREATE POLICY "Therapists delete own recap audio" ON "storage"."objects"
    FOR DELETE TO "authenticated"
    USING ("bucket_id" = 'daily-recap-audio'
           AND ("storage"."foldername"("name"))[1] = ("auth"."uid"())::"text");

-- lesson-plans: objects sit at the bucket root with no per-user prefix, so the
-- folder check above cannot apply. No code path reads this bucket yet; read
-- access for signed-in users mirrors the "Therapists manage own docs" policy on
-- public.lesson_plan_docs, which is what gates discovery of these paths.
DROP POLICY IF EXISTS "Authenticated read lesson plans" ON "storage"."objects";
CREATE POLICY "Authenticated read lesson plans" ON "storage"."objects"
    FOR SELECT TO "authenticated"
    USING ("bucket_id" = 'lesson-plans');
