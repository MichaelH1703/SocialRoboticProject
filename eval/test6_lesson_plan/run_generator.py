"""Run each transcript through the lesson plan generator once (lesson_planner.py, unchanged).

Each plan is saved to plans/<id>.txt as soon as it is made, and a transcript
that already has a plan is skipped, so this can be stopped and resumed
without ever running a transcript twice.
"""

import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))
from lesson_planner import generate_lesson_plan_from_transcript  # noqa: E402

PLANS = HERE / "plans"
PLANS.mkdir(exist_ok=True)
for path in sorted((HERE / "transcripts").glob("T*.txt")):
    out = PLANS / path.name
    if out.exists():
        print(f"{path.stem}: already has a plan, skipped")
        continue
    t0 = time.perf_counter()
    plan = generate_lesson_plan_from_transcript(path.read_text(encoding="utf-8").strip())
    out.write_text(plan + "\n", encoding="utf-8")
    print(f"{path.stem}: plan saved ({time.perf_counter() - t0:.0f}s, {len(plan.split())} words)", flush=True)
