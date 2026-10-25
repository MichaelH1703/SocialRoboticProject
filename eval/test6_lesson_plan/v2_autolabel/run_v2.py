"""Test 6 rerun: the same ten transcripts through lesson_planner_v2.py, speaker labels removed.

Real session transcripts have no "Therapist." / "Child." labels, so the labels
are stripped first and v2 adds its own. For each transcript this saves
unlabelled/<id>.txt (what v2 was given), analysis/<id>.json (every
intermediate result, including the auto labels) and plans/<id>.txt. A
transcript that already has a plan is skipped, so this can be stopped and
resumed without running any transcript twice.
"""

import json
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEST6 = HERE.parent
sys.path.insert(0, str(TEST6.parent.parent))
from lesson_planner_v2 import DEFAULT_MODEL, LABEL, analyse_transcript, render_plan  # noqa: E402

for folder in ("unlabelled", "analysis", "plans"):
    (HERE / folder).mkdir(exist_ok=True)

print(f"Model: {DEFAULT_MODEL}")
for path in sorted((TEST6 / "transcripts").glob("T*.txt")):
    if int(path.stem[1:]) > 20:  # T21-T30 are run in ../v2_T21_T30/
        continue
    out = HERE / "plans" / path.name
    if out.exists():
        print(f"{path.stem}: already has a plan, skipped")
        continue
    text = re.sub(r"\s+", " ", LABEL.sub("", path.read_text(encoding="utf-8"))).strip()
    (HERE / "unlabelled" / path.name).write_text(text + "\n", encoding="utf-8")
    t0 = time.perf_counter()
    analysis = analyse_transcript(text)
    (HERE / "analysis" / f"{path.stem}.json").write_text(
        json.dumps(analysis, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    out.write_text(render_plan(analysis) + "\n", encoding="utf-8")
    print(f"{path.stem}: plan saved ({time.perf_counter() - t0:.0f}s, speakers {analysis['speakers']})", flush=True)
