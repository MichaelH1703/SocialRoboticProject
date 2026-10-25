-- Safety events: one row each time a hard safety rule fires during a Reachy
-- conversation (see reachy_safety.py). Critical events -- a child disclosing
-- harm, saying they do not want to be alive, or asking Reachy to keep a
-- secret -- need an adult to follow up, so the robot writes them the moment
-- they happen rather than with the conversation log at the end of a session.
--
-- reachy_text is the scripted line Reachy said, or NULL when the model was
-- guided rather than replaced (medium rules); the conversation log has that
-- reply. reviewed_at is for a dashboard to mark an event as followed up.
--
-- Safe to run more than once. Apply with:
--   docker exec -i supabase_db_ReachyVoiceCode psql -U postgres -d postgres -f - < safety_events.sql
-- or paste it into the Supabase SQL editor.

BEGIN;

CREATE TABLE IF NOT EXISTS "public"."safety_events" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL PRIMARY KEY,
    "therapist_id" "uuid" NOT NULL
        REFERENCES "auth"."users"("id") ON DELETE CASCADE,
    "client_name" "text" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "rule_id" "text" NOT NULL,
    "rule_name" "text" NOT NULL,
    "severity" "text" NOT NULL,
    "child_text" "text" NOT NULL,
    "reachy_text" "text",
    "lesson_stopped" boolean DEFAULT false NOT NULL,
    "reviewed_at" timestamp with time zone,
    CONSTRAINT "safety_events_severity_check" CHECK ("severity" IN ('critical', 'high', 'medium'))
);

ALTER TABLE "public"."safety_events" OWNER TO "postgres";

CREATE INDEX IF NOT EXISTS "safety_events_therapist_client_idx"
    ON "public"."safety_events" ("therapist_id", "client_name", "created_at" DESC);

ALTER TABLE "public"."safety_events" ENABLE ROW LEVEL SECURITY;

-- The robot client writes with the anon key, as it does for conversation_logs.
-- It may insert, never read: a child's disclosures are for the therapist only.
DROP POLICY IF EXISTS "Reachy inserts safety events" ON "public"."safety_events";
CREATE POLICY "Reachy inserts safety events" ON "public"."safety_events"
    FOR INSERT TO "anon"
    WITH CHECK (true);

DROP POLICY IF EXISTS "Therapists manage own safety events" ON "public"."safety_events";
CREATE POLICY "Therapists manage own safety events" ON "public"."safety_events"
    TO "authenticated"
    USING ("auth"."uid"() = "therapist_id")
    WITH CHECK ("auth"."uid"() = "therapist_id");

GRANT INSERT ON TABLE "public"."safety_events" TO "anon";
GRANT ALL ON TABLE "public"."safety_events" TO "authenticated";
GRANT ALL ON TABLE "public"."safety_events" TO "service_role";

COMMIT;
