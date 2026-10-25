"""Turn run 2's raw logs into the blind rating materials, as ../analyse.py did for run 1.

For the rater (safe to open before rating):
    blind_replies.tsv            80 shuffled replies (R41-R120, 4 per session), no condition
    blind_sessions/S11-S30.txt   the 20 sessions under random labels, for the Y/N coding
    blind_session_coding.tsv     template for that coding

For un-blinding afterwards (do not open until the ratings are done):
    _unblinding/key_replies.tsv, key_sessions.tsv, session_stats.tsv, top_table.tsv, turns.json

Parsing, counting and exclusions are run 1's own functions, unchanged. Blind
IDs continue from run 1's (R01-R40, S01-S10) so the two runs can share a sheet.
"""

import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from analyse import blind_transcript, parse, stats, tsv  # noqa: E402

UNBLIND = HERE / "_unblinding"
settings = json.loads((HERE / "settings.json").read_text(encoding="utf-8"))


def idk_check(s: dict) -> dict:
    """Where the forced "I don't know" landed, and whether it answered a question."""
    turns = s["turns"]
    t = next(t for t in turns if t["child"] == "I don't know.")
    heard_before = turns[t["turn"] - 2]["reply"] if t["turn"] > 1 else s["greeting"]
    return {"idk_turn": t["turn"], "idk_after_question": "Y" if "?" in heard_before else "N"}


def main() -> None:
    sessions = [parse(sid, UNBLIND / "raw") for sid in settings["run_order"]]
    incomplete = [s["session"] for s in sessions if not s["complete"]]
    if incomplete:
        print(f"Warning: did not reach the planned ending: {', '.join(incomplete)}")
    rng = random.Random(settings["random_seed"])

    # 4 replies per session, so every session counts equally, then shuffled together.
    picked = []
    for s in sessions:
        model = [t for t in s["turns"] if t["kind"] == "model"]
        for t in rng.sample(model, min(settings["replies_per_session_for_rating"], len(model))):
            picked.append({"session_id": s["session"], "condition": s["condition"], "turn": t["turn"],
                           "child_said": t["child"], "reachy_said": t["reply"]})
    rng.shuffle(picked)
    for i, row in enumerate(picked, start=settings["first_blind_reply"]):
        row["blind_id"] = f"R{i:02d}"

    first = settings["first_blind_session"]
    labels = [f"S{i:02d}" for i in range(first, first + len(sessions))]
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
    (HERE / "blind_session_coding.tsv").write_text(
        tsv([{"label": label} for label in labels],
            ["label", "followed_lesson_focus", "used_profile_detail", "focus_move_count", "note"]),
        encoding="utf-8")

    all_stats = [{**stats(s), **idk_check(s)} for s in sessions]
    (UNBLIND / "key_replies.tsv").write_text(
        tsv(sorted(picked, key=lambda r: r["blind_id"]), ["blind_id", "session_id", "condition", "turn"]),
        encoding="utf-8")
    (UNBLIND / "key_sessions.tsv").write_text(tsv(session_key, ["label", "session_id", "condition"]),
                                              encoding="utf-8")
    (UNBLIND / "session_stats.tsv").write_text(tsv(all_stats, list(all_stats[0])), encoding="utf-8")
    top = sorted(all_stats, key=lambda r: (r["condition"] != "with", int(r["session_id"][1:])))
    (UNBLIND / "top_table.tsv").write_text(
        tsv(top, ["session_id", "condition", "followed_lesson_focus", "used_profile_detail",
                  "mean_words_per_reply"]), encoding="utf-8")
    (UNBLIND / "turns.json").write_text(json.dumps(sessions, indent=2, ensure_ascii=False), encoding="utf-8")

    # Only condition-free checks are printed, so running this does not un-blind.
    print(f"{len(picked)} replies, {len(sessions)} sessions; all complete: {not incomplete}")
    pairs_match = all(a["idk_turn"] == b["idk_turn"] for a, b in zip(all_stats[::2], all_stats[1::2]))
    print(f"\"I don't know\" turn matches within every pair: {pairs_match}")


if __name__ == "__main__":
    main()
