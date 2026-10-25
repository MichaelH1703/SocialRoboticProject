"""Paste-ready Test 6 tables for v3, in the sheet's layout, from compare_detail.tsv.

Writes results/:
    top_table.tsv      transcript_id, feature, planted, reported, result (no header), T01-T60
    bottom_table.tsv   transcript_id, quote, result (no header): every quote in sections 1-5 of v3's plans
    results.tsv        hit rate, false alarms per transcript, quotes not in transcript: per set and all 60
Feature names follow the sheet's wording, as used for v2.
"""

import csv
import json
import re
from difflib import SequenceMatcher
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEST6 = HERE.parent
OUT = HERE / "results"
OUT.mkdir(exist_ok=True)
features = json.loads((TEST6 / "features.json").read_text(encoding="utf-8"))
PART = {"what_happened": "what happened", "ending": "how it ended"}
SETS = {"T01-T10": range(1, 11), "T11-T20": range(11, 21), "T21-T30": range(21, 31), "T31-T60": range(31, 61),
        "All 60": range(1, 61)}


def sheet_name(tid: str, feature: str) -> str:
    f = features.get(tid, {})
    if feature.startswith("left out: "):
        return "Leaves out: " + feature[10:]
    if feature == "uses because/so":
        uses = [w for w in ("because", "so") if f.get(w)]
        return "Uses " + " and ".join(f"'{w}'" for w in uses)
    if feature == "uses neither":
        return "Uses neither 'because' nor 'so'"
    if feature.startswith("emotion: "):
        return "Emotion word: " + feature[9:]
    if feature == "no emotion words":
        return "Uses no emotion words"
    m = re.match(r"feeling \((\w+)\): (.*)", feature)
    if m:
        return f"Feeling: {m.group(2)} ({m.group(1)})"
    if feature in ("gives a reason", "gives no reasons"):
        return feature.capitalize()
    if feature.startswith("false alarm: "):
        kind = feature[13:]
        return "False alarm: " + PART.get(kind, kind)
    return feature


with (HERE / "compare_detail.tsv").open(encoding="utf-8", newline="") as f:
    rows = [r for r in csv.DictReader(f, delimiter="\t") if r["version"] == "v3"]
top = []
for r in rows:
    planted, reported = r["planted"], r["reported"]
    result = ("hit" if reported == "Y" else "miss") if planted == "Y" else "false alarm"
    top.append((r["transcript_id"], sheet_name(r["transcript_id"], r["feature"]), planted, reported, result))
(OUT / "top_table.tsv").write_text("\n".join("\t".join(t) for t in top) + "\n", encoding="utf-8")


def norm(text: str) -> str:
    text = text.lower().replace("’", "'")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9' ]+", " ", text)).strip()


bottom, not_there = [], {}
for i in range(1, 61):
    tid = f"T{i:02d}"
    plan = (HERE / "plans" / f"{tid}.txt").read_text(encoding="utf-8").split("6. **Suggested Reachy Prompts**")[0]
    parts = re.split(r"\b(Therapist|Child)\.\s*", (TEST6 / "transcripts" / f"{tid}.txt").read_text(encoding="utf-8"))
    session = norm(" ".join(parts[k + 1] for k in range(1, len(parts) - 1, 2)))
    for line in plan.splitlines():
        line = line.strip()[2:] if line.strip().startswith("- ") else ""
        if not line or "did not link them" in line:
            continue  # that line names words the child did not use; it is not a quote
        named = re.match(r'(?:Named|Showed) "([^"]+)": "(.*)"$', line)
        if named:
            quotes = [named.group(2)]  # the feeling's label is v3's own word, not a quote
        elif line.startswith(("Used sequencing words:", "Used vague words:")):
            quotes = re.findall(r'"([^"]+)"', line)
        elif line.endswith('"') and '"' in line[:-1]:
            quotes = [line[line.index('"') + 1:-1]]
        else:
            quotes = []
        for q in quotes:
            sentences = [s for s in re.split(r"(?<=[.!?])\s+", q) if norm(s)]
            if all(norm(s) in session for s in sentences):
                result = "exact"
            else:
                # Without punctuation a quote can join the child's words from
                # several turns. It is still word for word if it is made of
                # verbatim stretches of the session (three words or more).
                words = norm(q).split()
                blocks = SequenceMatcher(None, words, session.split(), autojunk=False).get_matching_blocks()
                covered = sum(b.size for b in blocks if b.size >= 3)
                result = ("exact" if covered == len(words) else
                          "reworded" if covered >= 0.85 * len(words) else "not there")
            bottom.append((tid, q, result))
            not_there[tid] = not_there.get(tid, 0) + (result == "not there")
(OUT / "bottom_table.tsv").write_text("\n".join("\t".join(b) for b in bottom) + "\n", encoding="utf-8")

lines = ["set\thit rate\tfalse alarms per transcript\tquotes not in transcript"]
for name, ids in SETS.items():
    tids = {f"T{i:02d}" for i in ids}
    mine = [t for t in top if t[0] in tids]
    planted = [t for t in mine if t[2] == "Y"]
    hits = sum(t[4] == "hit" for t in planted)
    alarms = sum(t[4] == "false alarm" for t in mine)
    quotes = sum(1 for b in bottom if b[0] in tids)
    lines.append(f"{name}\t{hits / len(planted):.2f}\t{alarms / len(tids):.1f}\t"
                 f"{sum(not_there.get(t, 0) for t in tids)} of {quotes}")
(OUT / "results.tsv").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
print(len(top), "top rows;", len(bottom), "quotes")
