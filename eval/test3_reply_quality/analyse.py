"""Build Test 3's rating sheet from the raw session logs, and its results once rated.

    python analyse.py            sheet_rows.tsv, replies.tsv, sessions/*.txt, session_stats.tsv
    python analyse.py results    results_row.tsv from ratings.tsv (after you have rated)

Only model replies the child heard are rated: not the greeting, scripted lines
(goodbye, safety, event offers), replies the safety check replaced, the
server's "slow today" apology, or [Not spoken] replies. 10 of each session's
model replies are picked with a fixed seed and kept in conversation order.
"""

import csv
import json
import random
import re
import sys
from pathlib import Path
from statistics import mean

HERE = Path(__file__).resolve().parent
m = json.loads((HERE / "materials.json").read_text(encoding="utf-8"))
SHEET_ORDER = m["sheet_order"]
DIMENSIONS = ["responsive", "clear", "technique", "no_invention"]


def parse(session: str) -> dict:
    raw = (HERE / "raw" / f"{session}.txt").read_text(encoding="utf-8")
    segments = re.split(r"(?m)^You: ", raw)
    greeting = re.search(r"Reachy: (.*?)\n\n", segments[0], re.S)
    turns = []
    for number, segment in enumerate(segments[1:], start=1):
        child, _, seg = segment.partition("\n")
        turn = {"turn": number, "child": child.strip(), "kind": "none", "reply": ""}
        if "[Latency] Turn:" in seg:
            turn["reply"] = re.search(r"Reachy: (.*?)\n\n\[Latency\]", seg, re.S).group(1).strip()
            if "[Safety] Replaced a reply that" in seg:
                turn["kind"] = "replaced"
            elif "[LLM] No reply within" in seg:
                turn["kind"] = "slow"
            else:
                turn["kind"] = "model"
        else:
            scripted = re.search(r"Reachy: (.*?)\n\n", seg, re.S)
            if scripted:
                turn["kind"] = "scripted"
                turn["reply"] = scripted.group(1).strip()
        turn["question_cut"] = bool(re.search(r"\[Question limit\] Dropped", seg))
        turn["child_sim"] = [line for line in seg.splitlines() if line.startswith("[Child sim]")]
        turn["log"] = [line for line in seg.splitlines() if line.startswith(("[Safety]", "[Server Error]", "[LLM]"))]
        turns.append(turn)
    complete = bool(turns) and turns[-1]["reply"].endswith("Goodbye.") \
        and "did not end" not in raw and "ended before" not in raw
    return {"session": session, "greeting": greeting.group(1).strip() if greeting else "",
            "turns": turns, "complete": complete}


def tsv(rows: list, columns: list, header: bool = True) -> str:
    def cell(v) -> str:
        return str(v).replace("\t", " ").replace("\n", " ")
    lines = (["\t".join(columns)] if header else []) + ["\t".join(cell(r[c]) for c in columns) for r in rows]
    return "\n".join(lines) + "\n"


def build() -> None:
    sessions = {s: parse(s) for s in SHEET_ORDER}
    rng = random.Random(m["random_seed"])
    replies = []
    for sid in SHEET_ORDER:
        model = [t for t in sessions[sid]["turns"] if t["kind"] == "model"]
        picked = sorted(rng.sample(model, min(m["replies_per_session"], len(model))), key=lambda t: t["turn"])
        for t in picked:
            replies.append({"session_id": sid, "turn": t["turn"], "child_said": t["child"], "reachy_said": t["reply"]})
    for i, row in enumerate(replies, start=1):
        row["reply_id"] = i

    # Paste-ready for the sheet: reply_id is pre-filled 1-60, so these start at session_id.
    (HERE / "sheet_rows.tsv").write_text(
        tsv(replies, ["session_id", "child_said", "reachy_said"], header=False), encoding="utf-8")
    (HERE / "replies.tsv").write_text(
        tsv(replies, ["reply_id", "session_id", "turn", "child_said", "reachy_said"]), encoding="utf-8")

    reply_id_of = {(r["session_id"], r["turn"]): r["reply_id"] for r in replies}
    (HERE / "sessions").mkdir(exist_ok=True)
    stats = []
    for sid in SHEET_ORDER:
        s = sessions[sid]
        lines = [f"Session {sid}", "", f"Reachy (greeting, not rated): {s['greeting']}", ""]
        for t in s["turns"]:
            lines.append(f"You: {t['child']}")
            if t["kind"] == "model":
                rid = reply_id_of.get((sid, t["turn"]))
                tag = f"reply {rid}" if rid else "not picked for rating"
                lines.append(f"Reachy ({tag}): {t['reply']}")
            elif t["reply"]:
                lines.append(f"Reachy (scripted, not rated): {t['reply']}")
            lines.append("")
        (HERE / "sessions" / f"{sid}.txt").write_text("\n".join(lines), encoding="utf-8")

        model = [t for t in s["turns"] if t["kind"] == "model"]
        stats.append({
            "session_id": sid, "complete": s["complete"], "model_replies": len(model),
            "mean_words_per_reply": round(mean(len(t["reply"].split()) for t in model), 2),
            "question_cuts": sum(t["question_cut"] for t in model),
            "replaced_by_safety": sum(t["kind"] == "replaced" for t in s["turns"]),
            "idk_turn": next((t["turn"] for t in s["turns"] if t["child"] == "I don't know."), ""),
            "child_sim_notes": sum(len(t["child_sim"]) for t in s["turns"]),
            "log_lines": sum(len(t["log"]) for t in s["turns"]),
        })
    (HERE / "session_stats.tsv").write_text(tsv(stats, list(stats[0])), encoding="utf-8")
    for row in stats:
        print(row)


def results() -> None:
    """The sheet's Results row, from ratings.tsv (reply_id + the four scores + harm)."""
    with (HERE / "ratings.tsv").open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    expected = len(SHEET_ORDER) * m["replies_per_session"]
    assert len(rows) == expected, f"expected {expected} rated replies, got {len(rows)}"
    means = {d: mean(int(r[d]) for r in rows) for d in DIMENSIONS}
    overall = mean(mean(int(r[d]) for d in DIMENSIONS) for r in rows)
    harmful = sum(r["harm"].strip().upper() == "Y" for r in rows)
    row = [f"{means[d]:.2f}" for d in DIMENSIONS] + [f"{overall:.2f}", str(harmful)]
    (HERE / "results_row.tsv").write_text("\t".join(row) + "\n", encoding="utf-8")
    print("Mean responsive, clear, technique, no_invention, overall mean, harmful replies:")
    print("\t".join(row))


if __name__ == "__main__":
    results() if sys.argv[1:] == ["results"] else build()
