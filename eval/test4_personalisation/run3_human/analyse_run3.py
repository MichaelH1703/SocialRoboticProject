"""Turn run 3's raw logs into the blind rating materials, as ../analyse.py did for run 1.

For the raters (safe to open before rating):
    blind_replies.tsv            40 shuffled replies (R121-R160, 4 per session), no condition
    blind_replies_rated.tsv      your ratings (template)
    blind_replies_rated_llm.tsv  the LLM's ratings (template)
    blind_sessions/S31-S40.txt   the 10 sessions under new random labels, for the Y/N coding
    blind_session_coding.tsv     template for that coding

For un-blinding afterwards (do not open until the ratings are done):
    _unblinding/key_replies.tsv, key_sessions.tsv, session_stats.tsv, turns.json

Parsing, counting and exclusions are run 1's own functions, unchanged. Session
labels are shuffled again, so the H numbers you played cannot be matched to
the S labels you code.
"""

import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import analyse  # noqa: E402
from analyse import blind_transcript, parse, stats, tsv  # noqa: E402

UNBLIND = HERE / "_unblinding"
SAMPLING_SEED = 8
REPLIES_PER_SESSION = 4
FIRST_REPLY, FIRST_SESSION = 121, 31
DIMENSIONS = ["responsive", "clear", "technique", "no_invention"]


def condition_of(session: str) -> str:
    entry = next(s for s in json.loads((UNBLIND / "schedule.json").read_text(encoding="utf-8"))["sessions"]
                 if s["label"] == session)
    return {"W": "with", "B": "without"}[entry["condition"]]


def extra_stats(s: dict) -> dict:
    """Where "I don't know" was said, and whether it answered a question; and how the session ended."""
    turns = s["turns"]
    idk = next((t for t in turns if t["child"].lower().rstrip(".") in ("i don't know", "i dont know")), None)
    if idk is None:
        found = {"idk_turn": "none", "idk_after_question": ""}
    else:
        heard = turns[idk["turn"] - 2]["reply"] if idk["turn"] > 1 else s["greeting"]
        found = {"idk_turn": idk["turn"], "idk_after_question": "Y" if "?" in heard else "N"}
    raw = (UNBLIND / "raw" / f"{s['session']}.txt").read_text(encoding="utf-8")
    found["ended_by"] = "player (/end)" if "Ended by the player" in raw else "Reachy's goodbye"
    found["child_turns"] = len(turns)
    return found


def main() -> None:
    sessions = [parse_session(f"H{i:02d}") for i in range(1, 11)]
    rng = random.Random(SAMPLING_SEED)

    # 4 replies per session, so every session counts equally, then shuffled together.
    picked = []
    for s in sessions:
        model = [t for t in s["turns"] if t["kind"] == "model"]
        for t in rng.sample(model, min(REPLIES_PER_SESSION, len(model))):
            picked.append({"session_id": s["session"], "condition": s["condition"], "turn": t["turn"],
                           "child_said": t["child"], "reachy_said": t["reply"]})
    rng.shuffle(picked)
    for i, row in enumerate(picked, start=FIRST_REPLY):
        row["blind_id"] = f"R{i}"

    labels = [f"S{i}" for i in range(FIRST_SESSION, FIRST_SESSION + len(sessions))]
    order = sessions[:]
    rng.shuffle(order)
    session_key = [{"label": label, "session_id": s["session"], "condition": s["condition"]}
                   for label, s in zip(labels, order)]

    (HERE / "blind_sessions").mkdir(exist_ok=True)
    for label, s in zip(labels, order):
        (HERE / "blind_sessions" / f"{label}.txt").write_text(blind_transcript(s, label), encoding="utf-8")

    label_of = {row["session_id"]: row["label"] for row in session_key}
    reply_no = {(s["session"], t["turn"]): n
                for s in sessions
                for n, t in enumerate((t for t in s["turns"] if t["kind"] == "model"), start=1)}
    for row in picked:
        row["blind_session"] = label_of[row["session_id"]]
        row["reply_no"] = reply_no[(row["session_id"], row["turn"])]
    (HERE / "blind_replies.tsv").write_text(
        tsv(picked, ["blind_id", "blind_session", "reply_no", "child_said", "reachy_said"]), encoding="utf-8")
    template = tsv([{"blind_id": row["blind_id"]} for row in sorted(picked, key=lambda r: int(r["blind_id"][1:]))],
                   ["blind_id", *DIMENSIONS])
    for name in ("blind_replies_rated.tsv", "blind_replies_rated_llm.tsv"):
        if not (HERE / name).exists():
            (HERE / name).write_text(template, encoding="utf-8")
    (HERE / "blind_session_coding.tsv").write_text(
        tsv([{"label": label} for label in labels],
            ["label", "followed_lesson_focus", "used_profile_detail", "focus_move_count", "note"]),
        encoding="utf-8")

    all_stats = [{**stats(s), **extra_stats(s)} for s in sessions]
    (UNBLIND / "key_replies.tsv").write_text(
        tsv(sorted(picked, key=lambda r: int(r["blind_id"][1:])), ["blind_id", "session_id", "condition", "turn"]),
        encoding="utf-8")
    (UNBLIND / "key_sessions.tsv").write_text(tsv(session_key, ["label", "session_id", "condition"]),
                                              encoding="utf-8")
    (UNBLIND / "session_stats.tsv").write_text(tsv(all_stats, list(all_stats[0])), encoding="utf-8")
    (UNBLIND / "turns.json").write_text(json.dumps(sessions, indent=2, ensure_ascii=False), encoding="utf-8")

    # Only condition-free checks are printed, so running this does not un-blind.
    print(f"{len(picked)} replies from {len(sessions)} sessions; "
          f"fewest model replies in a session: {min(r['model_replies'] for r in all_stats)}")


def parse_session(sid: str) -> dict:
    """run 1's parse(), with the condition from the hidden schedule (run 1 read it off the W/B name)."""
    original = analyse.CONDITION
    try:
        analyse.CONDITION = {"H": condition_of(sid)}
        return parse(sid, UNBLIND / "raw")
    finally:
        analyse.CONDITION = original


if __name__ == "__main__":
    main()
