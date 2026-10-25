"""Build run 4's blind coding and rating materials (seed 10).

Coding (Q1/Q2): the 40 run 4 sessions plus run 3's H01-H10, so the pooled 50 are
coded with the same questions; shuffled, labelled S41-S90. Each transcript is
coded against one version's lesson focus and style checklist: a "with" session
against its own version's; a run 4 "without" session against a version assigned
here (5 per version, seed 10), so every version is shown with 10 transcripts and
the checklist on screen says nothing about the condition; run 3's sessions (all
v1 in run 3) against v1's.

Ratings: 1 reply per run 4 session (20 per condition), seed 10, shuffled,
R161-R200.

For the coders and raters (safe to open):
    blind_sessions/S41-S90.txt        transcript, with its lesson focus and style checklist on top
    blind_session_coding.tsv          yours (filled by code_sessions.py)
    blind_session_coding_llm.tsv      the LLM's (template)
    blind_replies.tsv                 the 40 replies to rate
    blind_replies_rated.tsv           yours (template)
    blind_replies_rated_llm.tsv       the LLM's (template)
Keys and per-session numbers go to _unblinding/.

Parsing, counting and exclusions are run 1's own functions (../analyse.py), as
in runs 2 and 3: mean words per reply is over model replies the child heard.
"""

import json
import random
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
T4 = HERE.parent
sys.path.insert(0, str(T4))
import analyse  # noqa: E402
from analyse import parse, stats, tsv  # noqa: E402

UNBLIND = HERE / "_unblinding"
RUN3 = T4 / "run3_human" / "_unblinding"
SEED = 10
FIRST_REPLY, FIRST_SESSION = 161, 41
VERSIONS = ["v1", "v2", "v3", "v4"]
versions = json.loads((HERE / "versions.json").read_text(encoding="utf-8"))


def lesson_focus(version: str) -> str:
    plan = (T4 / "lesson_plan.txt" if version == "v1" else HERE / f"lesson_plan_{version}.txt").read_text(encoding="utf-8")
    section = re.search(r"Recommended Future Lesson Focus:?\**:?[ \t]*\n(.*?)(?:\n\s*\d+\.\s|\Z)", plan, re.S).group(1)
    return "\n".join(line.strip() for line in section.strip().splitlines() if line.strip())


def schedule(folder: Path) -> dict:
    return {s["label"]: s for s in json.loads((folder / "schedule.json").read_text(encoding="utf-8"))["sessions"]}


def load(session: str, folder: Path, condition: str) -> dict:
    original = analyse.CONDITION
    try:
        analyse.CONDITION = {"H": condition}
        return parse(session, folder / "raw")
    finally:
        analyse.CONDITION = original


def extra(s: dict, folder: Path) -> dict:
    turns = s["turns"]
    idk = next((t for t in turns if t["child"].lower().rstrip(".") in ("i don't know", "i dont know")), None)
    heard = (turns[idk["turn"] - 2]["reply"] if idk["turn"] > 1 else s["greeting"]) if idk else ""
    raw = (folder / "raw" / f"{s['session']}.txt").read_text(encoding="utf-8")
    return {"idk_turn": idk["turn"] if idk else "none", "idk_after_question": ("Y" if "?" in heard else "N") if idk else "",
            "ended_by": "player (/end)" if "Ended by the player" in raw else "Reachy's goodbye",
            "child_turns": len(turns)}


def transcript(s: dict, label: str, version: str) -> str:
    checklist = "\n".join(f"  {i}. {item}" for i, item in enumerate(versions[version]["style_checklist"], 1))
    focus = "\n".join(f"  {line}" for line in lesson_focus(version).splitlines())
    lines = [f"Session {label}", "", "Lesson focus:", focus, "", "Profile style checklist:", checklist, "",
             f"Reachy (greeting, not coded): {s['greeting']}", ""]
    n = 0
    for t in s["turns"]:
        lines.append(f"You: {t['child']}")
        if t["kind"] == "model":
            n += 1
            lines.append(f"Reachy [{n}]: {t['reply']}")
        elif t["reply"]:
            lines.append(f"Reachy (scripted, not coded): {t['reply']}")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    rng = random.Random(SEED)
    s4, s3 = schedule(UNBLIND), schedule(RUN3)
    sessions = []
    for h in [f"H{i:02d}" for i in range(1, 11)]:
        cond = "with" if s3[h]["condition"] == "W" else "without"
        sessions.append({**load(h, RUN3, cond), "run": 3, "version": "v1", "folder": RUN3})
    blank_versions = [v for v in VERSIONS for _ in range(5)]
    rng.shuffle(blank_versions)
    for h in [f"H{i}" for i in range(11, 51)]:
        c = s4[h]["condition"]
        cond, version = ("with", c[2:]) if c.startswith("W") else ("without", blank_versions.pop())
        sessions.append({**load(h, UNBLIND, cond), "run": 4, "version": version, "folder": UNBLIND})

    # Ratings: 1 reply from each run 4 session, then shuffled.
    picked = []
    for s in sessions:
        if s["run"] != 4:
            continue
        t = rng.choice([t for t in s["turns"] if t["kind"] == "model"])
        picked.append({"session_id": s["session"], "condition": s["condition"], "turn": t["turn"],
                       "child_said": t["child"], "reachy_said": t["reply"]})
    rng.shuffle(picked)
    for i, row in enumerate(picked, start=FIRST_REPLY):
        row["blind_id"] = f"R{i}"

    # Coding: all 50, shuffled, new labels.
    order = sessions[:]
    rng.shuffle(order)
    labels = [f"S{i}" for i in range(FIRST_SESSION, FIRST_SESSION + len(order))]
    (HERE / "blind_sessions").mkdir(exist_ok=True)
    for label, s in zip(labels, order):
        (HERE / "blind_sessions" / f"{label}.txt").write_text(transcript(s, label, s["version"]), encoding="utf-8")
    label_of = {s["session"]: label for label, s in zip(labels, order)}
    reply_no = {(s["session"], t["turn"]): n for s in sessions
                for n, t in enumerate((t for t in s["turns"] if t["kind"] == "model"), start=1)}
    for row in picked:
        row["blind_session"], row["reply_no"] = label_of[row["session_id"]], reply_no[(row["session_id"], row["turn"])]

    by_id = lambda rows: sorted(rows, key=lambda r: int(r["blind_id"][1:]))  # noqa: E731
    (HERE / "blind_replies.tsv").write_text(
        tsv(picked, ["blind_id", "blind_session", "reply_no", "child_said", "reachy_said"]), encoding="utf-8")
    dims = ["responsive", "clear", "technique", "no_invention"]
    for name in ("blind_replies_rated.tsv", "blind_replies_rated_llm.tsv"):
        if not (HERE / name).exists():
            (HERE / name).write_text(tsv([{"blind_id": r["blind_id"]} for r in by_id(picked)], ["blind_id", *dims]),
                                     encoding="utf-8")
    coding_cols = ["label", "followed_lesson_focus", "followed_profile_instructions", "note"]
    if not (HERE / "blind_session_coding_llm.tsv").exists():
        (HERE / "blind_session_coding_llm.tsv").write_text(tsv([{"label": l} for l in labels], coding_cols),
                                                           encoding="utf-8")

    (UNBLIND / "key_replies.tsv").write_text(
        tsv(by_id(picked), ["blind_id", "session_id", "condition", "turn"]), encoding="utf-8")
    (UNBLIND / "key_sessions.tsv").write_text(
        tsv([{"label": l, "session_id": s["session"], "condition": s["condition"], "version": s["version"],
              "run": s["run"]} for l, s in zip(labels, order)], ["label", "session_id", "condition", "version", "run"]),
        encoding="utf-8")
    all_stats = [{**stats(s), **extra(s, s["folder"]), "version": s["version"], "run": s["run"]} for s in sessions]
    (UNBLIND / "session_stats.tsv").write_text(tsv(all_stats, list(all_stats[0])), encoding="utf-8")
    for s in sessions:
        s.pop("folder")
    (UNBLIND / "turns.json").write_text(json.dumps(sessions, indent=2, ensure_ascii=False), encoding="utf-8")
    # Condition-free checks only.
    print(f"{len(picked)} replies to rate (R{FIRST_REPLY}-R{FIRST_REPLY + len(picked) - 1}); "
          f"{len(labels)} transcripts to code ({labels[0]}-{labels[-1]}).")


if __name__ == "__main__":
    main()
