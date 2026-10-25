"""Apply the manual-check decisions (manual_review.tsv) to the re-run's score tables.

Nothing is overwritten: the provisional tables stay as they are, and the
reviewed ones are written next to them with a _reviewed suffix
(v1_scoring_reviewed.tsv, v1/v2_features_reviewed.tsv,
v1/v2_quotes_reviewed.tsv, by_set_reviewed.tsv, scoring_summary_reviewed.md).
Every decision must match an item, and every provisional item must have a
decision; otherwise this stops with an error.

Rules agreed in the review (applied through the decisions, not in code):
1. A plan that contradicts itself credits a feature if any section clearly
   credits it; the contradiction is recorded (column "contradiction").
2. A credited reason must be the child's own; a wrong or invented reason is a miss.
"""

import csv
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
SETS = {"T01–T10": range(1, 11), "T11–T20": range(11, 21), "T21–T30": range(21, 31),
        "T31–T60": range(31, 61), "All 60": range(1, 61)}


def read(name: str) -> list:
    # The hand-typed tables (v1_scoring.tsv, manual_review.tsv) are plain tab-separated text; the generated ones
    # were written by csv with standard quoting, so a field holding '"' is wrapped in quotes.
    literal = name in ("v1_scoring.tsv", "manual_review.tsv")
    with (HERE / name).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t", **({"quoting": csv.QUOTE_NONE} if literal else {})))


def write(name: str, rows: list, fields: list) -> None:
    with (HERE / name).open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, delimiter="\t", lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


decisions = read("manual_review.tsv")

# ── v1 features ──────────────────────────────────────────────────────────────
v1 = read("v1_scoring.tsv")
for r in v1:
    r["traps_credited"] = r.get("traps_credited") or ""
    r["reviewed"], r["contradiction"] = "", ""
for d in (d for d in decisions if d["kind"] == "feature"):
    hits = [r for r in v1 if r["transcript_id"] == d["transcript_id"] and r["feature"] == d["item"]]
    assert len(hits) == 1, f"feature decision matches {len(hits)} rows: {d}"
    r = hits[0]
    assert r["result"] == d["provisional"], f"provisional mark differs: {d} vs {r['result']}"
    if d["final"] == "not counted" and r["result"] == "false alarm":
        r["feature"] = "(not counted) " + r["feature"].split(": ", 1)[1]
        r["planted"], r["reported"] = "N", "N"
    elif r["result"] == "not counted" and d["final"] == "false alarm":
        r["feature"] = "False alarm: " + r["feature"].replace("(not counted) ", "")
        r["planted"], r["reported"] = "N", "Y"
    elif d["final"] in ("hit", "miss"):
        r["reported"] = "Y" if d["final"] == "hit" else "N"
    r["result"] = d["final"]
    r["reviewed"] = d["reason"]
    if "contradiction recorded" in d["reason"]:
        r["contradiction"] = d["reason"].split("contradiction recorded", 1)[1].strip(" ()")
left = [r for r in v1 if r["confidence"] == "unsure" and not r["reviewed"]]
assert not left, f"unsure v1 rows without a decision: {[(r['transcript_id'], r['feature']) for r in left]}"
fields = list(v1[0].keys())
write("v1_scoring_reviewed.tsv", v1, fields)
feats = {"v1": [{"transcript_id": r["transcript_id"], "feature": r["feature"], "planted": r["planted"],
                 "reported": r["reported"], "result": r["result"], "scorer_row_or_evidence": r["evidence"],
                 "note": r["note"]} for r in v1],
         "v2": read("v2_features.tsv")}
for v in ("v1", "v2"):
    write(f"{v}_features_reviewed.tsv", feats[v], list(feats["v2"][0].keys()))

# ── Quotes ───────────────────────────────────────────────────────────────────
quotes = {}
for v in ("v1", "v2"):
    rows = read(f"{v}_quotes.tsv")
    for r in rows:
        r["reviewed"] = ""
    for d in (d for d in decisions if d["kind"] == "quote" and d["version"] == v):
        hits = [r for r in rows if r["transcript_id"] == d["transcript_id"] and r["how"] == "PROVISIONAL"
                and r["quote"].startswith(d["item"])]
        assert hits, f"quote decision matches nothing: {d}"
        for r in hits:
            assert r["found"] == d["provisional"], f"provisional mark differs: {d} vs {r['found']}"
            r["found"], r["how"], r["reviewed"] = d["final"], "checked by hand", d["reason"]
    left = [r for r in rows if r["how"] == "PROVISIONAL"]
    assert not left, f"{v}: provisional quotes without a decision: {[(r['transcript_id'], r['quote'][:40]) for r in left]}"
    write(f"{v}_quotes_reviewed.tsv", rows, list(rows[0].keys()))
    quotes[v] = [r for r in rows if r["found"] != "excluded"]

# ── By set ───────────────────────────────────────────────────────────────────
old = {(r["version"], r["set"]): r for r in read("by_set.tsv")}
out = []
for v in ("v1", "v2"):
    for name, rng in SETS.items():
        ids = {f"T{i:02d}" for i in rng}
        f = [r for r in feats[v] if r["transcript_id"] in ids]
        q = [r for r in quotes[v] if r["transcript_id"] in ids]
        hits, planted = sum(r["result"] == "hit" for r in f), sum(r["planted"] == "Y" for r in f)
        fa = sum(r["result"] == "false alarm" for r in f)
        phrase = [r for r in f if r["feature"].startswith("Feeling:") and r["feature"].endswith("(phrase)")]
        out.append({"version": v, "set": name, "hits": hits, "planted": planted, "hit_rate": f"{hits / planted:.2f}",
                    "false_alarms": fa, "fa_per_transcript": f"{fa / len(ids):.1f}",
                    "precision": f"{hits / (hits + fa):.3f}", "quotes_checked": len(q),
                    "quotes_not_there": sum(r["found"] == "not there" for r in q),
                    "quotes_reworded": sum(r["found"] == "reworded" for r in q),
                    "traps_credited": old[(v, name)]["traps_credited"],
                    "feelings_without_word_found": f"{sum(r['result'] == 'hit' for r in phrase)}/{len(phrase)}" if phrase else "",
                    "provisional_hit_rate": old[(v, name)]["hit_rate"],
                    "provisional_fa_per_transcript": old[(v, name)]["fa_per_transcript"],
                    "provisional_quotes_not_there": f"{old[(v, name)]['quotes_not_there']}/{old[(v, name)]['quotes_checked']}"})
write("by_set_reviewed.tsv", out, list(out[0].keys()))

lines = ["# Scoring summary after the manual check", "",
         "Decisions: `manual_review.tsv`. Provisional figures (before the check) in brackets.", "",
         "| Version | Set | Hit rate | False alarms / transcript | Precision | Quotes not there / checked | "
         "Feelings without a feeling word found |", "|---|---|---|---|---|---|---|"]
for r in out:
    lines.append(f"| {r['version']} | {r['set']} | {r['hit_rate']} ({r['hits']}/{r['planted']}) [{r['provisional_hit_rate']}] | "
                 f"{r['fa_per_transcript']} ({r['false_alarms']}) [{r['provisional_fa_per_transcript']}] | "
                 f"{float(r['precision']):.1%} | {r['quotes_not_there']}/{r['quotes_checked']} "
                 f"[{r['provisional_quotes_not_there']}] | {r['feelings_without_word_found']} |")
contra = [r for r in v1 if r["contradiction"]]
lines += ["", "Self-contradicting v1 plans (rule 1): " + "; ".join(f"{r['transcript_id']} {r['feature']}: {r['contradiction']}" for r in contra)]
(HERE / "scoring_summary_reviewed.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
