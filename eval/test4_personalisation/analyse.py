"""Turn Test 4's raw session logs into the blind rating materials and the stats.

For the rater (safe to open before rating):
    blind_replies.tsv          40 shuffled replies (20 per condition), no condition
    blind_sessions/S01-S10.txt the 10 sessions under random labels, for the Y/N coding
    blind_session_coding.tsv   template for that coding

For un-blinding afterwards (do not open until the ratings are done):
    _unblinding/key_replies.tsv     blind reply id -> session, condition
    _unblinding/key_sessions.tsv    blind session label -> session, condition
    _unblinding/session_stats.tsv   per-session counts, words per reply, automatic checks
    _unblinding/top_table.tsv       the sheet's top table, Y/N columns left for the coding

Only model replies the child heard are rated or counted: not the greeting,
scripted lines (goodbye, safety, event offers), replies the safety check
replaced, the server's "slow today" apology, or [Not spoken] replies.
"""

import json
import sys
import random
import re
from pathlib import Path
from statistics import mean

HERE = Path(__file__).resolve().parent
UNBLIND = HERE / "_unblinding"
m = json.loads((HERE / "materials.json").read_text(encoding="utf-8"))
CONDITION = {"W": "with", "B": "without"}

# Automatic checks, a cross-check on the human coding only. Keyword matching
# cannot judge meaning, so these flag candidates; criteria.md decides.
PROFILE_WORDS = re.compile(
    r"\b(horses?|riding|ride|rode|pony|ponies|pepper|stables?|meadowbank|theo|brother|art|drawing|draw|"
    r"dogs?|bark\w*|rear\w*|saturdays?)\b", re.I)
EXPLANATION = re.compile(r"\b(why|because|how come|what made)\b", re.I)
PERSPECTIVE = re.compile(
    r"\b(how (do|did|does) you think|how did (mia|she|he|they|everyone|her|the others)\b.*\bfeel|"
    r"what did (mia|she|he|they|everyone) think)", re.I)
CHOICE = re.compile(r"\bor\b[^.?!]*\?", re.I)


def parse(session: str, raw_dir: Path = UNBLIND / "raw") -> dict:
    raw = (raw_dir / f"{session}.txt").read_text(encoding="utf-8")
    segments = re.split(r"(?m)^You: ", raw)
    greeting = re.search(r"Reachy: (.*?)\n\n", segments[0], re.S)
    turns = []
    for number, segment in enumerate(segments[1:], start=1):
        child, _, seg = segment.partition("\n")
        turn = {"turn": number, "child": child.strip(), "kind": "none", "reply": "",
                "question_cut": "", "replaced_original": "", "not_spoken": ""}
        if "[Latency] Turn:" in seg:
            turn["reply"] = re.search(r"Reachy: (.*?)\n\n\[Latency\]", seg, re.S).group(1).strip()
            if "[Safety] Replaced a reply that" in seg:
                turn["kind"] = "replaced"
                turn["replaced_original"] = re.search(r"\[Safety\] Replaced a reply that (.*)", seg).group(1)
            elif "[LLM] No reply within" in seg:
                turn["kind"] = "slow"
            else:
                turn["kind"] = "model"
        else:
            scripted = re.search(r"Reachy: (.*?)\n\n", seg, re.S)
            if scripted:
                turn["kind"] = "scripted"
                turn["reply"] = scripted.group(1).strip()
        cut = re.search(r"\[Question limit\] Dropped: (.*)", seg)
        if cut:
            turn["question_cut"] = cut.group(1)
        dropped = re.search(r"\[Not spoken\] [^:]*: (.*)", seg)
        if dropped:
            turn["not_spoken"] = dropped.group(1)
        turn["log"] = [line for line in seg.splitlines() if line.startswith(("[Safety]", "[Server Error]", "[LLM]"))]
        turn["child_sim"] = [line for line in seg.splitlines() if line.startswith("[Child sim]")]
        turns.append(turn)
    # Complete means the planned ending was reached: the final goodbye line.
    complete = bool(turns) and turns[-1]["kind"] == "scripted" and turns[-1]["reply"].endswith("Goodbye.") \
        and "did not end" not in raw and "ended before" not in raw
    return {"session": session, "condition": CONDITION[session[0]],
            "greeting": greeting.group(1).strip() if greeting else "", "turns": turns,
            "complete": complete}


def stats(s: dict) -> dict:
    model = [t for t in s["turns"] if t["kind"] == "model"]
    replies = [t["reply"] for t in model]
    return {
        "session_id": s["session"],
        "condition": s["condition"],
        "model_replies": len(model),
        "mean_words_per_reply": round(mean(len(r.split()) for r in replies), 2) if replies else "",
        "question_cuts": sum(1 for t in model if t["question_cut"]),
        "replaced_by_safety": sum(1 for t in s["turns"] if t["kind"] == "replaced"),
        "auto_profile_word_replies": sum(1 for r in replies if PROFILE_WORDS.search(r)),
        "auto_explanation_replies": sum(1 for r in replies if EXPLANATION.search(r)),
        "auto_perspective_replies": sum(1 for r in replies if PERSPECTIVE.search(r)),
        "auto_choice_replies": sum(1 for r in replies if CHOICE.search(r)),
        "complete": s["complete"],
    }


def tsv(rows: list, columns: list) -> str:
    def cell(v) -> str:
        return str(v).replace("\t", " ").replace("\n", " ")
    return "\n".join(["\t".join(columns)] + ["\t".join(cell(r.get(c, "")) for c in columns) for r in rows]) + "\n"


def blind_transcript(s: dict, label: str) -> str:
    lines = [f"Session {label}", "", f"Reachy (greeting, not coded): {s['greeting']}", ""]
    numbered = 0
    for t in s["turns"]:
        lines.append(f"You: {t['child']}")
        if t["kind"] == "model":
            numbered += 1
            lines.append(f"Reachy [{numbered}]: {t['reply']}")
        elif t["reply"]:
            lines.append(f"Reachy (scripted, not coded): {t['reply']}")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    sessions = [parse(sid) for sid in m["run_order"]]
    rng = random.Random(m["random_seed"])

    # 4 replies per session, so every session counts equally, then shuffled together.
    picked = []
    for s in sessions:
        model = [t for t in s["turns"] if t["kind"] == "model"]
        for t in rng.sample(model, min(m["replies_per_session_for_rating"], len(model))):
            picked.append({"session_id": s["session"], "condition": s["condition"], "turn": t["turn"],
                           "child_said": t["child"], "reachy_said": t["reply"]})
    rng.shuffle(picked)
    for i, row in enumerate(picked, start=1):
        row["blind_id"] = f"R{i:02d}"

    labels = [f"S{i:02d}" for i in range(1, len(sessions) + 1)]
    order = sessions[:]
    rng.shuffle(order)
    session_key = [{"label": label, "session_id": s["session"], "condition": s["condition"]}
                   for label, s in zip(labels, order)]

    (HERE / "blind_sessions").mkdir(exist_ok=True)
    for label, s in zip(labels, order):
        (HERE / "blind_sessions" / f"{label}.txt").write_text(blind_transcript(s, label), encoding="utf-8")

    # Where each reply sits in the blind transcripts, so the rater can read the
    # conversation before it. Session labels carry no condition.
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

    all_stats = [stats(s) for s in sessions]
    (UNBLIND / "key_replies.tsv").write_text(
        tsv(sorted(picked, key=lambda r: r["blind_id"]), ["blind_id", "session_id", "condition", "turn"]),
        encoding="utf-8")
    (UNBLIND / "key_sessions.tsv").write_text(tsv(session_key, ["label", "session_id", "condition"]),
                                              encoding="utf-8")
    (UNBLIND / "session_stats.tsv").write_text(tsv(all_stats, list(all_stats[0])), encoding="utf-8")
    top = sorted(all_stats, key=lambda r: (r["condition"] != "with", r["session_id"]))
    (UNBLIND / "top_table.tsv").write_text(
        tsv(top, ["session_id", "condition", "followed_lesson_focus", "used_profile_detail",
                  "mean_words_per_reply"]), encoding="utf-8")
    (UNBLIND / "turns.json").write_text(json.dumps(sessions, indent=2, ensure_ascii=False), encoding="utf-8")

    for row in all_stats:
        print(row)


def pilot() -> None:
    """Readable pilot transcripts, labelled 1 and 2 rather than by condition."""
    sessions = [parse(sid, HERE / "pilot" / "raw") for sid in ("W0", "B0")]
    random.Random(m["random_seed"]).shuffle(sessions)
    for number, s in enumerate(sessions, start=1):
        label = f"pilot_{number}"
        (HERE / "pilot" / f"{label}.txt").write_text(blind_transcript(s, label), encoding="utf-8")
        print(label, "=", s["session"], stats(s))
        for t in s["turns"]:
            for note in t["child_sim"] + t["log"]:
                print("   ", note)


if __name__ == "__main__":
    pilot() if sys.argv[1:] == ["pilot"] else main()
