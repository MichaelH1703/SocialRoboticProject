-- Participants: lets the therapist dashboard add, remove and permanently delete
-- children, and lets one parent account be linked to several children.
--
-- Before this the child list was hard-coded in both dashboards, and a parent
-- account could only be linked to one child (parent_accounts_parent_id_key).
-- Every other table, and the robot scripts' CLIENT_NAME setting, identify a
-- child by (therapist_id, client_name), so `clients` keys on that same pair
-- instead of introducing a new id.
--
-- Safe to run more than once. Apply with:
--   docker exec -i supabase_db_ReachyVoiceCode psql -U postgres -d postgres -f - < participants_migration.sql
-- or paste it into the Supabase SQL editor.

BEGIN;

-- ── clients ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS "public"."clients" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL PRIMARY KEY,
    "therapist_id" "uuid" DEFAULT "auth"."uid"() NOT NULL
        REFERENCES "auth"."users"("id") ON DELETE CASCADE,
    "client_name" "text" NOT NULL,
    "age" integer,
    "color" "text" DEFAULT '#A8A29E'::"text" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    -- Set when a therapist removes a child from their active list. The child's
    -- data is kept until they are deleted permanently.
    "archived_at" timestamp with time zone,
    CONSTRAINT "clients_client_name_check" CHECK ("length"("btrim"("client_name")) > 0),
    CONSTRAINT "clients_age_check" CHECK ("age" IS NULL OR ("age" >= 1 AND "age" <= 99))
);

ALTER TABLE "public"."clients" OWNER TO "postgres";

-- Case-insensitive, so "max" cannot be added alongside "Max".
CREATE UNIQUE INDEX IF NOT EXISTS "clients_therapist_id_client_name_key"
    ON "public"."clients" ("therapist_id", "lower"("client_name"));

ALTER TABLE "public"."clients" ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Therapists manage own clients" ON "public"."clients";
CREATE POLICY "Therapists manage own clients" ON "public"."clients"
    TO "authenticated"
    USING ("auth"."uid"() = "therapist_id")
    WITH CHECK ("auth"."uid"() = "therapist_id");

DROP POLICY IF EXISTS "Parents read linked clients" ON "public"."clients";
CREATE POLICY "Parents read linked clients" ON "public"."clients"
    FOR SELECT TO "authenticated"
    USING (EXISTS ( SELECT 1
       FROM "public"."parent_accounts"
      WHERE (("parent_accounts"."parent_id" = "auth"."uid"())
         AND ("parent_accounts"."therapist_id" = "clients"."therapist_id")
         AND ("parent_accounts"."client_name" = "clients"."client_name"))));

GRANT ALL ON TABLE "public"."clients" TO "authenticated";
GRANT ALL ON TABLE "public"."clients" TO "service_role";

-- Carry over every child that already has data, keeping the age and colour the
-- dashboards used to hard-code for the demo children.
INSERT INTO "public"."clients" ("therapist_id", "client_name", "age", "color")
SELECT DISTINCT ON ("src"."therapist_id", "lower"("src"."client_name"))
       "src"."therapist_id",
       "src"."client_name",
       "legacy"."age",
       COALESCE("legacy"."color", '#A8A29E')
  FROM (
        SELECT "therapist_id", "client_name" FROM "public"."client_profiles"
        UNION SELECT "therapist_id", "client_name" FROM "public"."session_notes"
        UNION SELECT "therapist_id", "client_name" FROM "public"."daily_recap_sessions"
        UNION SELECT "therapist_id", "client_name" FROM "public"."client_curriculum"
        UNION SELECT "therapist_id", "client_name" FROM "public"."client_progress"
        UNION SELECT "therapist_id", "client_name" FROM "public"."parent_accounts"
        UNION SELECT "therapist_id", "client_name" FROM "public"."parent_feedback"
        UNION SELECT "therapist_id", "client_name" FROM "public"."recount_event_prompts"
       ) AS "src"
  LEFT JOIN (VALUES ('Max', 8, '#FF8C69'),
                    ('Anthony', 10, '#6B9FD4'),
                    ('Ryan', 12, '#72C472')) AS "legacy" ("client_name", "age", "color")
    ON "legacy"."client_name" = "src"."client_name"
 WHERE "src"."therapist_id" IN (SELECT "id" FROM "auth"."users")
   AND "length"("btrim"("src"."client_name")) > 0
 ORDER BY "src"."therapist_id", "lower"("src"."client_name"), "src"."client_name"
ON CONFLICT DO NOTHING;


-- ── parent_accounts: one parent, several children ───────────
ALTER TABLE "public"."parent_accounts" DROP CONSTRAINT IF EXISTS "parent_accounts_parent_id_key";

CREATE UNIQUE INDEX IF NOT EXISTS "parent_accounts_parent_client_key"
    ON "public"."parent_accounts" ("parent_id", "therapist_id", "client_name");

-- Stored at link time so the therapist dashboard can list who has access
-- without being able to read auth.users.
ALTER TABLE "public"."parent_accounts" ADD COLUMN IF NOT EXISTS "parent_email" "text";

UPDATE "public"."parent_accounts" AS "pa"
   SET "parent_email" = "u"."email"
  FROM "auth"."users" AS "u"
 WHERE "u"."id" = "pa"."parent_id"
   AND "pa"."parent_email" IS NULL;

DROP POLICY IF EXISTS "Therapists read links to own clients" ON "public"."parent_accounts";
CREATE POLICY "Therapists read links to own clients" ON "public"."parent_accounts"
    FOR SELECT TO "authenticated"
    USING ("auth"."uid"() = "therapist_id");

DROP POLICY IF EXISTS "Therapists remove links to own clients" ON "public"."parent_accounts";
CREATE POLICY "Therapists remove links to own clients" ON "public"."parent_accounts"
    FOR DELETE TO "authenticated"
    USING ("auth"."uid"() = "therapist_id");


-- ── link_parent_to_client ───────────────────────────────────
-- Links are created through this function rather than a table policy because
-- the parent is looked up by email in auth.users, which signed-in users cannot
-- read directly.
CREATE OR REPLACE FUNCTION "public"."link_parent_to_client"("p_client_name" "text", "p_parent_email" "text")
    RETURNS "void"
    LANGUAGE "plpgsql"
    SECURITY DEFINER
    SET "search_path" TO ''
    AS $$
declare
  v_therapist uuid := auth.uid();
  v_parent uuid;
  v_email text;
begin
  -- Checked before the email lookup, so only a therapist with a matching
  -- child can learn whether an account exists for an address.
  if v_therapist is null or not exists (
    select 1 from public.clients
     where therapist_id = v_therapist
       and client_name = p_client_name
       and archived_at is null
  ) then
    raise exception 'Client "%" was not found.', p_client_name;
  end if;

  select id, email into v_parent, v_email
    from auth.users
   where lower(email) = lower(btrim(p_parent_email));

  if v_parent is null then
    raise exception 'No account exists for %. Create the parent''s login in Supabase Authentication first.', btrim(p_parent_email);
  end if;

  if v_parent = v_therapist then
    raise exception 'That is your own account. Link the parent''s login instead.';
  end if;

  insert into public.parent_accounts (parent_id, therapist_id, client_name, parent_email)
  values (v_parent, v_therapist, p_client_name, v_email)
  on conflict (parent_id, therapist_id, client_name) do nothing;
end;
$$;

ALTER FUNCTION "public"."link_parent_to_client"("text", "text") OWNER TO "postgres";
REVOKE ALL ON FUNCTION "public"."link_parent_to_client"("text", "text") FROM PUBLIC, "anon";
GRANT EXECUTE ON FUNCTION "public"."link_parent_to_client"("text", "text") TO "authenticated", "service_role";


-- ── delete_client_permanently ───────────────────────────────
-- For a participant who withdraws. Several of these tables only let parents
-- (or the robot) write their rows, so the delete has to run as the owner.
-- The uploaded audio files live in Storage and are removed by the dashboard
-- before it calls this.
CREATE OR REPLACE FUNCTION "public"."delete_client_permanently"("p_client_name" "text")
    RETURNS "void"
    LANGUAGE "plpgsql"
    SECURITY DEFINER
    SET "search_path" TO ''
    AS $$
declare
  v_therapist uuid := auth.uid();
begin
  -- Only archived children can be deleted, so a single mis-click on an active
  -- child can never wipe their data.
  if v_therapist is null or not exists (
    select 1 from public.clients
     where therapist_id = v_therapist
       and client_name = p_client_name
       and archived_at is not null
  ) then
    raise exception 'Client "%" was not found among your removed clients.', p_client_name;
  end if;

  delete from public.client_profiles       where therapist_id = v_therapist and client_name = p_client_name;
  delete from public.session_notes         where therapist_id = v_therapist and client_name = p_client_name;
  delete from public.daily_recap_sessions  where therapist_id = v_therapist and client_name = p_client_name;
  delete from public.client_curriculum     where therapist_id = v_therapist and client_name = p_client_name;
  delete from public.client_progress       where therapist_id = v_therapist and client_name = p_client_name;
  delete from public.conversation_logs     where therapist_id = v_therapist and client_name = p_client_name;
  delete from public.parent_feedback       where therapist_id = v_therapist and client_name = p_client_name;
  delete from public.recount_event_prompts where therapist_id = v_therapist and client_name = p_client_name;
  delete from public.parent_accounts       where therapist_id = v_therapist and client_name = p_client_name;
  delete from public.clients               where therapist_id = v_therapist and client_name = p_client_name;
end;
$$;

ALTER FUNCTION "public"."delete_client_permanently"("text") OWNER TO "postgres";
REVOKE ALL ON FUNCTION "public"."delete_client_permanently"("text") FROM PUBLIC, "anon";
GRANT EXECUTE ON FUNCTION "public"."delete_client_permanently"("text") TO "authenticated", "service_role";

COMMIT;
