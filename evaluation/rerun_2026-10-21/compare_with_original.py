"""Compare the re-run with the original outputs still in eval/test6_lesson_plan/ (read only).

- v2: is each re-run plan / analysis byte-identical to the original v2 run's?
- v1, T01-T10: the original hand scores (scoring.tsv) against the re-run's,
  feature by feature (v1 sets no seed, so its text is expected to differ).
Writes compare_with_original.md.
"""

import csv
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEST6 = HERE.parent.parent / "eval" / "test6_lesson_plan"
OLD_V2 = {**{f"T{i:02d}": TEST6 / "v2_autolabel" for i in range(1, 21)},
          **{f"T{i}": TEST6 / "v2_T21_T30" for i in range(21, 31)},
          **{f"T{i}": TEST6 / "v2_T31_T60" for i in range(31, 61)}}

lines = ["# Re-run against the original outputs", ""]
same_plan, same_analysis, differ = 0, 0, []
for tid, folder in OLD_V2.items():
    new_plan, new_an = HERE / "v2" / f"{tid}_plan.md", HERE / "v2" / f"{tid}_analysis.json"
    if not new_plan.exists():
        differ.append(f"{tid} (no re-run plan)")
        continue
    p = new_plan.read_text(encoding="utf-8") == (folder / "plans" / f"{tid}.txt").read_text(encoding="utf-8")
    a = json.loads(new_an.read_text(encoding="utf-8")) == json.loads((folder / "analysis" / f"{tid}.json").read_text(encoding="utf-8"))
    same_plan += p
    same_analysis += a
    if not (p and a):
        differ.append(f"{tid} (plan {'same' if p else 'differs'}, analysis {'same' if a else 'differs'})")
lines += ["## v2", "", f"- Plans identical to the original v2 run: {same_plan}/60",
          f"- Analysis JSON identical: {same_analysis}/60", "- Differing: " + (", ".join(differ) or "none"), ""]


def read(path: Path) -> list:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t", quoting=csv.QUOTE_NONE))


old = {(r["transcript_id"], r["feature"]): r for r in read(TEST6 / "scoring.tsv") if r["planted"] in ("Y", "N")}
new = {(r["transcript_id"], r["feature"]): r for r in read(HERE / "v1_scoring.tsv")
       if r["result"] in ("hit", "miss", "false alarm") and int(r["transcript_id"][1:]) <= 10}
planted = [k for k, r in old.items() if r["planted"] == "Y"]
agree = sum(new.get(k, {}).get("result") == old[k]["result"] for k in planted)
lines += ["## v1, T01–T10 (original hand scores vs re-run)", "",
          f"- Planted features with the same result: {agree}/{len(planted)}",
          "- Planted features whose result changed:"]
for k in planted:
    if new.get(k, {}).get("result") != old[k]["result"]:
        lines.append(f"  - {k[0]} {k[1]}: original {old[k]['result']}, re-run {new.get(k, {}).get('result')}")
old_fa = sorted(k for k, r in old.items() if r["planted"] == "N")
new_fa = sorted(k for k, r in new.items() if r["planted"] == "N")
lines += [f"- False alarms: original {len(old_fa)} ({', '.join(f'{t} {f[13:]}' for t, f in old_fa)}); "
          f"re-run {len(new_fa)} ({', '.join(f'{t} {f[13:]}' for t, f in new_fa)})", ""]
(HERE / "compare_with_original.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
