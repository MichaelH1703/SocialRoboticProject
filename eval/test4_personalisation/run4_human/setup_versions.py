"""Seed run 4's database state (approved 2026-10-16). Run once; refuses to run twice.

1. Checks v1 (April under eval-test@reachy.local) is as in runs 1-3: profile md5
   da5f073a..., no Test B canary.
2. Generates v2-v4's lesson plans with lesson_planner.py from their recap
   transcripts (versions.json), as v1's was, once: saved to lesson_plan_vN.txt
   and reused if present.
3. In one transaction: removes the extra event titles re-added after run 3
   (both Aprils back to their 3 original titles; the removed rows are saved
   and restore_titles.sql puts them back), and adds v2-v4 the way ../setup_db.py
   added the blank April: a no-password therapist account, a client April (14),
   a profile, one session note, one recap with its lesson plan, and the same 3
   event titles.
4. Writes setup_rows.json and cleanup.sql (removes v2-v4), then saves every
   condition's system prompt to _unblinding/prompts/ and checks v1's and the
   blank's still match run 1's.
"""

import difflib
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
T4 = HERE.parent
PROJECT = T4.parent.parent
PYTHON = PROJECT / "venv" / "Scripts" / "python.exe"
v = json.loads((HERE / "versions.json").read_text(encoding="utf-8"))
m = json.loads((T4 / "materials.json").read_text(encoding="utf-8"))
run1_rows = json.loads((T4 / "setup_rows.json").read_text(encoding="utf-8"))
NEW = ["v2", "v3", "v4"]
NAME = m["client_name"]


def lit(text: str) -> str:
    assert "$t4$" not in text
    return f"$t4${text}$t4$"


def psql(sql: str) -> str:
    # Bytes, as ../setup_db.py: text mode would store \r\n in the lesson plans.
    result = subprocess.run(
        ["docker", "exec", "-i", "supabase_db_ReachyVoiceCode",
         "psql", "-U", "postgres", "-d", "postgres", "-v", "ON_ERROR_STOP=1", "-At"],
        input=sql.encode("utf-8"), capture_output=True)
    if result.returncode != 0:
        raise SystemExit(f"psql failed:\n{result.stderr.decode('utf-8', 'replace')}")
    return result.stdout.decode("utf-8")


def system_prompt(therapist_id: str) -> str:
    env = dict(os.environ, THERAPIST_ID=therapist_id, CLIENT_NAME=NAME, PYTHONIOENCODING="utf-8")
    out = subprocess.run([str(PYTHON), "reachy_text_chat.py", "--no-save"], input="/prompt\n/quit\n",
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                         cwd=PROJECT, env=env, timeout=600).stdout
    if "You: " not in out:
        raise SystemExit(f"Could not get the prompt (is Ollama running?):\n{out[-1500:]}")
    return out.split("You: ")[1]


def main() -> None:
    if (HERE / "setup_rows.json").exists():
        raise SystemExit("setup_rows.json exists: run 4's database setup has already been done.")
    with_id, blank_id = run1_rows["with_therapist_id"], run1_rows["blank_therapist_id"]

    # 1. v1 as in runs 1-3.
    state = psql(f"SELECT md5(profile_text), profile_text ILIKE '%axolotl%' FROM client_profiles "
                 f"WHERE id = '{run1_rows['profile_id']}';").strip()
    if state != "da5f073a15e45f1873a097232e742596|f":
        raise SystemExit(f"v1's profile is not as in runs 1-3 ({state}). Nothing changed.")

    # 2. Lesson plans, generated once.
    sys.path.insert(0, str(PROJECT))
    from lesson_planner import generate_lesson_plan_from_transcript
    plans = {}
    for key in NEW:
        path = HERE / f"lesson_plan_{key}.txt"
        if not path.exists():
            print(f"Generating {key}'s lesson plan...", flush=True)
            path.write_text(generate_lesson_plan_from_transcript(v[key]["recap_transcript"]), encoding="utf-8")
        plans[key] = path.read_text(encoding="utf-8")

    # 3a. The extra titles to remove: every April title row under the two run-1
    # therapists that is not one of run 1's own 6.
    original = run1_rows["with_title_ids"].split(",") + run1_rows["blank_title_ids"].split(",")
    extra = json.loads(psql(
        f"SELECT coalesce(json_agg(t ORDER BY therapist_id, event_order), '[]') FROM recount_event_prompts t "
        f"WHERE client_name = {lit(NAME)} AND therapist_id IN ('{with_id}', '{blank_id}') "
        f"AND id NOT IN ({', '.join(repr(i) for i in original)});").strip())
    (HERE / "removed_titles.json").write_text(json.dumps(extra, indent=2), encoding="utf-8")
    cols = ["id", "parent_id", "therapist_id", "client_name", "title", "event_order", "created_at", "updated_at"]

    def val(x) -> str:
        return "NULL" if x is None else (str(x) if isinstance(x, int) else "'" + str(x).replace("'", "''") + "'")
    restore = ",\n".join("(" + ", ".join(val(r[c]) for c in cols) + ")" for r in extra)
    (HERE / "restore_titles.sql").write_text(
        "-- Put back the event titles setup_versions.py removed (removed_titles.json).\n"
        f"INSERT INTO recount_event_prompts ({', '.join(cols)}) VALUES\n{restore};\n" if extra else
        "-- setup_versions.py removed no titles.\n", encoding="utf-8")

    # 3b. One transaction: remove the extra titles, add v2-v4.
    blocks = []
    for key in NEW:
        x = v[key]
        titles = ", ".join(f"(:'{key}_id', {lit(NAME)}, {lit(t)}, {i})" for i, t in enumerate(m["event_titles"], 1))
        blocks.append(f"""
INSERT INTO auth.users (instance_id, id, aud, role, email, encrypted_password, email_confirmed_at,
                        confirmation_token, recovery_token, email_change_token_new, email_change,
                        raw_app_meta_data, raw_user_meta_data, created_at, updated_at)
VALUES ('00000000-0000-0000-0000-000000000000', gen_random_uuid(), 'authenticated', 'authenticated',
        {lit(x["email"])}, '', now(), '', '', '', '',
        '{{"provider":"email","providers":["email"]}}', '{{}}', now(), now())
RETURNING id AS {key}_id \\gset
INSERT INTO clients (therapist_id, client_name, age) VALUES (:'{key}_id', {lit(NAME)}, 14)
RETURNING id AS {key}_client_id \\gset
INSERT INTO client_profiles (therapist_id, client_name, profile_text) VALUES (:'{key}_id', {lit(NAME)}, {lit(x["profile_text"])})
RETURNING id AS {key}_profile_id \\gset
INSERT INTO session_notes (therapist_id, client_name, timestamp, note_text)
VALUES (:'{key}_id', {lit(NAME)}, {lit(x["session_note"]["timestamp"])}, {lit(x["session_note"]["note_text"])})
RETURNING id AS {key}_note_id \\gset
INSERT INTO daily_recap_sessions (therapist_id, client_name, audio_path, original_filename, transcript, lesson_plan)
VALUES (:'{key}_id', {lit(NAME)}, 'eval/test4_run4_recap_no_audio', 'Test 4 run 4 {key} recap (typed transcript, no audio)',
        {lit(x["recap_transcript"])}, {lit(plans[key])})
RETURNING id AS {key}_recap_id \\gset
WITH ins AS (INSERT INTO recount_event_prompts (therapist_id, client_name, title, event_order)
             VALUES {titles} RETURNING id)
SELECT string_agg(id::text, ',') AS {key}_title_ids FROM ins \\gset""")
    emails = ", ".join(lit(v[k]["email"]) for k in NEW)
    fields = ", ".join(f"'{k}_{f}', :'{k}_{f}'" for k in NEW
                       for f in ("id", "client_id", "profile_id", "note_id", "recap_id", "title_ids"))
    extra_ids = ", ".join(repr(r["id"]) for r in extra) or "NULL"
    out = psql(f"""
BEGIN;
SELECT EXISTS (SELECT 1 FROM auth.users WHERE email IN ({emails})) AS already \\gset
\\if :already
  \\echo 'ALREADY SEEDED'
  \\quit
\\endif
DELETE FROM recount_event_prompts WHERE id IN ({extra_ids});
{"".join(blocks)}
COMMIT;
SELECT json_build_object({fields});
""")
    if "ALREADY SEEDED" in out:
        raise SystemExit("A run 4 therapist account already exists. Nothing changed.")
    rows = json.loads(out.strip().splitlines()[-1])
    rows.update({"v1_id": with_id, "blank_id": blank_id, "removed_title_ids": [r["id"] for r in extra]})
    (HERE / "setup_rows.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")

    # 4. Cleanup for v2-v4.
    q = lambda ids: ", ".join(f"'{i}'" for i in ids.split(","))  # noqa: E731
    lines = ["-- Undo setup_versions.py's additions (v2-v4). restore_titles.sql puts the removed titles back.",
             "BEGIN;"]
    for k in NEW:
        lines += [f"DELETE FROM recount_event_prompts WHERE id IN ({q(rows[k + '_title_ids'])});",
                  f"DELETE FROM daily_recap_sessions WHERE id = {rows[k + '_recap_id']};",
                  f"DELETE FROM session_notes WHERE id = '{rows[k + '_note_id']}';",
                  f"DELETE FROM client_profiles WHERE id = '{rows[k + '_profile_id']}';",
                  f"DELETE FROM clients WHERE id = '{rows[k + '_client_id']}';",
                  f"DELETE FROM auth.users WHERE id = '{rows[k + '_id']}';"]
    (HERE / "cleanup.sql").write_text("\n".join(lines + ["COMMIT;"]) + "\n", encoding="utf-8")

    # 5. Every condition's prompt; v1 and the blank must still match run 1's.
    prompts = HERE / "_unblinding" / "prompts"
    prompts.mkdir(parents=True, exist_ok=True)
    ids = {"v1": with_id, "blank": blank_id, **{k: rows[k + "_id"] for k in NEW}}
    text = {}
    for key, tid in ids.items():
        text[key] = system_prompt(tid)
        (prompts / f"prompt_{key}.txt").write_text(text[key], encoding="utf-8")
    run1 = {k: (T4 / "_unblinding" / f"prompt_{n}.txt").read_text(encoding="utf-8")
            for k, n in (("v1", "with"), ("blank", "without"))}
    print(f"Removed {len(extra)} extra title rows; added v2-v4 ({', '.join(rows[k + '_id'] for k in NEW)}).")
    for k in ("v1", "blank"):
        print(f"{k} prompt identical to run 1's: {text[k] == run1[k]}")
    for k in NEW:
        changed = [l for l in difflib.unified_diff(text["v1"].splitlines(), text[k].splitlines(), lineterm="", n=0)
                   if l[:1] in "+-" and l[:3] not in ("+++", "---")]
        print(f"{k} prompt: {len(changed)} lines differ from v1's (md5 {hashlib.md5(text[k].encode()).hexdigest()[:8]})")


if __name__ == "__main__":
    main()
