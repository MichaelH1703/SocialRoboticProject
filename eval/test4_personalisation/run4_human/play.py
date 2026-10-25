"""Test 4, run 4: you type April's replies, blind to the condition (H11-H50).

    python play.py setup    once: makes the hidden schedule (_unblinding/schedule.json)
    python play.py          plays the next unplayed session
    python play.py dryrun   a fake session (and a fake abandoned attempt) in _dryrun/

40 sessions: 20 "with" (5 each with April contexts v1-v4, versions.json) and
20 "without" (the blank April), in blocks of 4 (2 with + 2 without) shuffled
with seed 9. "I don't know" reminders: turns 6-10, each 4 times per condition.

The session itself is run 3's, unchanged: run3_human/play.py's session_process()
and card(), pointed at this run's schedule and folders. You see only Reachy's
spoken lines; everything else (and the condition) goes to the hidden raw log.

Before every session: April's database rows must match the snapshot taken
before the first session, and reachy_text_chat.py / reachy_safety.py must be
unchanged, or nothing runs. Ollama models are unloaded; the session process
warms Reachy's model up. An abandoned session (Ctrl+C) is replayed under the
same ID and condition, and recorded in attempts.tsv and guesses.tsv.
"""

import csv
import hashlib
import importlib.util
import json
import os
import random
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
# run3_human/play.py by its path: this file has the same name.
_spec = importlib.util.spec_from_file_location("run3_play", HERE.parent / "run3_human" / "play.py")
run3 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(run3)
from run_pairs import db_snapshot, unload_all_models  # noqa: E402  (run3 put run2/ on sys.path)

PROJECT, PYTHON = run3.PROJECT, run3.PYTHON
ROWS = HERE / "setup_rows.json"
SEED = 9
FIRST = 11
VERSIONS = ["v1", "v2", "v3", "v4"]
PER_VERSION = 5
WATCHED_CODE = ["reachy_text_chat.py", "reachy_safety.py"]
DRY_LINES = ["Yeah. Went bowling.", "Mia. And Ella and stuff.", "/prompt", "Happy.", "Got two strikes.",
             "Pizza.", "I don't know.", "Cake. Candles.", "Bye.", "No.", "/end"]


def paths(base: Path) -> dict:
    return {"base": base, "unblind": base / "_unblinding", "raw": base / "_unblinding" / "raw",
            "schedule": base / "_unblinding" / "schedule.json", "guesses": base / "guesses.tsv",
            "attempts": base / "attempts.tsv", "isolation": base / "isolation_log.txt",
            "before": base / "snapshot_before.json", "code": base / "code_hashes.json",
            "check": base / "isolation_check.txt"}


def therapists() -> dict:
    rows = json.loads(ROWS.read_text(encoding="utf-8"))
    return {"W-v1": rows["v1_id"], "W-v2": rows["v2_id"], "W-v3": rows["v3_id"], "W-v4": rows["v4_id"],
            "B": rows["blank_id"]}


def make_schedule() -> list:
    rng = random.Random(SEED)
    # Blocks of 4 (2 with + 2 without), each shuffled, so conditions are spread evenly.
    conditions = []
    for _ in range(10):
        block = ["W", "W", "B", "B"]
        rng.shuffle(block)
        conditions += block
    versions = [v for v in VERSIONS for _ in range(PER_VERSION)]
    rng.shuffle(versions)
    # Turns 6-10, each 4 times per condition, shuffled.
    turns = {c: [t for t in range(6, 11) for _ in range(4)] for c in "WB"}
    for c in "WB":
        rng.shuffle(turns[c])
    schedule = []
    for i, c in enumerate(conditions, start=FIRST):
        schedule.append({"label": f"H{i}", "condition": f"W-{versions.pop()}" if c == "W" else "B",
                         "idk_turn": turns[c].pop()})
    return schedule


def setup() -> None:
    p = paths(HERE)
    if p["schedule"].exists():
        raise SystemExit("The schedule already exists; not overwriting it.")
    p["unblind"].mkdir(parents=True, exist_ok=True)
    p["schedule"].write_text(json.dumps({"seed": SEED, "made": time.strftime("%Y-%m-%d %H:%M"),
                                         "sessions": make_schedule()}, indent=2), encoding="utf-8")
    print("Hidden schedule made for 40 sessions (H11-H50). Do not open _unblinding/.")


def code_hashes() -> dict:
    return {f: hashlib.md5((PROJECT / f).read_bytes()).hexdigest() for f in WATCHED_CODE}


def session_process(label: str, base: str) -> None:
    """Run 3's session, pointed at this run's schedule, folders and therapists."""
    p = paths(Path(base))
    run3.SCHEDULE, run3.RAW, run3.THERAPIST = p["schedule"], p["raw"], therapists()
    run3.session_process(label)


def record(path: Path, header: list, row: list) -> None:
    new_file = not path.exists()
    with path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        if new_file:
            writer.writerow(header)
        writer.writerow(row)


def play(base: Path = HERE, script: list = None) -> None:
    """One session. script (dry run only) replaces your typing, Enter and guess."""
    p = paths(base)
    if not p["schedule"].exists():
        raise SystemExit("Run 'python play.py setup' first.")
    schedule = json.loads(p["schedule"].read_text(encoding="utf-8"))["sessions"]
    todo = [s["label"] for s in schedule if not (p["raw"] / f"{s['label']}.txt").exists()]
    if not todo:
        raise SystemExit("All sessions are played.")
    label = todo[0]
    p["raw"].mkdir(parents=True, exist_ok=True)
    print(f"Session {label} ({len(schedule) - len(todo) + 1} of {len(schedule)}). Checking the setup...")

    # Same database and code as before the first session, or nothing runs.
    if not p["before"].exists():
        p["before"].write_text(json.dumps(db_snapshot(), indent=2), encoding="utf-8")
        p["code"].write_text(json.dumps(code_hashes(), indent=2), encoding="utf-8")
    if db_snapshot() != json.loads(p["before"].read_text(encoding="utf-8")):
        raise SystemExit("April's database rows have changed since the first session. Not running.")
    if code_hashes() != json.loads(p["code"].read_text(encoding="utf-8")):
        raise SystemExit("reachy_text_chat.py or reachy_safety.py has changed since the first session. Not running.")
    print("Database and code unchanged.")
    unloaded = unload_all_models()
    print(run3.card())
    if script is None:
        input("Press Enter to start.")

    started = time.strftime("%Y-%m-%d %H:%M")
    try:
        code = subprocess.run(
            [str(PYTHON), __file__, "one", label, str(base)], cwd=PROJECT,
            env=dict(os.environ, PYTHONIOENCODING="utf-8"),
            input=None if script is None else "\n".join(script) + "\n",
            text=True if script is not None else None).returncode
    except KeyboardInterrupt:  # Ctrl+C reaches both processes; run() has already stopped the session
        code = 1
    raw = p["raw"] / f"{label}.txt"
    if code != 0:
        aborted = p["raw"] / f"{label}.aborted-{time.strftime('%Y%m%d-%H%M%S')}.txt"
        if raw.exists():
            raw.rename(aborted)
        record(p["attempts"], ["label", "started", "outcome"], [label, started, "abandoned"])
        raise SystemExit(f"\n{label} abandoned; it will be offered again next time (same ID and condition).")
    record(p["attempts"], ["label", "started", "outcome"], [label, started, "played"])

    print(f"\n{label} saved.")
    if script is None:
        guess = run3.ask("Your guess for this session (with / without / unsure): ", ("with", "without", "unsure"))
        confidence = run3.ask("How sure, 1 (guessing) to 5 (certain): ", tuple("12345"))
    else:
        guess, confidence = "unsure", "1"
    abandoned = len(list(p["raw"].glob(f"{label}.aborted-*.txt")))
    record(p["guesses"], ["label", "guess", "confidence", "played", "abandoned_attempts"],
           [label, guess, confidence, time.strftime("%Y-%m-%d %H:%M"), abandoned])

    isolation = re.search(r"\[Isolation\] (.*)", raw.read_text(encoding="utf-8"))
    with p["isolation"].open("a", encoding="utf-8") as f:
        f.write(f"{label}: {unloaded} before starting\n    {isolation.group(1) if isolation else 'NO ISOLATION LINE'}\n")
    if len(todo) == 1:
        before, after = json.loads(p["before"].read_text(encoding="utf-8")), db_snapshot()
        lines = [f"Isolation check, run 4, finished {time.strftime('%Y-%m-%d %H:%M')}", "",
                 p["isolation"].read_text(encoding="utf-8").rstrip(), "",
                 "April's database rows (all tables the robot reads or writes, every therapist's April):"]
        lines += [f"  {t}: before {before[t]} | after {after[t]}" for t in before]
        lines += ["", f"Unchanged by the run: {before == after}"]
        p["check"].write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"All sessions played. Database unchanged by the run: {before == after}")
    else:
        print(f"{len(todo) - 1} left. Run 'python play.py' again when ready.")


def dryrun() -> None:
    """A fake 1-session schedule in _dryrun/: one abandoned attempt, then a full scripted session."""
    base = HERE / "_dryrun"
    p = paths(base)
    if p["schedule"].exists():
        raise SystemExit("_dryrun/ already exists; delete it to run the dry run again.")
    p["unblind"].mkdir(parents=True, exist_ok=True)
    p["schedule"].write_text(json.dumps({"seed": "dry run", "sessions": [
        {"label": "D01", "condition": "W-v2", "idk_turn": 6}]}, indent=2), encoding="utf-8")
    try:
        play(base, DRY_LINES[:3])  # stdin runs out after 3 lines: abandoned
    except SystemExit as e:
        print(e)
    play(base, DRY_LINES)


if __name__ == "__main__":
    if sys.argv[1:] == ["setup"]:
        setup()
    elif sys.argv[1:] == ["dryrun"]:
        dryrun()
    elif sys.argv[1:2] == ["one"]:
        session_process(sys.argv[2], sys.argv[3])
    else:
        play()
