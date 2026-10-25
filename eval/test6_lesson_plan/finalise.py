"""Build Test 6's paste-ready tables and summary from scoring.tsv and quotes.tsv.

Writes results/:
    top_table.tsv      transcript_id, feature, planted, reported, result (no header)
    bottom_table.tsv   transcript_id, quote, result (no header)
    results.tsv        hit rate, false alarms per transcript, quotes not in transcript
    summary.md         the same, plus a breakdown by category
"""

import csv
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "results"
OUT.mkdir(exist_ok=True)


def read(name: str) -> list:
    with (HERE / name).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


rows = [r for r in read("scoring.tsv") if r["planted"] in ("Y", "N")]
quotes = read("quotes.tsv")
planted = [r for r in rows if r["planted"] == "Y"]
hits = sum(r["result"] == "hit" for r in planted)
false_alarms = sum(r["result"] == "false alarm" for r in rows)
transcripts = len({r["transcript_id"] for r in rows})
not_there = sum(q["result"] == "not there" for q in quotes)

(OUT / "top_table.tsv").write_text(
    "\n".join("\t".join(r[c] for c in ("transcript_id", "feature", "planted", "reported", "result")) for r in rows) + "\n",
    encoding="utf-8")
(OUT / "bottom_table.tsv").write_text(
    "\n".join(f"{q['transcript_id']}\t{q['quote']}\t{q['result']}" for q in quotes) + "\n", encoding="utf-8")
(OUT / "results.tsv").write_text(
    f"{hits / len(planted):.2f}\n{false_alarms / transcripts:.1f}\n{not_there}\n", encoding="utf-8")


def category(feature: str) -> str:
    if feature.startswith("Leaves out"):
        return "Story parts left out"
    if "because" in feature or "'so'" in feature:
        return "Uses neither 'because' nor 'so'" if "neither" in feature else "Uses 'because' / 'so'"
    return "Emotion words (or none)"


lines = ["# Test 6 results", "",
         f"- Hit rate: {hits}/{len(planted)} = {hits / len(planted):.2f}",
         f"- False alarms: {false_alarms} over {transcripts} transcripts = {false_alarms / transcripts:.1f} per transcript",
         f"- Quotes: {len(quotes)} checked; " + ", ".join(
             f"{sum(q['result'] == k for q in quotes)} {k}" for k in ("exact", "reworded", "not there")),
         "", "| Planted feature type | Hits | Planted |", "|---|---|---|"]
for cat in ("Story parts left out", "Uses 'because' / 'so'", "Uses neither 'because' nor 'so'", "Emotion words (or none)"):
    group = [r for r in planted if category(r["feature"]) == cat]
    lines.append(f"| {cat} | {sum(r['result'] == 'hit' for r in group)} | {len(group)} |")
(OUT / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
