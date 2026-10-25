"""Add April's 4th and 5th event titles, for Test 3's two extra stories. Run once.

Added to both Aprils (with context, and the blank one from Test 4), so the two
stay identical apart from their context. The database allows 5 titles per
client (event_order 1-5). New row ids go to test3_rows.json; cleanup.sql
removes them.
"""

import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
rows4 = json.loads((HERE / "../test4_personalisation/setup_rows.json").read_text(encoding="utf-8"))
NEW_TITLES = [(4, "Played netball in PE"), (5, "Made pasta in food tech")]


def psql(sql: str) -> str:
    result = subprocess.run(
        ["docker", "exec", "-i", "supabase_db_ReachyVoiceCode",
         "psql", "-U", "postgres", "-d", "postgres", "-v", "ON_ERROR_STOP=1", "-At"],
        input=sql.encode("utf-8"), capture_output=True,
    )
    if result.returncode != 0:
        raise SystemExit(f"psql failed:\n{result.stderr.decode('utf-8', 'replace')}")
    return result.stdout.decode("utf-8")


therapists = [rows4["with_therapist_id"], rows4["blank_therapist_id"]]
values = ", ".join(f"('{t}', 'April', '{title}', {order})" for t in therapists for order, title in NEW_TITLES)
existing = psql(
    "SELECT count(*) FROM recount_event_prompts WHERE client_name = 'April' AND event_order >= 4 "
    f"AND therapist_id IN ('{therapists[0]}', '{therapists[1]}');").strip()
if existing != "0":
    raise SystemExit("April already has a 4th/5th event title; nothing changed.")

ids = psql(f"""
WITH ins AS (
  INSERT INTO recount_event_prompts (therapist_id, client_name, title, event_order)
  VALUES {values} RETURNING id)
SELECT string_agg(id::text, ',') FROM ins;
""").strip().splitlines()[-1]

(HERE / "test3_rows.json").write_text(json.dumps({"event_title_ids": ids}, indent=2), encoding="utf-8")
quoted = ", ".join(f"'{i}'" for i in ids.split(","))
(HERE / "cleanup.sql").write_text(f"""-- Undo Test 3's database change (April's 4th and 5th event titles, both Aprils).
-- Run this before Test 4's cleanup.sql. Apply with:
--   docker exec -i supabase_db_ReachyVoiceCode psql -U postgres -d postgres -f - < eval/test3_reply_quality/cleanup.sql
DELETE FROM recount_event_prompts WHERE id IN ({quoted});
""", encoding="utf-8")
print(ids)
print(psql("SELECT therapist_id = '" + therapists[0] + "' AS with_context, event_order, title FROM recount_event_prompts "
           "WHERE client_name = 'April' ORDER BY 1 DESC, 2;"))
