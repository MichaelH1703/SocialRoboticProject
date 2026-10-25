-- Run 2 pre-step (approved 2026-10-12): put the database back to run 1's state.
-- Removes Test B's canary sentence from April's profile and Test 3's 4th/5th event
-- titles. Undo with db_undo.sql. Apply with:
--   docker exec -i supabase_db_ReachyVoiceCode psql -U postgres -d postgres -v ON_ERROR_STOP=1 -f - < db_restore.sql
BEGIN;
UPDATE client_profiles SET profile_text = replace(profile_text, ' She has a pet axolotl called Biscuit.', '')
WHERE id = '35884b63-4f35-401c-a410-5632896c2991';
DELETE FROM recount_event_prompts WHERE id IN ('7349a73e-0251-49bf-b61f-14e91bd76445', 'c9523504-bb3e-4096-ac98-41bd1ef7ab69', '06edb2b1-3f3f-4d78-ac82-eba3ef790c98', '61d7936b-05d9-49c8-beab-4d540dd31166');
DO $$ BEGIN
  IF (SELECT md5(profile_text) FROM client_profiles WHERE id = '35884b63-4f35-401c-a410-5632896c2991')
     <> 'da5f073a15e45f1873a097232e742596' THEN RAISE EXCEPTION 'profile not at its run-1 text'; END IF;
  IF (SELECT count(*) FROM recount_event_prompts WHERE client_name = 'April'
      AND therapist_id IN ('6b51a49f-90b7-45a1-8c8f-7d5418dab26d', '973c8434-0efe-415a-892d-09a3b4680929')) <> 6
     THEN RAISE EXCEPTION 'expected 3 titles per April'; END IF;
END $$;
COMMIT;
