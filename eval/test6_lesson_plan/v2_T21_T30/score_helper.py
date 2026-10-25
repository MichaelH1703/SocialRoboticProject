"""Propose T21-T30 scores where they are mechanical, and print what needs judging by meaning.

Mechanical (from v2's fixed sentences in sections 2-4):
- a planted left-out part is reported if section 3 says "Did not say <part>."
  (or, for how they felt, "Did not name any feelings.");
- a given part reported as missing, "no feelings" when the child showed one,
  and "no reasons" when the child gave one are false alarms.

Printed for judgement: each plan's sections 1-4 next to the planted
feelings, reasons, traps and yes-only parts. Feelings and reasons are scored
by meaning (T21_T30_spec.md), so these are judged by reading. Writes
scoring_proposed.tsv and quotes_auto.tsv.
"""

import csv
import re
from difflib import SequenceMatcher
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEST6 = HERE.parent
WORDING = {"who": "who was there", "where": "where it happened", "what happened": "what happened",
           "how it ended": "how it ended"}


def norm(text: str) -> str:
    text = text.lower().replace("’", "'")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9' ]+", " ", text)).strip()


def segments(text: str) -> list:
    parts = re.split(r"\b(Therapist|Child)\.\s*", text)
    return [(parts[i].lower(), parts[i + 1].strip()) for i in range(1, len(parts) - 1, 2)]


def sections(plan: str) -> dict:
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
    """Who said each sentence of `text` word for word: child, therapist, both, or '' if no one did."""
    speakers = set()
    for sentence in re.split(r"(?<=[.!?])\s+", text.strip()):
        s = norm(sentence)
        if not s:
            continue
        found = {spk for spk, words in segs if re.search(rf"(?<![a-z0-9']){re.escape(s)}(?![a-z0-9'])", norm(words))}
        if not found:
            return ""
        speakers |= found
    return "/".join(sorted(speakers))


with (TEST6 / "T21_T30_features.tsv").open(encoding="utf-8", newline="") as f:
    features = list(csv.DictReader(f, delimiter="\t", quoting=csv.QUOTE_NONE))

rows = ["transcript_id\tfeature\tplanted\treported\tresult\tevidence (plan, sections 1-4)\tnote"]
quote_rows = ["transcript_id\tquote\tauto_match\tsaid_by\tclosest_turn\tsimilarity"]
for plan_path in sorted((HERE / "plans").glob("T*.txt")):
    tid = plan_path.stem
    plan = plan_path.read_text(encoding="utf-8")
    sec = sections(plan)
    s3, s4 = sec.get(3, []), sec.get(4, [])
    mine = [r for r in features if r["transcript_id"] == tid]
    segs = segments((TEST6 / "transcripts" / f"{tid}.txt").read_text(encoding="utf-8"))
    no_feelings = "Did not name any feelings." in s3 + s4
    no_reasons = next((l for l in s3 if l.startswith("Did not give any reasons")), "")

    def add(feature, planted, reported, evidence="", note=""):
        result = ("hit" if reported == "Y" else "miss" if reported == "N" else "JUDGE") if planted == "Y" else \
                 ("false alarm" if reported == "Y" else "JUDGE")
        rows.append(f"{tid}\t{feature}\t{planted}\t{reported}\t{result}\t{evidence}\t{note}")

    for r in mine:
        if r["type"] == "left_out":
            part = r["part_or_feeling"]
            line = "Did not name any feelings." if part == "how they felt" else f"Did not say {WORDING[part]}."
            add(f"Leaves out: {part} ({r['how']})", "Y", "Y" if line in s3 + s4 else "N", line if line in s3 + s4 else "")
        elif r["type"] == "feeling":
            add(f"Feeling: {r['part_or_feeling']} ({r['how']})", "Y", "?", "", f"child: {r['words']}")
    if any(r["type"] == "reason" for r in mine):
        add("Gives a reason", "Y", "N" if no_reasons else "?", no_reasons)
    elif any(r["type"] == "no_reasons" for r in mine):
        add("Gives no reasons", "Y", "Y" if no_reasons else "N", no_reasons)
    for r in mine:
        if r["type"] == "given":
            line = f"Did not say {WORDING[r['part_or_feeling']]}."
            if line in s3:
                add(f"False alarm: {r['part_or_feeling']}", "N", "Y", line, f"child: {r['words']}")
    if no_feelings and any(r["type"] == "feeling" for r in mine):
        add("False alarm: missing feelings", "N", "Y", "Did not name any feelings.")
    if no_reasons and any(r["type"] == "reason" for r in mine):
        add("False alarm: missing reasons", "N", "Y", no_reasons)
    if "Did not say why they felt that way." in s4:
        add("False alarm?: why they felt", "N", "?", "Did not say why they felt that way.",
            "JUDGE against the reason rows below")

    # v2's lines have a fixed shape, and a quote can itself contain quotation
    # marks (T29: "Miss! Miss!"), so quotes are taken line by line.
    quotes = []
    for n in (1, 2, 3, 4, 5):
        for line in sec.get(n, []):
            named = re.match(r'Named "([^"]+)": "(.*)"$', line)
            if named:
                quotes += [named.group(1), named.group(2)]
            elif line.startswith(("Used sequencing words:", "Used vague words:")):
                quotes += re.findall(r'"([^"]+)"', line)
            elif line.startswith("Did not give any reasons"):
                continue  # names words the child did not say; not a quote
            elif line.endswith('"') and '"' in line[:-1]:
                quotes.append(line[line.index('"') + 1:-1])
    for quote in quotes:
        who = said_by(quote, segs)
        if who:
            quote_rows.append(f"{tid}\t{quote}\texact\t{who}\t\t1.00")
            continue
        best = max(segs, key=lambda sw: SequenceMatcher(None, norm(quote), norm(sw[1])).ratio())
        quote_rows.append(f"{tid}\t{quote}\tcheck\t{best[0]}\t{best[1]}"
                          f"\t{SequenceMatcher(None, norm(quote), norm(best[1])).ratio():.2f}")

    print(f"\n==================== {tid}")
    print("\n".join(l for l in plan.split("5. **Recommended")[0].splitlines() if l.strip()))
    print("--- planted (feelings, reasons, traps, yes-only):")
    for r in mine:
        if r["type"] in ("feeling", "reason", "no_reasons", "trap") or r["how"] == "yes-only":
            print(f"  {r['type']}: {r['part_or_feeling']} ({r['how']}): {r['words']}")

(HERE / "scoring_proposed.tsv").write_text("\n".join(rows) + "\n", encoding="utf-8")
(HERE / "quotes_auto.tsv").write_text("\n".join(quote_rows) + "\n", encoding="utf-8")
print("\nQuotes not found word for word, or only the therapist's:")
print("\n".join(q for q in quote_rows[1:] if "\tcheck\t" in q or "\texact\ttherapist\t" in q) or "  none")
