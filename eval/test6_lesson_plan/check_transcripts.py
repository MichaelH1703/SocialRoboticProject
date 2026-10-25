"""Check each written transcript against its planted features in features.json.

Automatic: turn count (20-30), whether the CHILD says "because" / "so", the
CHILD's emotion words, and that the therapist's trap words appear only in her
lines. Story-part omissions cannot be checked by keyword and were checked by
reading. Prints PASS/FAIL per transcript; exits non-zero on any failure.
"""

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EMOTIONS = {
    "happy", "sad", "angry", "scared", "worried", "excited", "nervous", "proud", "annoyed", "cross",
    "upset", "frightened", "afraid", "glad", "bored", "silly", "embarrassed", "jealous", "lonely",
    "surprised", "calm", "frustrated", "frustrating", "thrilled", "cheerful", "grumpy", "shy", "relieved", "delighted",
}


def segments(text: str) -> list:
    """[(speaker, words)] from the spoken 'Therapist.' / 'Child.' labels."""
    parts = re.split(r"\b(Therapist|Child)\.\s*", text)
    return [(parts[i], parts[i + 1].strip()) for i in range(1, len(parts) - 1, 2)]


def words(text: str) -> set:
    return set(re.findall(r"[a-z']+", text.lower()))


def main() -> None:
    features = json.loads((HERE / "features.json").read_text(encoding="utf-8"))
    failed = False
    for path in sorted((HERE / "transcripts").glob("T*.txt")):
        tid = path.stem
        if tid not in features:  # T21-T30 have their own sheet and check (check_T21_T30.py)
            continue
        f = features[tid]
        segs = segments(path.read_text(encoding="utf-8"))
        child = set().union(*(words(w) for s, w in segs if s == "Child"))
        therapist = set().union(*(words(w) for s, w in segs if s == "Therapist"))
        problems = []
        if not 20 <= len(segs) <= 30:
            problems.append(f"{len(segs)} turns, not 20-30")
        for word in ("because", "so"):
            if (word in child) != f[word]:
                problems.append(f"child {'uses' if word in child else 'does not use'} '{word}', planted {f[word]}")
        if (child & EMOTIONS) != set(f["emotions"]):
            problems.append(f"child emotion words {sorted(child & EMOTIONS)}, planted {f['emotions']}")
        for trap in f.get("therapist_traps", []):
            if trap not in therapist:
                problems.append(f"trap '{trap}' not said by the therapist")
            if trap in child and trap not in {"because", "so"} | set(f["emotions"]):
                problems.append(f"trap '{trap}' also said by the child")
        failed |= bool(problems)
        print(f"{tid}: {'FAIL ' + '; '.join(problems) if problems else 'PASS'} ({len(segs)} turns)")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
