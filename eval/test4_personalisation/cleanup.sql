-- Undo Test 4's database changes. Apply with:
--   docker exec -i supabase_db_ReachyVoiceCode psql -U postgres -d postgres -f - < eval/test4_personalisation/cleanup.sql
BEGIN;
DELETE FROM recount_event_prompts WHERE id IN ('09e552a2-161a-4f92-8777-b31e3654cf9a', 'fff0e108-f5c0-487f-9166-a8fd4e8e7f2b', 'b5bd50cf-dbb4-4fba-baea-30bfb081e73e', '556907c7-6723-438f-b5e4-88bfa48ad42d', 'f4fb5c77-2467-47f3-ae58-b3a5019642ac', '449cd5d2-f5fc-4094-832a-cece2f46c70d');
DELETE FROM daily_recap_sessions WHERE id = 18;
DELETE FROM session_notes WHERE id = 'ab5c8459-1b7a-4528-b274-9f0f26ad583a';
UPDATE client_profiles SET profile_text = '' WHERE id = '35884b63-4f35-401c-a410-5632896c2991';
DELETE FROM clients WHERE id = '4835190a-2f00-45db-9341-1b70dd8ec8c4';
DELETE FROM auth.users WHERE id = '973c8434-0efe-415a-892d-09a3b4680929';
COMMIT;
