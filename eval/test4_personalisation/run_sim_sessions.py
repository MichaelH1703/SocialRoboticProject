"""Run Test 4 with a simulated April (../simulated_child.py) instead of a fixed script.

    python run_sim_sessions.py check   compare the two conditions' system prompts
    python run_sim_sessions.py pilot   one session per condition, into pilot/
    python run_sim_sessions.py run     the 10 sessions in materials.json's order

Each session runs in a fresh process, which imports reachy_text_chat.py
unchanged, sets THERAPIST_ID / CLIENT_NAME for its condition, turns saving off,
and drives TextSession turn by turn. April hears exactly what the child would
hear: Reachy's greeting, scripted lines and model replies, never the dropped
[Not spoken] replies. W and B sessions with the same number share a seed, so
April answers identically whenever Reachy says the same thing.

Child turns: a fixed opening (so the same event is picked in every session),
then generated answers, with one forced "I don't know": at the first open
question from turn 6, else the first question of any kind from turn 10, else
the last content turn. Then "Bye." and "No.".
"""

import difflib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent.parent
PYTHON = PROJECT / "venv" / "Scripts" / "python.exe"

m = json.loads((HERE / "materials.json").read_text(encoding="utf-8"))
rows = json.loads((HERE / "setup_rows.json").read_text(encoding="utf-8"))
THERAPIST = {"W": rows["with_therapist_id"], "B": rows["blank_therapist_id"]}

# Things only in April's profile, note or plan. April must never say them, or
# Reachy repeating them would look like personalisation.
OUTSIDE_FACT_SHEET = re.compile(
    r"\b(horses?|pony|ponies|pepper|stables?|meadowbank|riding|theo|brother|art|drawing|dogs?)\b", re.I)
SAYS_IDK = re.compile(r"\b(?:i )?(?:don'?t|do not) know\b|\bdunno\b", re.I)
# Feelings April did not have today. The fact sheet allows only those in
# materials.json's allowed_feelings; the pilot showed her inventing others.
OTHER_FEELINGS = re.compile(
    r"\b(annoyed|angry|mad|cross|sad|upset|scared|afraid|worried|anxious|embarrassed|excited|proud|"
    r"bored|tired|lonely|jealous|confused|frustrated|shy|surprised|bad)\b", re.I)


def session_process(session: str, condition: str, seed: int) -> None:
    """One session, in this process. Output is the session's raw log."""
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
    print(f"[Child sim] session {session}, {c['model']}, temperature {c['temperature']}, seed {seed}")

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
        feeling = OTHER_FEELINGS.search(line)
        if feeling and feeling.group(1).lower() not in c["allowed_feelings"]:
            return f"a feeling not on the fact sheet ({feeling.group(1)})"
        return None

    def take_turn(line: str) -> str:
        print(f"You: {line}", flush=True)
        before = len(rtc.chat_history)
        chat.handle(line)
        return " ".join(e["text"] for e in rtc.chat_history[before:] if e["role"] == "assistant")

    def asks_open_question(text: str) -> bool:
        return "?" in text and bool(re.search(r"\b(how|why|what)\b", text, re.I)) \
            and not re.search(r"\bor\b", text, re.I)

    context = rtc.build_context_from_supabase(rtc.THERAPIST_ID, rtc.CLIENT_NAME)
    chat = rtc.TextSession(context)
    chat.update_instructions()
    chat.greet()

    child = SimulatedChild(c["system_prompt"], c["model"], seed, c["temperature"], c["fallback_line"])
    heard = next(e["text"] for e in reversed(rtc.chat_history) if e["role"] == "assistant")
    child.hear(heard)

    idk_used = False
    for turn in range(1, c["content_turns"] + 1):
        if turn == 1:
            line = c["opening_line"]
            child.say(line)
        # Only ever in answer to a question, so it never comes out of nowhere.
        # The last content turn is the backstop that guarantees exactly one.
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


def run_session(session: str, seed: int, out: Path) -> None:
    result = subprocess.run(
        [str(PYTHON), __file__, "one", session, session[0], str(seed)],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8",
        cwd=PROJECT, env=dict(os.environ, PYTHONIOENCODING="utf-8"), timeout=1800,
    )
    out.write_text(result.stdout, encoding="utf-8")
    if result.returncode != 0:
        raise SystemExit(f"{session} failed:\n{result.stdout[-3000:]}")


def run_all(sessions: list, raw_dir: Path) -> None:
    raw_dir.mkdir(parents=True, exist_ok=True)
    for session, seed in sessions:
        path = raw_dir / f"{session}.txt"
        if path.exists():
            print(f"{session}: already run, skipped")
            continue
        t0 = time.perf_counter()
        run_session(session, seed, path)
        print(f"{session}: done in {time.perf_counter() - t0:.0f}s", flush=True)


def system_prompt(condition: str) -> str:
    env = dict(os.environ, THERAPIST_ID=THERAPIST[condition], CLIENT_NAME=m["client_name"],
               PYTHONIOENCODING="utf-8")
    out = subprocess.run(
        [str(PYTHON), "reachy_text_chat.py", "--no-save"], input="/prompt\n/quit\n",
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8",
        cwd=PROJECT, env=env, timeout=600,
    ).stdout
    return out.split("You: ")[1]


def check() -> None:
    with_prompt, blank_prompt = system_prompt("W"), system_prompt("B")
    (HERE / "_unblinding" / "prompt_with.txt").write_text(with_prompt, encoding="utf-8")
    (HERE / "_unblinding" / "prompt_without.txt").write_text(blank_prompt, encoding="utf-8")
    diff = difflib.unified_diff(with_prompt.splitlines(), blank_prompt.splitlines(),
                                "with context", "without context", lineterm="", n=1)
    print("\n".join(diff))


if __name__ == "__main__":
    command = sys.argv[1]
    if command == "one":
        session_process(sys.argv[2], sys.argv[3], int(sys.argv[4]))
    elif command == "check":
        check()
    elif command == "pilot":
        run_all([("W0", 100), ("B0", 100)], HERE / "pilot" / "raw")
    elif command == "run":
        run_all([(s, int(s[1:])) for s in m["run_order"]], HERE / "_unblinding" / "raw")
