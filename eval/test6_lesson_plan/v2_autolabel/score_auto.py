"""Propose Test 6 scores for the v2 plans, using v1's scoring rules (../README.md).

v2 builds sections 2-4 of the plan from fixed sentences ("Did not say where it
happened.", "Gave a reason: ...", "Named feelings: ..."), so whether each
planted feature is reported can be read off the plan text. Section 1, the
model's summary, and any line needing judgement are printed to be read by
hand. Who really said each quoted or credited word is looked up in the
original labelled transcript.

Writes scoring_auto.tsv and quotes_auto.tsv. After checking, they are copied
to scoring.tsv and quotes.tsv, with any hand judgements added.
"""

import json
import re
from difflib import SequenceMatcher
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEST6 = HERE.parent
PARTS = {"who": "who was there", "where": "where it happened", "what happened": "what happened",
         "how it ended": "how it ended"}  # features.json name -> the plan's wording


def norm(text: str) -> str:
    text = text.lower().replace("’", "'")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9' ]+", " ", text)).strip()


def segments(text: str) -> list:
    parts = re.split(r"\b(Therapist|Child)\.\s*", text)
    return [(parts[i].lower(), parts[i + 1].strip()) for i in range(1, len(parts) - 1, 2)]


def sections(plan: str) -> dict:
    """{1: [lines], ...} from the numbered headings."""
    out, current = {}, None
    for raw in plan.splitlines():
        heading = re.match(r"(\d)\. \*\*", raw)
        if heading:
            current = int(heading.group(1))
            out[current] = []
        elif current and raw.strip().startswith("- "):
            out[current].append(raw.strip()[2:])
    return out


def said_by(text: str, segs: list) -> str:
    """Who said each sentence of `text`: child, therapist, both, or '' if no one did word for word."""
    speakers = set()
    for sentence in re.split(r"(?<=[.!?])\s+", text.strip()):
        s = norm(sentence)
        found = {spk for spk, words in segs if s and re.search(rf"(?<![a-z0-9']){re.escape(s)}(?![a-z0-9'])", norm(words))}
        if not found:
            return ""
        speakers |= found
    return "/".join(sorted(speakers))


features = json.loads((TEST6 / "features.json").read_text(encoding="utf-8"))
rows = ["transcript_id\tfeature\tplanted\treported\tresult\tevidence (plan, sections 1-4)\tnote"]
quote_rows = ["transcript_id\tquote\tauto_match\tsaid_by\tclosest_turn\tsimilarity"]
for plan_path in sorted((HERE / "plans").glob("T*.txt")):
    tid = plan_path.stem
    f = features[tid]
    plan = plan_path.read_text(encoding="utf-8")
    sec = sections(plan)
    s2, s3, s4 = sec.get(2, []), sec.get(3, []), sec.get(4, [])
    segs = segments((TEST6 / "transcripts" / f"{tid}.txt").read_text(encoding="utf-8"))
    child_words = set(norm(" ".join(w for s, w in segs if s == "child")).split())

    def row(feature, planted, reported, evidence="", note=""):
        if planted == "Y":
            result = "hit" if reported else "miss"
        else:
            result = "false alarm" if reported is True else reported
        rows.append(f"{tid}\t{feature}\t{planted}\t{'Y' if reported is True else 'N' if reported is False else '?'}"
                    f"\t{result}\t{evidence}\t{note}")

    feelings_gap = "Did not name any feelings." in s3 + s4
    named = next((l.split(": ", 1)[1].split(", ") for l in s2 if l.startswith("Named feelings:")), [])
    reasons = [l.split(": ", 1)[1] for l in s2 if l.startswith("Gave a reason:")]
    reasons_gap = next((l for l in s3 if l.startswith("Did not give any reasons")), "")

    for part in f["omits"]:
        if part == "how they felt":
            row("Leaves out: how they felt", "Y", feelings_gap, "Did not name any feelings." if feelings_gap else "")
        else:
            line = f"Did not say {PARTS[part]}."
            row(f"Leaves out: {part}", "Y", line in s3, line if line in s3 else "")
    uses = [w for w in ("because", "so") if f[w]]
    if uses:
        row("Uses " + " and ".join(f"'{w}'" for w in uses), "Y", bool(reasons) and not reasons_gap,
            "; ".join(f"Gave a reason: {r}" for r in reasons))
    else:
        row("Uses neither 'because' nor 'so'", "Y", bool(reasons_gap), reasons_gap)
    for word in f["emotions"]:
        row(f"Emotion word: {word}", "Y", word in named, f"Named feelings: {', '.join(named)}" if word in named else "")
    if not f["emotions"]:
        row("Uses no emotion words", "Y", feelings_gap, "Did not name any feelings." if feelings_gap else "")

    # False alarms, within the three planted categories only.
    for part, wording in PARTS.items():
        line = f"Did not say {wording}."
        if line in s3 and part not in f["omits"]:
            row(f"False alarm: {part}", "N", True, line, "CHECK the child gave it")
    if uses and reasons_gap:
        row("False alarm: missing reasons", "N", True, reasons_gap)
    if f["emotions"] and feelings_gap:
        row("False alarm: missing emotion words", "N", True, "Did not name any feelings.")
    if uses and "Did not say why they felt that way." in s4:
        row("False alarm?: why they felt", "N", "JUDGE", "Did not say why they felt that way.",
            "JUDGE: did the child give a reason for a feeling?")

    # Credit to the wrong speaker (notes, not scored).
    notes = [f"credits '{w}' to the child" for w in named if w not in f["emotions"]]
    notes += [f"reason quoted is not the child's ({said_by(r.strip(chr(34)), segs) or 'not found'}): {r}"
              for r in reasons if "child" not in said_by(r.strip('"'), segs)]
    for l in s2:
        if l.startswith(("Used sequencing words:", "Used vague words:")):
            notes += [f"'{w}' is not the child's word" for w in re.findall(r'"([^"]+)"', l) if w not in child_words]
    if notes:
        rows.append(f"{tid}\t(not scored)\t\t\t\t\t" + "; ".join(notes))

    for quote in re.findall(r"[\"“]([^\"”]{1,300})[\"”]", plan.split("6. **Suggested Reachy Prompts**")[0]):
        who = said_by(quote, segs)
        if who:
            quote_rows.append(f"{tid}\t{quote}\texact\t{who}\t\t1.00")
            continue
        best = max(segs, key=lambda sw: SequenceMatcher(None, norm(quote), norm(sw[1])).ratio())
        ratio = SequenceMatcher(None, norm(quote), norm(best[1])).ratio()
        quote_rows.append(f"{tid}\t{quote}\tcheck\t{best[0]}\t{best[1]}\t{ratio:.2f}")

    print(f"\n== {tid} ({f['event']}) ==\nSUMMARY: {' | '.join(sec.get(1, []))}")
    for r in rows:
        if r.startswith(tid) and ("CHECK" in r or "JUDGE" in r or "(not scored)" in r):
            print("  " + r.split("\t", 1)[1].replace("\t", " | "))

(HERE / "scoring_auto.tsv").write_text("\n".join(rows) + "\n", encoding="utf-8")
(HERE / "quotes_auto.tsv").write_text("\n".join(quote_rows) + "\n", encoding="utf-8")
print("\nQuotes needing a look:")
print("\n".join(q for q in quote_rows[1:] if "\tcheck\t" in q or "\texact\ttherapist" in q) or "  none")
