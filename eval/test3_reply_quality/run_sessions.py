"""Run Test 3: April with her context, three events, each run twice.

    python run_sessions.py run    the 6 sessions in materials.json's order

Five events, each run twice; the two runs of a story are five sessions apart.

Isolation: before every session the parent unloads every model from Ollama
and waits until none is loaded, then the session runs in a brand-new process
with empty histories, which it logs. April's database rows are snapshotted
before and after the whole run (isolation_check.txt) to show the runs wrote
nothing that a later session could read.

Same method as Test 4's run_sim_sessions.py (which is left untouched so Test 4
stays reproducible): each session runs in a fresh process that imports
reachy_text_chat.py unchanged, with saving off, and a simulated April
(../simulated_child.py) answers what Reachy actually asked from the story's
fact sheet. Child turns: a fixed opening that picks the story's event, 11
generated answers including one forced "I don't know" in answer to a
question, then "Bye." and "No.". Raw output goes to raw/<session>.txt.
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

m = json.loads((HERE / "materials.json").read_text(encoding="utf-8"))
THERAPIST_ID = json.loads((HERE / m["setup_rows_from"]).read_text(encoding="utf-8"))["with_therapist_id"]

# Things only in April's profile, note or plan. April must never say them, or
# Reachy repeating them would look like it came from the profile.
OUTSIDE_FACT_SHEET = re.compile(
    r"\b(horses?|pony|ponies|pepper|stables?|meadowbank|riding|theo|brother|art|drawing|dogs?)\b", re.I)
SAYS_IDK = re.compile(r"\b(?:i )?(?:don'?t|do not) know\b|\bdunno\b", re.I)
FEELINGS = re.compile(
    r"\b(annoyed|angry|mad|cross|sad|upset|scared|afraid|worried|anxious|embarrassed|excited|proud|"
    r"bored|tired|lonely|jealous|confused|frustrated|shy|surprised|bad|happy|nervous|relieved|cold)\b", re.I)


def story_prompt(story: dict) -> str:
    if "system_prompt_from" in story:
        source = json.loads((HERE / story["system_prompt_from"]).read_text(encoding="utf-8"))
        return source["child"]["system_prompt"]
    return story["system_prompt"]


def session_process(session: str, seed: int) -> None:
    """One session, in this process. Output is the session's raw log."""
    story = m["stories"][session.split("-")[0]]
    os.environ["THERAPIST_ID"] = THERAPIST_ID
    os.environ["CLIENT_NAME"] = m["client_name"]
    os.chdir(PROJECT)
    sys.path[:0] = [str(PROJECT), str(PROJECT / "eval")]
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    import reachy_safety
    import reachy_text_chat as rtc
    from simulated_child import SimulatedChild

    rtc.SAVE_TO_SUPABASE = False
    c = m["child"]
    print(f"[Child sim] session {session} ({story['event_title']}), {c['model']}, "
          f"temperature {c['temperature']}, seed {seed}")

    def reject(line: str):
        if not line:
            return "empty"
        if len(line.split()) > c["max_words"]:
            return "too long"
        if "?" in line:
            return "asks a question"
        if SAYS_IDK.search(line):
            return "says I don't know"
        if rtc.is_goodbye(line):
            return "reads as a goodbye"
        rule = reachy_safety.classify(line)
        if rule is not None:
            return f"sets off safety rule {rule.id}"
        if OUTSIDE_FACT_SHEET.search(line):
            return "mentions something outside the fact sheet"
        for feeling in FEELINGS.findall(line):
            if feeling.lower() not in story["allowed_feelings"]:
                return f"a feeling not on the fact sheet ({feeling})"
        return None

    def take_turn(line: str) -> str:
        print(f"You: {line}", flush=True)
        before = len(rtc.chat_history)
        chat.handle(line)
        return " ".join(e["text"] for e in rtc.chat_history[before:] if e["role"] == "assistant")

    def asks_open_question(text: str) -> bool:
        return "?" in text and bool(re.search(r"\b(how|why|what)\b", text, re.I)) \
            and not re.search(r"\bor\b", text, re.I)

    # Isolation evidence: a new process, nothing in Reachy's histories, and no
    # model loaded in Ollama (the parent unloaded them all before starting us).
    print(f"[Isolation] new process pid {os.getpid()}; Reachy chat history {len(rtc.chat_history)} items, "
          f"conversation log {len(rtc.conversation_log)} rows; models loaded in Ollama: {loaded_models() or 'none'}")
    rtc.warm_up_model()

    context = rtc.build_context_from_supabase(rtc.THERAPIST_ID, rtc.CLIENT_NAME)
    chat = rtc.TextSession(context)
    chat.update_instructions()
    chat.greet()

    child = SimulatedChild(story_prompt(story), c["model"], seed, c["temperature"], c["fallback_line"])
    heard = next(e["text"] for e in reversed(rtc.chat_history) if e["role"] == "assistant")
    child.hear(heard)

    idk_used = False
    for turn in range(1, c["content_turns"] + 1):
        if turn == 1:
            line = story["opening_line"]
            child.say(line)
        # Only ever in answer to a question; the last content turn is the
        # backstop that guarantees exactly one.
        elif not idk_used and ((turn >= c["idk_earliest_turn"] and asks_open_question(heard))
                               or (turn >= c["idk_latest_turn"] and "?" in heard)
                               or turn == c["content_turns"]):
            line = c["idk_line"]
            child.say(line)
            idk_used = True
        else:
            line, notes = child.respond(turn, reject)
            for note in notes:
                print(f"[Child sim] {note}")
        heard = take_turn(line)
        child.hear(heard)
        if chat.ended:
            print("[Child sim] Session ended before the planned goodbye.")
            return

    for line in c["ending_lines"]:
        child.say(line)
        child.hear(take_turn(line))
        if chat.ended:
            return
    print("[Child sim] Session did not end after the planned goodbye.")


OLLAMA = "http://localhost:11434"


def loaded_models() -> list:
    with urllib.request.urlopen(f"{OLLAMA}/api/ps", timeout=10) as resp:
        return [model["name"] for model in json.load(resp).get("models", [])]


def unload_all_models() -> str:
    """Unload every model from Ollama, so no session can share cached state with another."""
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


def db_snapshot() -> dict:
    """April's rows in every table the robot reads or writes. Must be unchanged by the run."""
    def psql(sql: str) -> str:
        return subprocess.run(
            ["docker", "exec", "-i", "supabase_db_ReachyVoiceCode", "psql", "-U", "postgres", "-d", "postgres", "-At"],
            input=sql.encode("utf-8"), capture_output=True, check=True).stdout.decode("utf-8").strip()
    tables = ["conversation_logs", "session_notes", "client_profiles", "daily_recap_sessions",
              "recount_event_prompts", "client_progress", "client_curriculum", "safety_events"]
    snapshot = {}
    for table in tables:
        if psql(f"SELECT to_regclass('public.{table}') IS NOT NULL;") != "t":
            snapshot[table] = "table not present"
            continue
        snapshot[table] = psql(
            f"SELECT count(*) || ' rows, md5 ' || coalesce(md5(string_agg(t::text, '|' ORDER BY t::text)), '-') "
            f"FROM {table} t WHERE client_name = 'April';")
    return snapshot


def run() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    log = [f"Isolation check, {time.strftime('%Y-%m-%d %H:%M')}", ""]
    before = db_snapshot()
    for session in m["run_order"]:
        path = RAW / f"{session}.txt"
        if path.exists():
            print(f"{session}: already run, skipped")
            continue
        log.append(f"{session}: {unload_all_models()} before starting")
        t0 = time.perf_counter()
        result = subprocess.run(
            [str(PYTHON), __file__, "one", session, str(m["seeds"][session])],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8",
            cwd=PROJECT, env=dict(os.environ, PYTHONIOENCODING="utf-8"), timeout=1800,
        )
        path.write_text(result.stdout, encoding="utf-8")
        if result.returncode != 0:
            raise SystemExit(f"{session} failed:\n{result.stdout[-3000:]}")
        isolation = re.search(r"\[Isolation\] (.*)", result.stdout)
        log.append(f"    {isolation.group(1) if isolation else 'NO ISOLATION LINE'}")
        print(f"{session}: done in {time.perf_counter() - t0:.0f}s", flush=True)

    after = db_snapshot()
    log += ["", "April's database rows (all tables the robot reads or writes):"]
    log += [f"  {table}: before {before[table]} | after {after[table]}" for table in before]
    log += ["", f"Unchanged by the run: {before == after}"]
    (HERE / "isolation_check.txt").write_text("\n".join(log) + "\n", encoding="utf-8")
    print("\n".join(log))


if __name__ == "__main__":
    if sys.argv[1] == "one":
        session_process(sys.argv[2], int(sys.argv[3]))
    elif sys.argv[1] == "run":
        run()
