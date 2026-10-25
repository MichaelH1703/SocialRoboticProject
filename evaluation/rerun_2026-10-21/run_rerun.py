"""Run one lesson planner version on T01-T60, in order, one transcript at a time.

    python run_rerun.py v1   # lesson_planner.py (qwen2.5:3b), labelled transcripts, as run_generator.py did
    python run_rerun.py v2   # lesson_planner_v2.py (qwen3:8b), labels stripped and re-added, as run_v2.py did

The planners are imported unchanged. Outputs go to <version>/ in this folder:
T01_plan.md for every version, plus for v2 T01_analysis.json (every
intermediate result, including the auto labels) and unlabelled/T01.txt (what v2
was given). A failed attempt is retried once; a second failure is recorded as
FAILED (with the error) and the run moves on. A transcript that already has a
plan or a failure record is skipped, so nothing is ever overwritten.
"""

import datetime
import json
import platform
import re
import sys
import time
import traceback
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
TEST6 = ROOT / "eval" / "test6_lesson_plan"
sys.path.insert(0, str(ROOT))

version = sys.argv[1]
OUT = HERE / version
OUT.mkdir(exist_ok=True)
if version == "v1":
    from lesson_planner import generate_lesson_plan_from_transcript  # noqa: E402
    MODEL = "qwen2.5:3b"
else:
    from lesson_planner_v2 import DEFAULT_MODEL as MODEL, LABEL, analyse_transcript, render_plan  # noqa: E402
    (OUT / "unlabelled").mkdir(exist_ok=True)


def stamp() -> str:
    return datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")


def log(line: str) -> None:
    with (HERE / "run_log.md").open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(line, flush=True)


def ollama_ps() -> str:
    try:
        ps = json.load(urllib.request.urlopen("http://localhost:11434/api/ps", timeout=30))
        return "; ".join(f"{m['name']} {m['size_vram'] / m['size']:.0%} GPU" for m in ps.get("models", [])) or "none loaded"
    except Exception as e:  # noqa: BLE001
        return f"(failed: {e})"


def run_one(path: Path) -> str:
    tid = path.stem
    raw = path.read_text(encoding="utf-8")
    if version == "v1":
        plan = generate_lesson_plan_from_transcript(raw.strip())
        (OUT / f"{tid}_plan.md").write_text(plan + "\n", encoding="utf-8")
        return f"{len(plan.split())} words"
    text = re.sub(r"\s+", " ", LABEL.sub("", raw)).strip()
    (OUT / "unlabelled" / path.name).write_text(text + "\n", encoding="utf-8")
    old = next((d / "unlabelled" / path.name for d in (TEST6 / "v2_autolabel", TEST6 / "v2_T21_T30", TEST6 / "v2_T31_T60")
                if (d / "unlabelled" / path.name).exists()), None)
    same = "input identical to original v2 run" if old and old.read_text(encoding="utf-8") == text + "\n" else "INPUT DIFFERS from original v2 run"
    analysis = analyse_transcript(text)
    (OUT / f"{tid}_analysis.json").write_text(json.dumps(analysis, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT / f"{tid}_plan.md").write_text(render_plan(analysis) + "\n", encoding="utf-8")
    return f"speakers {analysis['speakers']}, {same}"


log(f"\n### {version} ({MODEL}), started {stamp()} on {platform.node()}")
log(f"- before first transcript, ollama ps: {ollama_ps()}")
for path in sorted((TEST6 / "transcripts").glob("T*.txt")):
    tid = path.stem
    if (OUT / f"{tid}_plan.md").exists() or (OUT / f"{tid}_FAILED.txt").exists():
        log(f"- {tid}: already done, skipped")
        continue
    errors = []
    for attempt in (1, 2):
        start, t0 = stamp(), time.perf_counter()
        try:
            info = run_one(path)
        except Exception:  # noqa: BLE001
            errors.append(traceback.format_exc())
            log(f"- {tid}: attempt {attempt} failed, start {start}, end {stamp()} ({time.perf_counter() - t0:.0f}s): "
                f"{errors[-1].strip().splitlines()[-1]}")
            continue
        status = "ok" if attempt == 1 else "ok (retry)"
        log(f"- {tid}: {status}, start {start}, end {stamp()} ({time.perf_counter() - t0:.0f}s), {info}")
        if tid in ("T01", "T30", "T60"):
            log(f"  - ollama ps: {ollama_ps()}")
        break
    else:
        (OUT / f"{tid}_FAILED.txt").write_text("\n\n".join(errors), encoding="utf-8")
        log(f"- {tid}: FAILED after 2 attempts (see {version}/{tid}_FAILED.txt)")
log(f"### {version} finished {stamp()}")
