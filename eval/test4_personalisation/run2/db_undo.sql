-- Undo db_restore.sql: put Test B's canary sentence and Test 3's titles back
-- (the rows exactly as they were before run 2, md5 06c50053... for the profile).
BEGIN;
UPDATE client_profiles SET profile_text = profile_text || ' She has a pet axolotl called Biscuit.'
WHERE id = '35884b63-4f35-401c-a410-5632896c2991' AND profile_text NOT LIKE '%axolotl%';
INSERT INTO recount_event_prompts (id, parent_id, therapist_id, client_name, title, event_order, created_at, updated_at) VALUES
('7349a73e-0251-49bf-b61f-14e91bd76445', NULL, '6b51a49f-90b7-45a1-8c8f-7d5418dab26d', 'April', 'Played netball in PE', 4, '2026-10-10T15:52:39.8936+00:00', '2026-10-10T15:52:39.8936+00:00'),
('c9523504-bb3e-4096-ac98-41bd1ef7ab69', NULL, '6b51a49f-90b7-45a1-8c8f-7d5418dab26d', 'April', 'Made pasta in food tech', 5, '2026-10-10T15:52:39.8936+00:00', '2026-10-10T15:52:39.8936+00:00'),
('06edb2b1-3f3f-4d78-ac82-eba3ef790c98', NULL, '973c8434-0efe-415a-892d-09a3b4680929', 'April', 'Played netball in PE', 4, '2026-10-10T15:52:39.8936+00:00', '2026-10-10T15:52:39.8936+00:00'),
('61d7936b-05d9-49c8-beab-4d540dd31166', NULL, '973c8434-0efe-415a-892d-09a3b4680929', 'April', 'Made pasta in food tech', 5, '2026-10-10T15:52:39.8936+00:00', '2026-10-10T15:52:39.8936+00:00');
SELECT md5(profile_text) = '06c500538cf704d6e53fddc4244e600f' AS canary_back FROM client_profiles WHERE id = '35884b63-4f35-401c-a410-5632896c2991';
COMMIT;
