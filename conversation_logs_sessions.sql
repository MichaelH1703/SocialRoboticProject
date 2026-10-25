-- Conversation logs for the therapist dashboard's Conversation Logs tab.
--
-- 1. Therapists may read their own clients' logs. schema.sql only gave
--    conversation_logs an INSERT policy, so with RLS on every read came back
--    empty.
-- 2. session_id and turn_index let the dashboard group turns by session and
--    show them in order. "timestamp" is text to the minute, so neither can be
--    worked out from it. The robot sets one session_id per run, in
--    save_conversation_on_exit. Rows written before this have both NULL; the
--    dashboard groups those by the gaps between their timestamps.
--
-- Apply before running the updated robot scripts; until then they retry the
-- upload without these columns. Safe to run more than once. Apply with:
--   docker exec -i supabase_db_ReachyVoiceCode psql -U postgres -d postgres -f - < conversation_logs_sessions.sql
-- or paste it into the Supabase SQL editor.

BEGIN;

ALTER TABLE "public"."conversation_logs"
    ADD COLUMN IF NOT EXISTS "session_id" "uuid",
    ADD COLUMN IF NOT EXISTS "turn_index" integer;

CREATE INDEX IF NOT EXISTS "conversation_logs_therapist_client_idx"
    ON "public"."conversation_logs" ("therapist_id", "client_name");

DROP POLICY IF EXISTS "therapists can read own conversation logs" ON "public"."conversation_logs";
CREATE POLICY "therapists can read own conversation logs" ON "public"."conversation_logs"
    FOR SELECT TO "authenticated"
    USING ("auth"."uid"() = "therapist_id");

COMMIT;
