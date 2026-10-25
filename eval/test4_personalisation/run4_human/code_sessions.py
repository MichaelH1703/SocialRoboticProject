"""Code the 50 blind transcripts (S41-S90), one at a time.

    python code_sessions.py          next uncoded transcript, until all are done (q to stop)
    python code_sessions.py S45      redo one transcript

Each transcript shows its lesson focus and profile style checklist, then asks:
    Q1  Did Reachy steer towards the lesson focus? (y/n)
    Q2  Did Reachy's replies follow the profile's style instructions? (y/n)
    an optional note
Answers are saved to blind_session_coding.tsv after every transcript, so you
can stop and carry on later. Nothing here shows a session's condition.
"""

import csv
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "blind_session_coding.tsv"
COLUMNS = ["label", "followed_lesson_focus", "followed_profile_instructions", "note"]
LABELS = [f"S{i}" for i in range(41, 91)]


def load() -> dict:
    if not OUT.exists():
        return {}
    with OUT.open(encoding="utf-8", newline="") as f:
        return {r["label"]: r for r in csv.DictReader(f, delimiter="\t") if r["followed_lesson_focus"]}


def save(done: dict) -> None:
    with OUT.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, COLUMNS, delimiter="\t")
        writer.writeheader()
        for label in LABELS:
            writer.writerow(done.get(label, {"label": label}))


def yes_no(question: str) -> str:
    while True:
        answer = input(f"{question} (y/n, q to stop): ").strip().lower()
        if answer == "q":
            raise SystemExit("Stopped. Run again to carry on.")
        if answer in ("y", "n"):
            return answer.upper()


def code(label: str, done: dict) -> None:
    os.system("cls" if os.name == "nt" else "clear")
    print((HERE / "blind_sessions" / f"{label}.txt").read_text(encoding="utf-8"))
    print(f"--- {label}: {len(done)} of {len(LABELS)} coded ---")
    q1 = yes_no("Q1. Did Reachy steer towards the lesson focus?")
    q2 = yes_no("Q2. Did Reachy's replies follow the profile's style instructions?")
    note = input("Note (optional, Enter to skip): ").strip().replace("\t", " ")
    done[label] = {"label": label, "followed_lesson_focus": q1, "followed_profile_instructions": q2, "note": note}
    save(done)


def main() -> None:
    done = load()
    if sys.argv[1:]:
        code(sys.argv[1].upper(), done)
        return
    for label in LABELS:
        if label not in done:
            code(label, done)
    print(f"All {len(LABELS)} transcripts coded. Saved to {OUT.name}.")


if __name__ == "__main__":
    main()
