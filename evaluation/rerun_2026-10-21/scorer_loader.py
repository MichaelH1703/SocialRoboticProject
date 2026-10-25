"""Load the scoring rules of eval/test6_lesson_plan/v3/compare.py without running its script part.

compare.py scores at import time and writes compare.md / compare_detail.tsv
into v3/. To reuse its rules unchanged without touching v3/, only its
imports, constants and function definitions are executed (the module-level
code from `features = ...` on is skipped). The file itself is not modified;
its SHA-256 is checked against the value recorded in run_log.md.
"""

import ast
import hashlib
from pathlib import Path

COMPARE = Path(__file__).resolve().parent.parent.parent / "eval" / "test6_lesson_plan" / "v3" / "compare.py"
COMPARE_SHA = hashlib.sha256(COMPARE.read_bytes()).hexdigest()


def load() -> dict:
    tree = ast.parse(COMPARE.read_text(encoding="utf-8"))
    keep = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "features" for t in node.targets):
            break  # start of the script part
        keep.append(node)
    ns = {"__file__": str(COMPARE), "__name__": "compare_rules"}
    exec(compile(ast.Module(body=keep, type_ignores=[]), str(COMPARE), "exec"), ns)
    return ns
