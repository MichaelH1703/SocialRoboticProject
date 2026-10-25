"""Test 4, run 3: you type April's replies, blind to the condition.

    python play.py setup   once: makes the hidden schedule (_unblinding/schedule.json)
    python play.py         plays the next unplayed session (H01-H10: 5 with, 5 without)

Same robot code and prompts as runs 1 and 2 (reachy_text_chat.py unchanged,
saving off). The condition only changes which therapist's April is loaded
(../setup_rows.json); play.py takes it from the hidden schedule and never shows
it. You see only what April would hear: Reachy's spoken lines. Everything else
(state, question cuts, safety replacements, [Not spoken] replies, the condition)
goes to the hidden raw log, _unblinding/raw/Hnn.txt, in the same format as runs
1 and 2. Slash commands are off, so the prompt cannot be shown.

Isolation as in run 2: both prompts are checked against run 1's before every
session, every Ollama model is unloaded, each session runs in a fresh process
that warms Reachy's model up first, and April's database rows are snapshotted
before the first session and after the last.

After each session you guess the condition (guesses.tsv), to measure how blind
you stayed.
"""

import csv
import json
import os
import random
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent), str(HERE.parent / "run2")]
import run_sim_sessions as base  # noqa: E402
from run_pairs import db_snapshot, loaded_models, unload_all_models  # noqa: E402

PROJECT, PYTHON, m, THERAPIST = base.PROJECT, base.PYTHON, base.m, base.THERAPIST
UNBLIND = HERE / "_unblinding"
RAW = UNBLIND / "raw"
SCHEDULE = UNBLIND / "schedule.json"
GUESSES = HERE / "guesses.tsv"
SESSIONS_PER_CONDITION = 5
SCHEDULE_SEED = 7
WRAP_UP_TURN = 13  # runs 1 and 2: 12 content turns, then "Bye." and "No."


def card() -> str:
    """What the player needs: April's day (from the simulated child's fact sheet) and how she talks."""
    facts = re.search(r"Never add anything else, and never contradict them:\n(.*?)\n\n",
                      m["child"]["system_prompt"], re.S).group(1)
    return f"""
You are April (14, Autism), telling Reachy about today.

What happened today:
{facts}

Try to (as the simulated April did in runs 1 and 2):
- Start with "Yeah. Went bowling." so Reachy picks this event.
- Answer only what Reachy asks, in 1 to 5 words, never more than 10. Leave out
  small words; sometimes say "thing" or "stuff". Never ask Reachy a question.
- Feelings today: happy, and a bit nervous. "Good" or "fun" are fine too.
- "Why" questions are hard: give a short or vague answer. If Reachy offers two
  choices, pick one. If Reachy only comments, say "Yeah." or "Mm."
- Anything not on the list: "Can't remember." or "Not really."
- Say "I don't know." only on the turn you are told to.
- After about 12 answers, say "Bye.", then "No." to Reachy's last question.

You won't be told whether Reachy has April's notes.
/end stops a session early (it still counts); Ctrl+C abandons it (replayed next time).
"""


def setup() -> None:
    if SCHEDULE.exists():
        raise SystemExit("The schedule already exists; not overwriting it.")
    rng = random.Random(SCHEDULE_SEED)
    conditions = ["W"] * SESSIONS_PER_CONDITION + ["B"] * SESSIONS_PER_CONDITION
    rng.shuffle(conditions)
    # Turns 6-10 once per condition, so the turn says nothing about the condition.
    turns = {c: rng.sample(range(6, 11), SESSIONS_PER_CONDITION) for c in "WB"}
    schedule = [{"label": f"H{i:02d}", "condition": c, "idk_turn": turns[c].pop()}
                for i, c in enumerate(conditions, start=1)]
    UNBLIND.mkdir(parents=True, exist_ok=True)
    SCHEDULE.write_text(json.dumps({"seed": SCHEDULE_SEED, "made": time.strftime("%Y-%m-%d %H:%M"),
                                    "sessions": schedule}, indent=2), encoding="utf-8")
    print(f"Hidden schedule made for {len(schedule)} sessions. Do not open _unblinding/.")


def session_process(label: str) -> None:
    """One session, in this process. The player sees Reachy's spoken lines; the log gets everything."""
    entry = next(s for s in json.loads(SCHEDULE.read_text(encoding="utf-8"))["sessions"] if s["label"] == label)
    console = sys.__stdout__
    console.reconfigure(encoding="utf-8", errors="replace")
    log = (RAW / f"{label}.txt").open("w", encoding="utf-8")
    sys.stdout = sys.stderr = log

    def show(text: str) -> None:
        console.write(text + "\n")
        console.flush()

    os.environ["THERAPIST_ID"] = THERAPIST[entry["condition"]]
    os.environ["CLIENT_NAME"] = m["client_name"]
    os.chdir(PROJECT)
    sys.path[:0] = [str(PROJECT)]
    import reachy_text_chat as rtc

    rtc.SAVE_TO_SUPABASE = False
    print(f"[Human] session {label}, condition {entry['condition']}, \"I don't know\" at turn {entry['idk_turn']}")
    print(f"[Isolation] new process pid {os.getpid()}; Reachy chat history {len(rtc.chat_history)} items, "
          f"conversation log {len(rtc.conversation_log)} rows; models loaded in Ollama: {loaded_models() or 'none'}")
    show("Loading Reachy...")
    rtc.warm_up_model()

    context = rtc.build_context_from_supabase(rtc.THERAPIST_ID, rtc.CLIENT_NAME)
    chat = rtc.TextSession(context)
    chat.update_instructions()
    chat.greet()
    show(f"\nReachy: {next(e['text'] for e in reversed(rtc.chat_history) if e['role'] == 'assistant')}\n")

    turn = 0
    while not chat.ended:
        turn += 1
        if turn == entry["idk_turn"]:
            show('(This turn, answer "I don\'t know.")')
        elif turn == WRAP_UP_TURN:
            show('(Time to finish: say "Bye.", then "No.")')
        console.write(f"[{turn}] You: ")
        console.flush()
        line = sys.stdin.readline()
        if not line:
            raise KeyboardInterrupt
        line = line.strip()
        if line == "/end":
            print("[Human] Ended by the player before Reachy's goodbye.")
            show("(Session ended.)")
            break
        if not line or line.startswith("/"):
            if line:
                show("(Commands are off in blind mode. /end stops the session.)")
            turn -= 1
            continue
        print(f"You: {line}", flush=True)
        before = len(rtc.chat_history)
        chat.handle(line)
        heard = " ".join(e["text"] for e in rtc.chat_history[before:] if e["role"] == "assistant")
        show(f"\nReachy: {heard}\n")
    print("[Human] Session over.")
    log.flush()


def ask(question: str, answers: tuple) -> str:
    while True:
        reply = input(question).strip().lower()
        if reply in answers:
            return reply


def play() -> None:
    if not SCHEDULE.exists():
        raise SystemExit("Run 'python play.py setup' first.")
    schedule = json.loads(SCHEDULE.read_text(encoding="utf-8"))["sessions"]
    todo = [s["label"] for s in schedule if not (RAW / f"{s['label']}.txt").exists()]
    if not todo:
        raise SystemExit("All sessions are played.")
    label = todo[0]
    RAW.mkdir(parents=True, exist_ok=True)
    print(f"Session {label} ({len(schedule) - len(todo) + 1} of {len(schedule)}). Checking the prompts...")
    same = all(base.system_prompt(c) == (HERE.parent / "_unblinding" / f"prompt_{n}.txt").read_text(
        encoding="utf-8") for c, n in (("W", "with"), ("B", "without")))
    if not same:
        raise SystemExit("The prompts no longer match run 1's (has the database changed?). Not running.")
    print("Prompts match run 1.")
    before_path = HERE / "snapshot_before.json"
    if not before_path.exists():
        before_path.write_text(json.dumps(db_snapshot(), indent=2), encoding="utf-8")
    unloaded = unload_all_models()
    print(card())
    input("Press Enter to start.")

    try:
        code = subprocess.run([str(PYTHON), __file__, "one", label], cwd=PROJECT,
                              env=dict(os.environ, PYTHONIOENCODING="utf-8")).returncode
    except KeyboardInterrupt:  # Ctrl+C reaches both processes; run() has already stopped the session
        code = 1
    raw = RAW / f"{label}.txt"
    if code != 0:
        aborted = RAW / f"{label}.aborted-{time.strftime('%Y%m%d-%H%M%S')}.txt"
        raw.rename(aborted)
        raise SystemExit(f"\n{label} abandoned; it will be offered again next time.")

    print(f"\n{label} saved.")
    guess = ask("Your guess for this session (with / without / unsure): ", ("with", "without", "unsure"))
    confidence = ask("How sure, 1 (guessing) to 5 (certain): ", tuple("12345"))
    new_file = not GUESSES.exists()
    with GUESSES.open("a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        if new_file:
            writer.writerow(["label", "guess", "confidence", "played"])
        writer.writerow([label, guess, confidence, time.strftime("%Y-%m-%d %H:%M")])

    isolation = re.search(r"\[Isolation\] (.*)", raw.read_text(encoding="utf-8"))
    with (HERE / "isolation_log.txt").open("a", encoding="utf-8") as f:
        f.write(f"{label}: {unloaded} before starting\n    {isolation.group(1) if isolation else 'NO ISOLATION LINE'}\n")
    if len(todo) == 1:
        before, after = json.loads(before_path.read_text(encoding="utf-8")), db_snapshot()
        lines = [f"Isolation check, run 3, finished {time.strftime('%Y-%m-%d %H:%M')}", "",
                 (HERE / "isolation_log.txt").read_text(encoding="utf-8").rstrip(), "",
                 "April's database rows (all tables the robot reads or writes):"]
        lines += [f"  {t}: before {before[t]} | after {after[t]}" for t in before]
        lines += ["", f"Unchanged by the run: {before == after}"]
        (HERE / "isolation_check.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"All sessions played. Database unchanged by the run: {before == after}")
    else:
        print(f"{len(todo) - 1} left. Run 'python play.py' again when ready.")


if __name__ == "__main__":
    if sys.argv[1:] == ["setup"]:
        setup()
    elif sys.argv[1:2] == ["one"]:
        session_process(sys.argv[2])
    else:
        play()
