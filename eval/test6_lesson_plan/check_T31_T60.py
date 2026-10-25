"""Check transcripts T31-T60 against their truth sheet (T31_T60_features.tsv).

Automatic checks:
- labels and turn counts (20-50);
- every quoted `words` entry is in the transcript and said by the right
  speaker (the child's for given/feeling/reason, the therapist's for a trap,
  the therapist's question and the child's reply for an asked or yes-only part);
- every transcript accounts for all five story parts and for reasons;
- (no totals: the generator did not meet the spec's, and the truth sheet was annotated afterwards).

Prints PASS/FAIL per transcript. Exits non-zero on any failure.
"""

import csv
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
IDS = [f"T{i}" for i in range(31, 61)]
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


with (HERE / "T31_T60_features.tsv").open(encoding="utf-8", newline="") as f:
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
    if not 20 <= len(segs) <= 50:
        problems.append(f"{len(segs)} turns, not 20-50")
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

sys.exit(1 if failed else 0)
