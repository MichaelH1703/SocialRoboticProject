"""Test 4, run 2: ten more pairs, W6-W15 and B6-B15.

    python run_pairs.py check   both system prompts, compared with run 1's saved ones
    python run_pairs.py run     the 20 sessions in settings.json's order (resumes)

Same method as ../run_sim_sessions.py, which is left untouched so run 1 stays
reproducible: a fresh process per session imports reachy_text_chat.py
unchanged, with saving off, and the simulated April (../../simulated_child.py)
answers from the same fact sheet and settings (../materials.json). Changes:

- Each Wn/Bn pair shares the child's seed (n, as in run 1) AND the turn of the
  forced "I don't know" (settings.json), which is given at exactly that turn in
  both sessions. Run 1 picked the turn from Reachy's questions, so it landed at
  turn 6 in most W sessions and turn 10 in most B sessions. Whether Reachy's
  line before it asked a question is logged.
- Before every session the parent unloads every Ollama model and checks none
  is loaded. The session then warms Reachy's model up, as reachy_text_chat.py's
  main does, so the first reply is not slowed by loading.
- April's database rows are snapshotted before and after the whole run
  (isolation_check.txt), and both prompts must match run 1's before any run.
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
sys.path.insert(0, str(HERE.parent))
import run_sim_sessions as base  # noqa: E402

PROJECT, PYTHON, m, THERAPIST = base.PROJECT, base.PYTHON, base.m, base.THERAPIST
settings = json.loads((HERE / "settings.json").read_text(encoding="utf-8"))
UNBLIND = HERE / "_unblinding"
RAW = UNBLIND / "raw"
OLLAMA = "http://localhost:11434"


def loaded_models() -> list:
    with urllib.request.urlopen(f"{OLLAMA}/api/ps", timeout=10) as resp:
        return [model["name"] for model in json.load(resp).get("models", [])]


def session_process(session: str, seed: int, idk_turn: int) -> None:
    """One session, in this process. Output is the session's raw log."""
    condition = session[0]
    os.environ["THERAPIST_ID"] = THERAPIST[condition]
    os.environ["CLIENT_NAME"] = m["client_name"]
    os.chdir(PROJECT)
    sys.path[:0] = [str(PROJECT), str(PROJECT / "eval")]
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    import reachy_safety
    import reachy_text_chat as rtc
    from simulated_child import SimulatedChild

    rtc.SAVE_TO_SUPABASE = False
    c = m["child"]
    print(f"[Child sim] session {session}, {c['model']}, temperature {c['temperature']}, seed {seed}, "
          f"\"I don't know\" at turn {idk_turn}")

    def reject(line: str):
        if not line:
            return "empty"
        if len(line.split()) > c["max_words"]:
            return "too long"
        if "?" in line:
            return "asks a question"
        if base.SAYS_IDK.search(line):
            return "says I don't know"
        if rtc.is_goodbye(line):
            return "reads as a goodbye"
        rule = reachy_safety.classify(line)
        if rule is not None:
            return f"sets off safety rule {rule.id}"
        if base.OUTSIDE_FACT_SHEET.search(line):
            return "mentions something outside the fact sheet"
        feeling = base.OTHER_FEELINGS.search(line)
        if feeling and feeling.group(1).lower() not in c["allowed_feelings"]:
            return f"a feeling not on the fact sheet ({feeling.group(1)})"
        return None

    def take_turn(line: str) -> str:
        print(f"You: {line}", flush=True)
        before = len(rtc.chat_history)
        chat.handle(line)
        return " ".join(e["text"] for e in rtc.chat_history[before:] if e["role"] == "assistant")

    # Isolation evidence: a new process, nothing in Reachy's histories, and no
    # model loaded in Ollama (the parent unloaded them all before starting us).
    print(f"[Isolation] new process pid {os.getpid()}; Reachy chat history {len(rtc.chat_history)} items, "
          f"conversation log {len(rtc.conversation_log)} rows; models loaded in Ollama: {loaded_models() or 'none'}")
    rtc.warm_up_model()

    context = rtc.build_context_from_supabase(rtc.THERAPIST_ID, rtc.CLIENT_NAME)
    chat = rtc.TextSession(context)
    chat.update_instructions()
    chat.greet()

    child = SimulatedChild(c["system_prompt"], c["model"], seed, c["temperature"], c["fallback_line"])
    heard = next(e["text"] for e in reversed(rtc.chat_history) if e["role"] == "assistant")
    child.hear(heard)

    for turn in range(1, c["content_turns"] + 1):
        if turn == 1:
            line = c["opening_line"]
            child.say(line)
        elif turn == idk_turn:
            line = c["idk_line"]
            child.say(line)
            print(f"[Child sim] forced \"I don't know\" at turn {turn}; Reachy's line before it "
                  f"{'asked' if '?' in heard else 'did not ask'} a question")
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


def check() -> bool:
    """Both conditions' prompts, saved, and compared byte for byte with run 1's."""
    UNBLIND.mkdir(parents=True, exist_ok=True)
    same = True
    for condition, name in (("W", "with"), ("B", "without")):
        prompt = base.system_prompt(condition)
        (UNBLIND / f"prompt_{name}.txt").write_text(prompt, encoding="utf-8")
        run1 = (HERE.parent / "_unblinding" / f"prompt_{name}.txt").read_text(encoding="utf-8")
        print(f"{name}: {'identical to run 1' if prompt == run1 else 'DIFFERS from run 1'}")
        same &= prompt == run1
    return same


def run() -> None:
    if not check():
        raise SystemExit("A prompt differs from run 1's; not running.")
    RAW.mkdir(parents=True, exist_ok=True)
    before_path = HERE / "snapshot_before.json"
    if not before_path.exists():
        before_path.write_text(json.dumps(db_snapshot(), indent=2), encoding="utf-8")
    before = json.loads(before_path.read_text(encoding="utf-8"))
    log_path = HERE / "isolation_log.txt"
    for session in settings["run_order"]:
        path = RAW / f"{session}.txt"
        if path.exists():
            print(f"{session}: already run, skipped")
            continue
        pair = session[1:]
        seed, idk_turn = settings["child_seeds"][pair], settings["idk_turns"][pair]
        unloaded = unload_all_models()
        t0 = time.perf_counter()
        result = subprocess.run(
            [str(PYTHON), __file__, "one", session, str(seed), str(idk_turn)],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8",
            cwd=PROJECT, env=dict(os.environ, PYTHONIOENCODING="utf-8"), timeout=1800,
        )
        path.write_text(result.stdout, encoding="utf-8")
        if result.returncode != 0:
            path.rename(path.with_suffix(".failed.txt"))
            raise SystemExit(f"{session} failed:\n{result.stdout[-3000:]}")
        isolation = re.search(r"\[Isolation\] (.*)", result.stdout)
        with log_path.open("a", encoding="utf-8") as log:
            log.write(f"{session}: {unloaded} before starting\n"
                      f"    {isolation.group(1) if isolation else 'NO ISOLATION LINE'}\n")
        print(f"{session}: done in {time.perf_counter() - t0:.0f}s", flush=True)

    after = db_snapshot()
    lines = [f"Isolation check, run 2, finished {time.strftime('%Y-%m-%d %H:%M')}", "",
             log_path.read_text(encoding="utf-8").rstrip(), "",
             "April's database rows (all tables the robot reads or writes):"]
    lines += [f"  {table}: before {before[table]} | after {after[table]}" for table in before]
    lines += ["", f"Unchanged by the run: {before == after}"]
    (HERE / "isolation_check.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    if sys.argv[1] == "one":
        session_process(sys.argv[2], int(sys.argv[3]), int(sys.argv[4]))
    elif sys.argv[1] == "check":
        check()
    elif sys.argv[1] == "run":
        run()
