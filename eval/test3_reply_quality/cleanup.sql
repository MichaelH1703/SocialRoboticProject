-- Undo Test 3's database change (April's 4th and 5th event titles, both Aprils).
-- Run this before Test 4's cleanup.sql. Apply with:
--   docker exec -i supabase_db_ReachyVoiceCode psql -U postgres -d postgres -f - < eval/test3_reply_quality/cleanup.sql
DELETE FROM recount_event_prompts WHERE id IN ('83107d4d-c1d8-4927-8135-be3c27196bec', 'aa68bfb3-d69e-4c9e-ae7c-50f4c32a7028', '40977599-2f27-40a3-a60b-6cf20b757521', '743eaaf6-ed21-425e-8f49-dc8d3552e7a5');
