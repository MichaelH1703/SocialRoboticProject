


SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;


COMMENT ON SCHEMA "public" IS 'standard public schema';



CREATE EXTENSION IF NOT EXISTS "pg_stat_statements" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "pgcrypto" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "supabase_vault" WITH SCHEMA "vault";






CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA "extensions";






CREATE OR REPLACE FUNCTION "public"."set_updated_at"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
begin
  new.updated_at = now();
  return new;
end;
$$;


ALTER FUNCTION "public"."set_updated_at"() OWNER TO "postgres";

SET default_tablespace = '';

SET default_table_access_method = "heap";


CREATE TABLE IF NOT EXISTS "public"."client_curriculum" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "therapist_id" "uuid",
    "client_name" "text" NOT NULL,
    "lesson_name" "text" NOT NULL,
    "lesson_order" integer DEFAULT 0
);


ALTER TABLE "public"."client_curriculum" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."client_profiles" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "therapist_id" "uuid",
    "client_name" "text" NOT NULL,
    "profile_text" "text" DEFAULT ''::"text"
);


ALTER TABLE "public"."client_profiles" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."client_progress" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "therapist_id" "uuid",
    "client_name" "text" NOT NULL,
    "category" "text" NOT NULL,
    "lessons" "text"[] DEFAULT '{}'::"text"[]
);


ALTER TABLE "public"."client_progress" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."conversation_logs" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "therapist_id" "uuid",
    "client_name" "text" NOT NULL,
    "timestamp" "text" NOT NULL,
    "user_text" "text" NOT NULL,
    "assistant_text" "text" NOT NULL
);


ALTER TABLE "public"."conversation_logs" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."daily_recap_sessions" (
    "id" bigint NOT NULL,
    "therapist_id" "uuid" NOT NULL,
    "client_name" "text" NOT NULL,
    "audio_path" "text" NOT NULL,
    "original_filename" "text",
    "transcript" "text",
    "uploaded_at" timestamp with time zone DEFAULT "now"(),
    "lesson_plan" "text"
);


ALTER TABLE "public"."daily_recap_sessions" OWNER TO "postgres";


ALTER TABLE "public"."daily_recap_sessions" ALTER COLUMN "id" ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME "public"."daily_recap_sessions_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);



CREATE TABLE IF NOT EXISTS "public"."lesson_plan_docs" (
    "id" bigint NOT NULL,
    "therapist_id" "uuid",
    "title" "text" NOT NULL,
    "description" "text",
    "category" "text",
    "storage_path" "text" NOT NULL,
    "uploaded_at" timestamp with time zone DEFAULT "now"(),
    "content" "text"
);


ALTER TABLE "public"."lesson_plan_docs" OWNER TO "postgres";


ALTER TABLE "public"."lesson_plan_docs" ALTER COLUMN "id" ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME "public"."lesson_plan_docs_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);



CREATE TABLE IF NOT EXISTS "public"."parent_accounts" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "parent_id" "uuid" NOT NULL,
    "therapist_id" "uuid" NOT NULL,
    "client_name" "text" NOT NULL
);


ALTER TABLE "public"."parent_accounts" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."parent_feedback" (
    "id" integer NOT NULL,
    "parent_id" "uuid" NOT NULL,
    "therapist_id" "uuid" NOT NULL,
    "client_name" "text" NOT NULL,
    "timestamp" "text" NOT NULL,
    "feedback_text" "text" NOT NULL
);


ALTER TABLE "public"."parent_feedback" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "public"."parent_feedback_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "public"."parent_feedback_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."parent_feedback_id_seq" OWNED BY "public"."parent_feedback"."id";



CREATE TABLE IF NOT EXISTS "public"."recount_event_prompts" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "parent_id" "uuid",
    "therapist_id" "uuid" NOT NULL,
    "client_name" "text" NOT NULL,
    "title" "text" NOT NULL,
    "event_order" integer NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "recount_event_prompts_event_order_check" CHECK ((("event_order" >= 1) AND ("event_order" <= 5)))
);


ALTER TABLE "public"."recount_event_prompts" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."session_notes" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "therapist_id" "uuid",
    "client_name" "text" NOT NULL,
    "timestamp" "text" NOT NULL,
    "note_text" "text" NOT NULL
);


ALTER TABLE "public"."session_notes" OWNER TO "postgres";


ALTER TABLE ONLY "public"."parent_feedback" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."parent_feedback_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."client_curriculum"
    ADD CONSTRAINT "client_curriculum_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."client_curriculum"
    ADD CONSTRAINT "client_curriculum_therapist_id_client_name_lesson_name_key" UNIQUE ("therapist_id", "client_name", "lesson_name");



ALTER TABLE ONLY "public"."client_profiles"
    ADD CONSTRAINT "client_profiles_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."client_profiles"
    ADD CONSTRAINT "client_profiles_therapist_id_client_name_key" UNIQUE ("therapist_id", "client_name");



ALTER TABLE ONLY "public"."client_progress"
    ADD CONSTRAINT "client_progress_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."client_progress"
    ADD CONSTRAINT "client_progress_therapist_id_client_name_category_key" UNIQUE ("therapist_id", "client_name", "category");



ALTER TABLE ONLY "public"."conversation_logs"
    ADD CONSTRAINT "conversation_logs_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."daily_recap_sessions"
    ADD CONSTRAINT "daily_recap_sessions_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."lesson_plan_docs"
    ADD CONSTRAINT "lesson_plan_docs_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."parent_accounts"
    ADD CONSTRAINT "parent_accounts_parent_id_key" UNIQUE ("parent_id");



ALTER TABLE ONLY "public"."parent_accounts"
    ADD CONSTRAINT "parent_accounts_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."parent_feedback"
    ADD CONSTRAINT "parent_feedback_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."recount_event_prompts"
    ADD CONSTRAINT "recount_event_prompts_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."session_notes"
    ADD CONSTRAINT "session_notes_pkey" PRIMARY KEY ("id");



CREATE OR REPLACE TRIGGER "recount_event_prompts_set_updated_at" BEFORE UPDATE ON "public"."recount_event_prompts" FOR EACH ROW EXECUTE FUNCTION "public"."set_updated_at"();



ALTER TABLE ONLY "public"."client_curriculum"
    ADD CONSTRAINT "client_curriculum_therapist_id_fkey" FOREIGN KEY ("therapist_id") REFERENCES "auth"."users"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."client_profiles"
    ADD CONSTRAINT "client_profiles_therapist_id_fkey" FOREIGN KEY ("therapist_id") REFERENCES "auth"."users"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."client_progress"
    ADD CONSTRAINT "client_progress_therapist_id_fkey" FOREIGN KEY ("therapist_id") REFERENCES "auth"."users"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."conversation_logs"
    ADD CONSTRAINT "conversation_logs_therapist_id_fkey" FOREIGN KEY ("therapist_id") REFERENCES "auth"."users"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."lesson_plan_docs"
    ADD CONSTRAINT "lesson_plan_docs_therapist_id_fkey" FOREIGN KEY ("therapist_id") REFERENCES "auth"."users"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."parent_accounts"
    ADD CONSTRAINT "parent_accounts_parent_id_fkey" FOREIGN KEY ("parent_id") REFERENCES "auth"."users"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."parent_feedback"
    ADD CONSTRAINT "parent_feedback_parent_id_fkey" FOREIGN KEY ("parent_id") REFERENCES "auth"."users"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."recount_event_prompts"
    ADD CONSTRAINT "recount_event_prompts_parent_id_fkey" FOREIGN KEY ("parent_id") REFERENCES "auth"."users"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."session_notes"
    ADD CONSTRAINT "session_notes_therapist_id_fkey" FOREIGN KEY ("therapist_id") REFERENCES "auth"."users"("id") ON DELETE CASCADE;



CREATE POLICY "Own data only" ON "public"."client_curriculum" USING (("auth"."uid"() = "therapist_id"));



CREATE POLICY "Own data only" ON "public"."client_profiles" USING (("auth"."uid"() = "therapist_id"));



CREATE POLICY "Own data only" ON "public"."client_progress" USING (("auth"."uid"() = "therapist_id"));



CREATE POLICY "Own data only" ON "public"."session_notes" USING (("auth"."uid"() = "therapist_id"));



CREATE POLICY "Parents can delete their own recount prompts" ON "public"."recount_event_prompts" FOR DELETE USING (("auth"."uid"() = "parent_id"));



CREATE POLICY "Parents can insert their own recount prompts" ON "public"."recount_event_prompts" FOR INSERT WITH CHECK (("auth"."uid"() = "parent_id"));



CREATE POLICY "Parents can read their child's curriculum" ON "public"."client_curriculum" FOR SELECT USING ((EXISTS ( SELECT 1
   FROM "public"."parent_accounts"
  WHERE (("parent_accounts"."parent_id" = "auth"."uid"()) AND ("parent_accounts"."therapist_id" = "client_curriculum"."therapist_id") AND ("parent_accounts"."client_name" = "client_curriculum"."client_name")))));



CREATE POLICY "Parents can read their child's progress" ON "public"."client_progress" FOR SELECT USING ((EXISTS ( SELECT 1
   FROM "public"."parent_accounts"
  WHERE (("parent_accounts"."parent_id" = "auth"."uid"()) AND ("parent_accounts"."therapist_id" = "client_progress"."therapist_id") AND ("parent_accounts"."client_name" = "client_progress"."client_name")))));



CREATE POLICY "Parents can read their child's session notes" ON "public"."session_notes" FOR SELECT USING ((EXISTS ( SELECT 1
   FROM "public"."parent_accounts"
  WHERE (("parent_accounts"."parent_id" = "auth"."uid"()) AND ("parent_accounts"."therapist_id" = "session_notes"."therapist_id") AND ("parent_accounts"."client_name" = "session_notes"."client_name")))));



CREATE POLICY "Parents can read their own account" ON "public"."parent_accounts" FOR SELECT USING (("parent_id" = "auth"."uid"()));



CREATE POLICY "Parents can update their own recount prompts" ON "public"."recount_event_prompts" FOR UPDATE USING (("auth"."uid"() = "parent_id")) WITH CHECK (("auth"."uid"() = "parent_id"));



CREATE POLICY "Parents can view their own recount prompts" ON "public"."recount_event_prompts" FOR SELECT USING (("auth"."uid"() = "parent_id"));



CREATE POLICY "Therapists manage own docs" ON "public"."lesson_plan_docs" USING (("auth"."uid"() = "therapist_id"));



CREATE POLICY "Users can delete their own daily recap sessions" ON "public"."daily_recap_sessions" FOR DELETE USING (("auth"."uid"() = "therapist_id"));



CREATE POLICY "Users can insert their own daily recap sessions" ON "public"."daily_recap_sessions" FOR INSERT WITH CHECK (("auth"."uid"() = "therapist_id"));



CREATE POLICY "Users can update their own daily recap sessions" ON "public"."daily_recap_sessions" FOR UPDATE USING (("auth"."uid"() = "therapist_id"));



CREATE POLICY "Users can view their own daily recap sessions" ON "public"."daily_recap_sessions" FOR SELECT USING (("auth"."uid"() = "therapist_id"));



ALTER TABLE "public"."client_curriculum" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."client_profiles" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."client_progress" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."conversation_logs" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."daily_recap_sessions" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."lesson_plan_docs" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."parent_accounts" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."parent_feedback" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "parents manage own feedback" ON "public"."parent_feedback" USING (("auth"."uid"() = "parent_id"));



CREATE POLICY "parents read own link" ON "public"."parent_accounts" FOR SELECT USING (("auth"."uid"() = "parent_id"));



ALTER TABLE "public"."recount_event_prompts" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."session_notes" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "therapists can delete own daily recap sessions" ON "public"."daily_recap_sessions" FOR DELETE TO "authenticated" USING (("auth"."uid"() = "therapist_id"));



CREATE POLICY "therapists can insert own conversation logs" ON "public"."conversation_logs" FOR INSERT TO "authenticated" WITH CHECK (("auth"."uid"() = "therapist_id"));



CREATE POLICY "therapists can insert own daily recap sessions" ON "public"."daily_recap_sessions" FOR INSERT TO "authenticated" WITH CHECK (("auth"."uid"() = "therapist_id"));



CREATE POLICY "therapists can update own daily recap sessions" ON "public"."daily_recap_sessions" FOR UPDATE TO "authenticated" USING (("auth"."uid"() = "therapist_id")) WITH CHECK (("auth"."uid"() = "therapist_id"));



CREATE POLICY "therapists can view own daily recap sessions" ON "public"."daily_recap_sessions" FOR SELECT TO "authenticated" USING (("auth"."uid"() = "therapist_id"));



CREATE POLICY "therapists read feedback" ON "public"."parent_feedback" FOR SELECT USING (("auth"."uid"() = "therapist_id"));





ALTER PUBLICATION "supabase_realtime" OWNER TO "postgres";


GRANT USAGE ON SCHEMA "public" TO "postgres";
GRANT USAGE ON SCHEMA "public" TO "anon";
GRANT USAGE ON SCHEMA "public" TO "authenticated";
GRANT USAGE ON SCHEMA "public" TO "service_role";






















































































































































GRANT ALL ON FUNCTION "public"."set_updated_at"() TO "anon";
GRANT ALL ON FUNCTION "public"."set_updated_at"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."set_updated_at"() TO "service_role";


















GRANT ALL ON TABLE "public"."client_curriculum" TO "anon";
GRANT ALL ON TABLE "public"."client_curriculum" TO "authenticated";
GRANT ALL ON TABLE "public"."client_curriculum" TO "service_role";



GRANT ALL ON TABLE "public"."client_profiles" TO "anon";
GRANT ALL ON TABLE "public"."client_profiles" TO "authenticated";
GRANT ALL ON TABLE "public"."client_profiles" TO "service_role";



GRANT ALL ON TABLE "public"."client_progress" TO "anon";
GRANT ALL ON TABLE "public"."client_progress" TO "authenticated";
GRANT ALL ON TABLE "public"."client_progress" TO "service_role";



GRANT ALL ON TABLE "public"."conversation_logs" TO "anon";
GRANT ALL ON TABLE "public"."conversation_logs" TO "authenticated";
GRANT ALL ON TABLE "public"."conversation_logs" TO "service_role";



GRANT ALL ON TABLE "public"."daily_recap_sessions" TO "anon";
GRANT ALL ON TABLE "public"."daily_recap_sessions" TO "authenticated";
GRANT ALL ON TABLE "public"."daily_recap_sessions" TO "service_role";



GRANT ALL ON SEQUENCE "public"."daily_recap_sessions_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."daily_recap_sessions_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."daily_recap_sessions_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."lesson_plan_docs" TO "anon";
GRANT ALL ON TABLE "public"."lesson_plan_docs" TO "authenticated";
GRANT ALL ON TABLE "public"."lesson_plan_docs" TO "service_role";



GRANT ALL ON SEQUENCE "public"."lesson_plan_docs_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."lesson_plan_docs_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."lesson_plan_docs_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."parent_accounts" TO "anon";
GRANT ALL ON TABLE "public"."parent_accounts" TO "authenticated";
GRANT ALL ON TABLE "public"."parent_accounts" TO "service_role";



GRANT ALL ON TABLE "public"."parent_feedback" TO "anon";
GRANT ALL ON TABLE "public"."parent_feedback" TO "authenticated";
GRANT ALL ON TABLE "public"."parent_feedback" TO "service_role";



GRANT ALL ON SEQUENCE "public"."parent_feedback_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."parent_feedback_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."parent_feedback_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."recount_event_prompts" TO "anon";
GRANT ALL ON TABLE "public"."recount_event_prompts" TO "authenticated";
GRANT ALL ON TABLE "public"."recount_event_prompts" TO "service_role";



GRANT ALL ON TABLE "public"."session_notes" TO "anon";
GRANT ALL ON TABLE "public"."session_notes" TO "authenticated";
GRANT ALL ON TABLE "public"."session_notes" TO "service_role";









ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "service_role";






ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "service_role";






ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "service_role";































