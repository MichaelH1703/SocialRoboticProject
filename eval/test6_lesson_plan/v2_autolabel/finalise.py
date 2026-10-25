"""Build the v2 run's paste-ready tables from scoring.tsv and quotes.tsv (same layout as v1).

Writes results/:
    top_table.tsv      transcript_id, feature, planted, reported, result (no header), T01-T20
    bottom_table.tsv   transcript_id, quote, result (no header), T01-T20
    results.tsv        hit rate, false alarms per transcript, quotes not in transcript, over T01-T20
    summary.md         the same for all 20, for T01-T10 (used in development) and T11-T20
                       (held out) separately, and v1 alongside on T01-T10
"""

import csv
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "results"
OUT.mkdir(exist_ok=True)
DEV = {f"T{i:02d}" for i in range(1, 11)}
CATEGORIES = ("Story parts left out", "Uses 'because' / 'so'", "Uses neither 'because' nor 'so'",
              "Emotion words (or none)")


def read(path: Path) -> list:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def category(feature: str) -> str:
    if feature.startswith("Leaves out"):
        return "Story parts left out"
    if "because" in feature or "'so'" in feature:
        return "Uses neither 'because' nor 'so'" if "neither" in feature else "Uses 'because' / 'so'"
    return "Emotion words (or none)"


def measures(rows: list, quotes: list) -> dict:
    planted = [r for r in rows if r["planted"] == "Y"]
    transcripts = len({r["transcript_id"] for r in rows})
    return {
        "hits": sum(r["result"] == "hit" for r in planted), "planted": len(planted),
        "false_alarms": sum(r["result"] == "false alarm" for r in rows), "transcripts": transcripts,
        "quotes": len(quotes), "not_there": sum(q["result"] == "not there" for q in quotes),
        "by_category": {c: (sum(r["result"] == "hit" for r in planted if category(r["feature"]) == c),
                            sum(category(r["feature"]) == c for r in planted)) for c in CATEGORIES},
    }


rows = [r for r in read(HERE / "scoring.tsv") if r["planted"] in ("Y", "N")]
quotes = read(HERE / "quotes.tsv")
everything = measures(rows, quotes)
dev = measures([r for r in rows if r["transcript_id"] in DEV], [q for q in quotes if q["transcript_id"] in DEV])
held = measures([r for r in rows if r["transcript_id"] not in DEV], [q for q in quotes if q["transcript_id"] not in DEV])
v1 = measures([r for r in read(HERE.parent / "scoring.tsv") if r["planted"] in ("Y", "N")],
              read(HERE.parent / "quotes.tsv"))

(OUT / "top_table.tsv").write_text(
    "\n".join("\t".join(r[c] for c in ("transcript_id", "feature", "planted", "reported", "result")) for r in rows) + "\n",
    encoding="utf-8")
(OUT / "bottom_table.tsv").write_text(
    "\n".join(f"{q['transcript_id']}\t{q['quote']}\t{q['result']}" for q in quotes) + "\n", encoding="utf-8")
(OUT / "results.tsv").write_text(
    f"{everything['hits'] / everything['planted']:.2f}\n"
    f"{everything['false_alarms'] / everything['transcripts']:.1f}\n{everything['not_there']}\n", encoding="utf-8")


def cell(m: dict, key: str) -> str:
    if key == "hit":
        return f"{m['hits'] / m['planted']:.2f} ({m['hits']}/{m['planted']})"
    if key == "fa":
        return f"{m['false_alarms'] / m['transcripts']:.1f} ({m['false_alarms']})"
    return f"{m['not_there']} of {m['quotes']}"


columns = [("v1, T01-T10", v1), ("v2, T01-T10 (development)", dev), ("v2, T11-T20 (held out)", held),
           ("v2, all 20", everything)]
lines = ["# Test 6 results: lesson planner v2, speaker labels removed and added automatically", "",
         "| Measure | " + " | ".join(name for name, _ in columns) + " |", "|---" * (len(columns) + 1) + "|"]
for label, key in (("Hit rate", "hit"), ("False alarms per transcript", "fa"), ("Quotes not in transcript", "q")):
    lines.append(f"| {label} | " + " | ".join(cell(m, key) for _, m in columns) + " |")
lines += ["", "| Planted feature type (hits / planted) | " + " | ".join(name for name, _ in columns) + " |",
          "|---" * (len(columns) + 1) + "|"]
for cat in CATEGORIES:
    lines.append(f"| {cat} | " + " | ".join("{}/{}".format(*m["by_category"][cat]) for _, m in columns) + " |")
label_file = HERE / "label_accuracy.txt"
if label_file.exists():
    lines += ["", "## Automatic speaker labels", ""] + [
        f"- {l}" for l in label_file.read_text(encoding="utf-8").splitlines() if l.startswith("OVERALL")]
(OUT / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
