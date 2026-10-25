"""Run Test B: 5 sessions as Ben, with saving ON, asking leading questions.

    python run_sessions.py run [S1 ...]   runs the given sessions (default: all, in
                                         scripts.json's order) that have no
                                         raw/<session>_db.json yet

Each session runs in a brand-new process that imports reachy_text_chat.py
unchanged, with saving on as in a real session, after every model has been
unloaded from Ollama (same isolation as Test 3's run_sessions.py). Ben's lines
are fixed (scripts.json). The context Reachy got is printed into the raw log.

Around each session the parent lists every conversation_logs and safety_events
id in the database; the ids that are new afterwards are that session's rows,
whoever they were saved under. They go to raw/<session>_db.json, and their ids
are added to cleanup.sql.

Outputs per session: raw/<session>.txt (process output), raw/<session>.json
(turns), raw/<session>_db.json (new rows). If a .txt exists without its
_db.json, the session was interrupted after it may have saved: the run stops
so a person can check before anything is re-run.
"""

import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent.parent
PYTHON = PROJECT / "venv" / "Scripts" / "python.exe"
RAW = HERE / "raw"
OLLAMA = "http://localhost:11434"

m = json.loads((HERE / "scripts.json").read_text(encoding="utf-8"))
CANARY = re.compile(r"\b(" + "|".join(m["canary_words"]) + r")s?\b", re.I)


def psql(sql: str) -> str:
    result = subprocess.run(
        ["docker", "exec", "-i", "supabase_db_ReachyVoiceCode",
         "psql", "-U", "postgres", "-d", "postgres", "-v", "ON_ERROR_STOP=1", "-At"],
        input=sql.encode("utf-8"), capture_output=True)
    if result.returncode != 0:
        raise SystemExit(f"psql failed:\n{result.stderr.decode('utf-8', 'replace')}")
    return result.stdout.decode("utf-8").strip()


def therapist_id() -> str:
    return psql(f"SELECT id FROM auth.users WHERE email = '{m['therapist_email']}';")


def session_process(session: str) -> None:
    """One session, in this process. Output is the session's raw log."""
    os.chdir(PROJECT)
    sys.path.insert(0, str(PROJECT))
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    import reachy_text_chat as rtc

    assert rtc.SAVE_TO_SUPABASE, "saving must be on for Test B"
    if not rtc.check_ollama():
        raise SystemExit(f"Could not reach Ollama at {rtc.OLLAMA_BASE_URL}")
    print(f"[Test B] session {session} as {rtc.CLIENT_NAME}, therapist {rtc.THERAPIST_ID}, saving ON")
    print(f"[Isolation] new process pid {os.getpid()}; Reachy chat history {len(rtc.chat_history)} items, "
          f"conversation log {len(rtc.conversation_log)} rows; models loaded in Ollama: {loaded_models() or 'none'}")
    rtc.warm_up_model()

    context = rtc.build_context_from_supabase(rtc.THERAPIST_ID, rtc.CLIENT_NAME)
    print(f"[Context] canary words in Reachy's context: {CANARY.findall(context) or 'none'}")
    print(context)
    print("[Context end]")

    chat = rtc.TextSession(context)
    chat.update_instructions()
    chat.greet()
    greeting = next(e["text"] for e in reversed(rtc.chat_history) if e["role"] == "assistant")
    turns = [{"ben": None, "reachy": greeting}]

    for line in m["sessions"][session]:
        print(f"You: {line}", flush=True)
        before = len(rtc.chat_history)
        chat.handle(line)
        reply = " ".join(e["text"] for e in rtc.chat_history[before:] if e["role"] == "assistant")
        turns.append({"ben": line, "reachy": reply})
        if chat.ended:
            break

    # What main() does at exit.
    print()
    rtc.save_conversation_on_exit(rtc.THERAPIST_ID, rtc.CLIENT_NAME, rtc.conversation_log)
    rtc.print_safety_summary()

    (RAW / f"{session}.json").write_text(json.dumps({
        "session": session, "client_name": rtc.CLIENT_NAME, "therapist_id": rtc.THERAPIST_ID,
        "ended_by_goodbye": chat.ended, "context_canary_hits": CANARY.findall(context),
        "log_rows_in_memory": len(rtc.conversation_log), "safety_events_fired": len(rtc.safety_log),
        "turns": turns,
    }, indent=2, ensure_ascii=False), encoding="utf-8")


def loaded_models() -> list:
    with urllib.request.urlopen(f"{OLLAMA}/api/ps", timeout=10) as resp:
        return [model["name"] for model in json.load(resp).get("models", [])]


def unload_all_models() -> str:
    names = loaded_models()
    for name in names:
        request = urllib.request.Request(
            f"{OLLAMA}/api/generate", data=json.dumps({"model": name, "keep_alive": 0}).encode("utf-8"),
            headers={"Content-Type": "application/json"})
        urllib.request.urlopen(request, timeout=60).read()
    deadline = time.time() + 60
    while loaded_models():
        if time.time() > deadline:
            raise SystemExit(f"Ollama did not unload: {loaded_models()}")
        time.sleep(0.5)
    return f"unloaded {', '.join(names) or 'nothing'}; confirmed none loaded"


def ids(table: str) -> set:
    return set(psql(f"SELECT id FROM {table};").split())


def new_rows(table: str, columns: str, before: set) -> list:
    after = ids(table) - before
    if not after:
        return []
    id_list = ", ".join(f"'{i}'" for i in sorted(after))
    out = psql(f"SELECT json_agg(t) FROM (SELECT {columns} FROM {table} WHERE id IN ({id_list})) t;")
    return json.loads(out)


def add_to_cleanup(session: str, logs: list, events: list) -> None:
    path = HERE / "cleanup.sql"
    sql = path.read_text(encoding="utf-8")
    lines = []
    for table, rows in (("conversation_logs", logs), ("safety_events", events)):
        if rows:
            id_list = ", ".join(f"'{r['id']}'" for r in rows)
            lines.append(f"DELETE FROM {table} WHERE id IN ({id_list});  -- {session}")
    if lines:
        marker = "-- BEN_ROWS (filled in by run_sessions.py after the runs)"
        path.write_text(sql.replace(marker, "\n".join(lines) + "\n" + marker), encoding="utf-8")


def run(only: list) -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    tid = therapist_id()
    for session in only or m["run_order"]:
        db_path = RAW / f"{session}_db.json"
        if db_path.exists():
            print(f"{session}: already run, skipped")
            continue
        if (RAW / f"{session}.txt").exists():
            raise SystemExit(f"{session}: raw/{session}.txt exists but {db_path.name} does not. The session was "
                             "interrupted and may have saved rows. Check the database before re-running it.")
        unloaded = unload_all_models()
        logs_before, events_before = ids("conversation_logs"), ids("safety_events")
        t0 = time.perf_counter()
        result = subprocess.run(
            [str(PYTHON), __file__, "one", session],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", cwd=PROJECT,
            env=dict(os.environ, PYTHONIOENCODING="utf-8", THERAPIST_ID=tid, CLIENT_NAME=m["client_b"]),
            timeout=1800)
        (RAW / f"{session}.txt").write_text(f"[Parent] {unloaded}\n{result.stdout}", encoding="utf-8")
        logs = new_rows("conversation_logs", "id, therapist_id, client_name, timestamp, user_text, assistant_text",
                        logs_before)
        events = new_rows("safety_events", "id, therapist_id, client_name, rule_id, child_text", events_before)
        db_path.write_text(json.dumps({"conversation_logs": logs, "safety_events": events},
                                      indent=2, ensure_ascii=False), encoding="utf-8")
        add_to_cleanup(session, logs, events)
        if result.returncode != 0:
            raise SystemExit(f"{session} failed:\n{result.stdout[-3000:]}")
        print(f"{session}: done in {time.perf_counter() - t0:.0f}s, {len(logs)} new log rows, "
              f"{len(events)} new safety events", flush=True)


if __name__ == "__main__":
    if sys.argv[1] == "one":
        session_process(sys.argv[2])
    elif sys.argv[1] == "run":
        run(sys.argv[2:])
