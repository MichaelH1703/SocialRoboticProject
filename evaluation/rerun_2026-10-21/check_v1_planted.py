"""Check that v1_scoring.tsv has exactly the planted rows the scorer expects, transcript by transcript.

The planted (Y) rows do not depend on the plan, so compare.py's rules are run
on any analysis (here the original v2 run, read only) to list them, in the
sheet's wording. Prints every difference; prints nothing else if they agree.
"""

import csv
import json
from collections import Counter

import scorer_loader
from score_rerun import sheet_name  # noqa: F401  (also writes the score tables; harmless)

c = scorer_loader.load()
T6 = c["TEST6"]
features = json.loads((T6 / "features.json").read_text(encoding="utf-8"))
sheet = c["read_tsv"]("T21_T30_features.tsv") + c["read_tsv"]("T31_T60_features.tsv")
with open("v1_scoring.tsv", encoding="utf-8", newline="") as f:
    v1 = list(csv.DictReader(f, delimiter="\t", quoting=csv.QUOTE_NONE))
problems = 0
for i in range(1, 61):
    tid = f"T{i:02d}"
    a = json.loads((c["RUNS"]["v2"][tid] / "analysis" / f"{tid}.json").read_text(encoding="utf-8"))
    p = c["plan_facts"](a)
    rows = c["score_t01_t20"](tid, p, features[tid]) if i <= 20 else c["score_t21_t60"](tid, p, sheet, c["truth_turns"](tid))
    want = Counter(sheet_name(n, tid) for pl, _, n in rows if pl == "Y")
    # A transcript with feelings planted but none of them "how they felt" left out still has its rows in want.
    got = Counter(r["feature"] for r in v1 if r["transcript_id"] == tid and r["planted"] == "Y")
    if want != got:
        problems += 1
        print(tid, "missing:", dict(want - got), "extra:", dict(got - want))
print("transcripts with differences:", problems)
