"""Check transcripts T21-T30 and their features sheet against T21_T30_spec.md.

Automatic checks:
- labels and turn counts (20-40);
- every quoted `words` entry is in the transcript and said by the right
  speaker (the child's for given/feeling/reason, the therapist's for a trap,
  the therapist's question and the child's reply for an asked or yes-only part);
- every transcript accounts for all five story parts and for reasons;
- the totals the spec asks for.

Prints PASS/FAIL per transcript, then the totals. Exits non-zero on any failure.
"""

import csv
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
IDS = [f"T{i}" for i in range(21, 31)]
PARTS = ("who", "where", "what happened", "how it ended")


def norm(text: str) -> str:
    text = text.lower().replace("’", "'")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9' ]+", " ", text)).strip()


def segments(text: str) -> list:
    parts = re.split(r"\b(Therapist|Child)\.\s*", text)
    return [(parts[i].lower(), parts[i + 1].strip()) for i in range(1, len(parts) - 1, 2)]


def said(piece: str, segs: list, speaker: str) -> bool:
    """Whether `piece` is said word for word, ignoring case and punctuation, in one of `speaker`'s turns."""
    p = norm(piece)
    return bool(p) and any(s == speaker and re.search(rf"(?<![a-z0-9']){re.escape(p)}(?![a-z0-9'])", norm(w))
                           for s, w in segs)


def pieces(words: str) -> list:
    return [p for p in re.split(r"…|\.\.\.", words) if norm(p)]


with (HERE / "T21_T30_features.tsv").open(encoding="utf-8", newline="") as f:
    rows = list(csv.DictReader(f, delimiter="\t", quoting=csv.QUOTE_NONE))

failed = False
for tid in IDS:
    path = HERE / "transcripts" / f"{tid}.txt"
    text = path.read_text(encoding="utf-8").strip()
    segs = segments(text)
    mine = [r for r in rows if r["transcript_id"] == tid]
    problems = []
    if not re.match(r"(Therapist|Child)\. ", text):
        problems.append("does not start with a label")
    if not 20 <= len(segs) <= 40:
        problems.append(f"{len(segs)} turns, not 20-40")
    for r in mine:
        kind, words = r["type"], r["words"].strip()
        if kind in ("given", "feeling", "reason"):
            missing = [p for p in pieces(words) if not said(p, segs, "child")]
            if not words or missing:
                problems.append(f"{kind} {r['part_or_feeling']!r}: not the child's words: {missing or 'empty'}")
        elif kind == "trap":
            missing = [p for p in pieces(words) if not said(p, segs, "therapist")]
            if not words or missing:
                problems.append(f"trap {r['part_or_feeling']!r}: not the therapist's words: {missing or 'empty'}")
        elif kind == "left_out" and r["how"] in ("asked", "yes-only"):
            qa = segments(words)
            if not (len(qa) == 2 and qa[0][0] == "therapist" and qa[1][0] == "child"
                    and said(qa[0][1], segs, "therapist") and said(qa[1][1], segs, "child")):
                problems.append(f"left_out {r['part_or_feeling']!r}: question and reply not found")
        elif kind not in ("left_out", "no_reasons"):
            problems.append(f"unknown type {kind!r}")
    accounted = {r["part_or_feeling"] for r in mine if r["type"] in ("given", "left_out")}
    for part in PARTS:
        if part not in accounted:
            problems.append(f"story part {part!r} neither given nor left out")
    felt = any(r["type"] == "feeling" for r in mine)
    felt_out = any(r["type"] == "left_out" and r["part_or_feeling"] == "how they felt" for r in mine)
    if felt == felt_out:
        problems.append("needs feeling rows or 'how they felt' left out (exactly one)")
    reasons = any(r["type"] == "reason" for r in mine)
    if reasons == any(r["type"] == "no_reasons" for r in mine):
        problems.append("needs reason rows or one no_reasons row (exactly one)")
    rough = sum(w.count(".") + w.count("?") + w.count("!") for _, w in segs) < len(segs) / 2
    failed |= bool(problems)
    print(f"{tid}: {'FAIL ' + '; '.join(problems) if problems else 'PASS'} ({len(segs)} turns{', rough' if rough else ''})")

# The totals the spec asks for.
left = [r for r in rows if r["type"] == "left_out"]
per = Counter(r["transcript_id"] for r in left)
how = Counter(r["how"] for r in left)
parts = Counter(r["part_or_feeling"] for r in left)
feel = [r for r in rows if r["type"] == "feeling"]
reason = [r for r in rows if r["type"] == "reason"]
traps = {r["transcript_id"] for r in rows if r["type"] == "trap"}
turns = {tid: len(segments((HERE / "transcripts" / f"{tid}.txt").read_text(encoding="utf-8"))) for tid in IDS}
totals = [
    ("parts left out, 12-18", 12 <= len(left) <= 18, len(left)),
    ("each part left out at least twice", all(parts[p] >= 2 for p in PARTS + ("how they felt",)), dict(parts)),
    ("silent at least 6", how["silent"] >= 6, how["silent"]),
    ("asked at least 4", how["asked"] >= 4, how["asked"]),
    ("yes-only at least 1", how["yes-only"] >= 1, how["yes-only"]),
    ("at most 3 per transcript", max(per.values()) <= 3, dict(per)),
    ("nothing left out in at least 1", sum(per[t] == 0 for t in IDS) >= 1, [t for t in IDS if per[t] == 0]),
    ("feeling as a phrase in at least 5", len({r["transcript_id"] for r in feel if r["how"] == "phrase"}) >= 5,
     len({r["transcript_id"] for r in feel if r["how"] == "phrase"})),
    ("no feelings in at least 2", parts["how they felt"] >= 2, parts["how they felt"]),
    ("2+ feelings in at least 2", sum(c >= 2 for c in Counter(r["transcript_id"] for r in feel).values()) >= 2,
     sum(c >= 2 for c in Counter(r["transcript_id"] for r in feel).values())),
    ("reason without because/so in at least 3", len({r["transcript_id"] for r in reason if r["how"] != "because-so"}) >= 3,
     len({r["transcript_id"] for r in reason if r["how"] != "because-so"})),
    ("no reasons in at least 2", sum(r["type"] == "no_reasons" for r in rows) >= 2, sum(r["type"] == "no_reasons" for r in rows)),
    ("because/so reason in at least 2", len({r["transcript_id"] for r in reason if r["how"] == "because-so"}) >= 2,
     len({r["transcript_id"] for r in reason if r["how"] == "because-so"})),
    ("therapist trap in at least 6", len(traps) >= 6, len(traps)),
    ("more than 30 turns in at least 2", sum(n > 30 for n in turns.values()) >= 2, sum(n > 30 for n in turns.values())),
]
print()
for name, ok, value in totals:
    failed |= not ok
    print(f"{'ok  ' if ok else 'FAIL'} {name}: {value}")
sys.exit(1 if failed else 0)
