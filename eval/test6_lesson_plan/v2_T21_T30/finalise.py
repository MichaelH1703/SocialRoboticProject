"""Build T21-T30's paste-ready tables and summary from scoring.tsv and quotes.tsv.

Writes results/:
    top_table.tsv      transcript_id, feature, planted, reported, result (no header)
    bottom_table.tsv   transcript_id, quote, result (no header)
    results.tsv        hit rate, false alarms per transcript, quotes not in transcript
    summary.md         the same, wrong-speaker credits, the breakdowns the spec asks
                       for, labelling accuracy, and v2's T11-T20 numbers for context
"""

import csv
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "results"
OUT.mkdir(exist_ok=True)


def read(path: Path) -> list:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t", quoting=csv.QUOTE_NONE))


rows = read(HERE / "scoring.tsv")
scored = [r for r in rows if r["planted"] in ("Y", "N")]
planted = [r for r in scored if r["planted"] == "Y"]
quotes = read(HERE / "quotes.tsv")
hits = sum(r["result"] == "hit" for r in planted)
false_alarms = [r for r in scored if r["result"] == "false alarm"]
wrong = [r for r in rows if r["result"] == "wrong speaker"]
transcripts = len({r["transcript_id"] for r in rows})
not_there = sum(q["result"] == "not there" for q in quotes)

(OUT / "top_table.tsv").write_text(
    "\n".join("\t".join(r[c] for c in ("transcript_id", "feature", "planted", "reported", "result")) for r in scored)
    + "\n", encoding="utf-8")
(OUT / "bottom_table.tsv").write_text(
    "\n".join(f"{q['transcript_id']}\t{q['quote']}\t{q['result']}" for q in quotes) + "\n", encoding="utf-8")
(OUT / "results.tsv").write_text(
    f"{hits / len(planted):.2f}\n{len(false_alarms) / transcripts:.1f}\n{not_there}\n", encoding="utf-8")


def group(test) -> str:
    g = [r for r in planted if test(r["feature"])]
    return f"{sum(r['result'] == 'hit' for r in g)}/{len(g)}"


lines = [
    "# Test 6, held-out set T21-T30: lesson planner v2, labels added automatically", "",
    f"- Hit rate: {hits}/{len(planted)} = {hits / len(planted):.2f}",
    f"- False alarms: {len(false_alarms)} over {transcripts} transcripts = {len(false_alarms) / transcripts:.1f} per "
    "transcript (" + ", ".join(f"{r['transcript_id']} {r['feature'][13:]}" for r in false_alarms) + ")",
    f"- Quotes: {len(quotes)} checked; " + ", ".join(
        f"{sum(q['result'] == k for q in quotes)} {k}" for k in ("exact", "reworded", "not there"))
    + f"; {sum(q['said_by'] != 'child' for q in quotes)} include the therapist's words",
    f"- Therapist's traps credited to the child: {len(wrong)} of "
    f"{sum(1 for _ in open(HERE.parent / 'T21_T30_features.tsv', encoding='utf-8') if chr(9) + 'trap' + chr(9) in _)} ("
    + ", ".join(f"{r['transcript_id']} {r['feature'][23:]}" for r in wrong) + ")",
    "", "| Planted feature (hits / planted) | |", "|---|---|",
    f"| Story parts left out | {group(lambda f: f.startswith('Leaves out'))} |",
    f"| …left out silently (never asked) | {group(lambda f: f.startswith('Leaves out') and '(silent)' in f)} |",
    f"| …asked about but not given | {group(lambda f: f.startswith('Leaves out') and '(asked)' in f)} |",
    f"| …only a yes to the therapist's guess | {group(lambda f: f.startswith('Leaves out') and '(yes-only)' in f)} |",
    f"| Feelings | {group(lambda f: f.startswith('Feeling'))} |",
    f"| …named with an emotion word | {group(lambda f: f.startswith('Feeling') and '(word)' in f)} |",
    f"| …shown any other way | {group(lambda f: f.startswith('Feeling') and '(phrase)' in f)} |",
    f"| Reasons (gives a reason / gives none) | {group(lambda f: f.startswith('Gives'))} |",
]
label_file = HERE / "label_accuracy.txt"
if label_file.exists():
    text = label_file.read_text(encoding="utf-8")
    lines += ["", "## Automatic speaker labels (word by word)", ""]
    lines += [f"- {l}" for l in text.splitlines() if l.startswith("OVERALL")]
    lines += [f"- {l}" for l in text.splitlines() if re.match(r"T\d+: (NOT|\d)", l)]
earlier = HERE.parent / "v2_autolabel" / "scoring.tsv"
if earlier.exists():
    e = [r for r in read(earlier) if r["planted"] in ("Y", "N") and int(r["transcript_id"][1:]) >= 11]
    ep = [r for r in e if r["planted"] == "Y"]
    lines += ["", "## For context: v2 on T11-T20 (scored by keyword, not meaning)", "",
              f"- Hit rate {sum(r['result'] == 'hit' for r in ep) / len(ep):.2f}; false alarms per transcript "
              f"{sum(r['result'] == 'false alarm' for r in e) / 10:.1f}"]
(OUT / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
