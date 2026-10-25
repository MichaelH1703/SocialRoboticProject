"""Seed the local Supabase for Test 4. Run once; refuses to run twice.

With context:    April under eval-test@reachy.local gets a profile, one session
                 note, one recap session with a lesson plan, and 3 event titles.
Without context: eval-test-blank@reachy.local is created (no password, so it
                 cannot log in) with a client April (14) and the same 3 event
                 titles, and nothing else.

Every row added is listed in setup_rows.json, and cleanup.sql removes them all.
Exactly one session note is added, so the robot's unordered note query cannot
pick a different note from run to run.
"""

import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
m = json.loads((HERE / "materials.json").read_text(encoding="utf-8"))
lesson_plan = (HERE / "lesson_plan.txt").read_text(encoding="utf-8")


def lit(text: str) -> str:
    assert "$t4$" not in text
    return f"$t4${text}$t4$"


def psql(sql: str) -> str:
    # Bytes, not text mode: on Windows text mode turns every \n into \r\n on
    # the way in, and the stored lesson plan would then differ from what the
    # dashboard saves.
    result = subprocess.run(
        ["docker", "exec", "-i", "supabase_db_ReachyVoiceCode",
         "psql", "-U", "postgres", "-d", "postgres", "-v", "ON_ERROR_STOP=1", "-At"],
        input=sql.encode("utf-8"), capture_output=True,
    )
    if result.returncode != 0:
        raise SystemExit(f"psql failed:\n{result.stderr.decode('utf-8', 'replace')}")
    return result.stdout.decode("utf-8")


name = m["client_name"]
titles = m["event_titles"]
note = m["session_note"]


def title_rows(var: str) -> str:
    return ", ".join(f"(:'{var}', {lit(name)}, {lit(t)}, {i})" for i, t in enumerate(titles, start=1))


sql = f"""
BEGIN;
SELECT id AS with_id FROM auth.users WHERE email = {lit(m["with_therapist_email"])} \\gset

-- Refuse to run twice, or onto data that is already there.
SELECT EXISTS (SELECT 1 FROM auth.users WHERE email = {lit(m["blank_therapist_email"])})
    OR EXISTS (SELECT 1 FROM session_notes WHERE therapist_id = :'with_id' AND client_name = {lit(name)})
    OR EXISTS (SELECT 1 FROM daily_recap_sessions WHERE therapist_id = :'with_id' AND client_name = {lit(name)})
    OR EXISTS (SELECT 1 FROM recount_event_prompts WHERE therapist_id = :'with_id' AND client_name = {lit(name)})
    AS already_seeded \\gset
\\if :already_seeded
  \\echo 'ALREADY SEEDED: Test 4 data is already there; nothing changed.'
  \\quit
\\endif

INSERT INTO auth.users (instance_id, id, aud, role, email, encrypted_password, email_confirmed_at,
                        confirmation_token, recovery_token, email_change_token_new, email_change,
                        raw_app_meta_data, raw_user_meta_data, created_at, updated_at)
VALUES ('00000000-0000-0000-0000-000000000000', gen_random_uuid(), 'authenticated', 'authenticated',
        {lit(m["blank_therapist_email"])}, '', now(), '', '', '', '',
        '{{"provider":"email","providers":["email"]}}', '{{}}', now(), now())
RETURNING id AS blank_id \\gset

INSERT INTO clients (therapist_id, client_name, age) VALUES (:'blank_id', {lit(name)}, 14)
RETURNING id AS blank_client_id \\gset

UPDATE client_profiles SET profile_text = {lit(m["profile_text"])}
WHERE therapist_id = :'with_id' AND client_name = {lit(name)}
RETURNING id AS profile_id \\gset

INSERT INTO session_notes (therapist_id, client_name, timestamp, note_text)
VALUES (:'with_id', {lit(name)}, {lit(note["timestamp"])}, {lit(note["note_text"])})
RETURNING id AS note_id \\gset

INSERT INTO daily_recap_sessions (therapist_id, client_name, audio_path, original_filename, transcript, lesson_plan)
VALUES (:'with_id', {lit(name)}, 'eval/test4_recap_no_audio', 'Test 4 recap (typed transcript, no audio)',
        {lit(m["recap_transcript"])}, {lit(lesson_plan)})
RETURNING id AS recap_id \\gset

WITH ins AS (
  INSERT INTO recount_event_prompts (therapist_id, client_name, title, event_order)
  VALUES {title_rows("with_id")} RETURNING id)
SELECT string_agg(id::text, ',') AS with_title_ids FROM ins \\gset

WITH ins AS (
  INSERT INTO recount_event_prompts (therapist_id, client_name, title, event_order)
  VALUES {title_rows("blank_id")} RETURNING id)
SELECT string_agg(id::text, ',') AS blank_title_ids FROM ins \\gset

COMMIT;

SELECT json_build_object(
  'with_therapist_id', :'with_id', 'blank_therapist_id', :'blank_id',
  'blank_client_id', :'blank_client_id', 'profile_id', :'profile_id', 'note_id', :'note_id',
  'recap_id', :'recap_id', 'with_title_ids', :'with_title_ids', 'blank_title_ids', :'blank_title_ids');
"""

output = psql(sql)
if "ALREADY SEEDED" in output:
    raise SystemExit(output.strip())
rows = json.loads(output.strip().splitlines()[-1])
(HERE / "setup_rows.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")


def quoted(ids: str) -> str:
    return ", ".join(f"'{i}'" for i in ids.split(","))


(HERE / "cleanup.sql").write_text(f"""-- Undo Test 4's database changes. Apply with:
--   docker exec -i supabase_db_ReachyVoiceCode psql -U postgres -d postgres -f - < eval/test4_personalisation/cleanup.sql
BEGIN;
DELETE FROM recount_event_prompts WHERE id IN ({quoted(rows["with_title_ids"])}, {quoted(rows["blank_title_ids"])});
DELETE FROM daily_recap_sessions WHERE id = {rows["recap_id"]};
DELETE FROM session_notes WHERE id = '{rows["note_id"]}';
UPDATE client_profiles SET profile_text = '' WHERE id = '{rows["profile_id"]}';
DELETE FROM clients WHERE id = '{rows["blank_client_id"]}';
DELETE FROM auth.users WHERE id = '{rows["blank_therapist_id"]}';
COMMIT;
""", encoding="utf-8")

print(json.dumps(rows, indent=2))
