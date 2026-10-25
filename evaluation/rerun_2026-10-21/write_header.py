"""Write the header of run_log.md: environment, models, and SHA-256 of every input.

Re-run of Test 6 (NFR3) for lesson planner v1 and v2. Nothing outside this
folder is written.
"""

import datetime
import hashlib
import json
import platform
import socket
import subprocess
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
TEST6 = ROOT / "eval" / "test6_lesson_plan"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(cmd: list) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=60).stdout.strip()
    except Exception as e:  # noqa: BLE001
        return f"(failed: {e})"


tags = json.load(urllib.request.urlopen("http://localhost:11434/api/tags", timeout=30))
version = json.load(urllib.request.urlopen("http://localhost:11434/api/version", timeout=30))
now = datetime.datetime.now().astimezone()
lines = [
    "# Test 6 (NFR3) re-run: lesson planner v1 and v2", "",
    f"- Started: {now:%Y-%m-%d %H:%M:%S %z}",
    f"- Host: {socket.gethostname()} ({platform.platform()})",
    f"- Python: {sys.version.split()[0]} ({sys.executable})",
    f"- Ollama: {version.get('version')}",
    "- GPU: " + run(["nvidia-smi", "--query-gpu=name,driver_version,memory.used,memory.total", "--format=csv,noheader"]),
    "", "## `ollama list`", "", "```", run(["ollama", "list"]), "```", "",
    "Full digests (`/api/tags`):", "",
]
lines += [f"- `{m['name']}`: `{m['digest']}`" for m in tags["models"]]
lines += ["", "## SHA-256 of planners, scorer and helpers", "", "```"]
for p in [ROOT / "lesson_planner.py", ROOT / "lesson_planner_v2.py", ROOT / "lesson_planner_v3.py",
          TEST6 / "v3" / "compare.py", TEST6 / "find_quotes.py", TEST6 / "run_generator.py",
          TEST6 / "v2_autolabel" / "run_v2.py"]:
    lines.append(f"{sha(p)}  {p.relative_to(ROOT).as_posix()}")
lines += ["```", "", "## SHA-256 of truth sheets", "", "```"]
for p in [TEST6 / "features.json", TEST6 / "T21_T30_spec.md", TEST6 / "T21_T30_features.tsv", TEST6 / "T31_T60_features.tsv"]:
    lines.append(f"{sha(p)}  {p.relative_to(ROOT).as_posix()}")
lines += ["```", "", "## SHA-256 of transcripts (labelled originals)", "", "```"]
for p in sorted((TEST6 / "transcripts").glob("T*.txt")):
    lines.append(f"{sha(p)}  {p.relative_to(ROOT).as_posix()}")
lines += ["```", "", "## Runs", "",
          "One line per attempt. Status `ok`, `retry` (first attempt failed) or `FAILED` (both attempts failed).", ""]
(HERE / "run_log.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
