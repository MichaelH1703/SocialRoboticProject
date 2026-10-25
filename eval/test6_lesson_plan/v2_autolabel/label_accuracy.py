"""How accurate were v2's automatic speaker labels in the Test 6 rerun?

Compares each sentence's auto label (analysis/<id>.json) with its true label
from the original labelled transcript, for the model's labels alone and after
the echo rule. Lists every wrong sentence. Writes label_accuracy.txt.
"""

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEST6 = HERE.parent


def truth(text: str) -> list:
    """[(speaker, sentence)] from the spoken labels."""
    parts = re.split(r"\b(Therapist|Child)\.\s*", text)
    out = []
    for i in range(1, len(parts) - 1, 2):
        for s in re.split(r"(?<=[.!?])\s+", parts[i + 1].strip()):
            if s:
                out.append(("therapist" if parts[i] == "Therapist" else "child", s))
    return out


def tally(pred: list, gold: list) -> dict:
    return {"n": len(gold), "ok": sum(p == g for p, g in zip(pred, gold)),
            "child": sum(g == "child" for g in gold), "said_child": sum(p == "child" for p in pred),
            "both": sum(p == g == "child" for p, g in zip(pred, gold))}


def line(name: str, t: dict) -> str:
    return (f"{name}: {t['ok']}/{t['n']} sentences right ({t['ok'] / t['n']:.1%}); "
            f"child's sentences found {t['both']}/{t['child']} ({t['both'] / t['child']:.1%}); "
            f"labelled child and really were {t['both']}/{t['said_child']} ({t['both'] / max(1, t['said_child']):.1%})")


out = []
totals = {"model alone": [], "after echo rule": [], "after echo rule, T01-T10": [],
          "after echo rule, T11-T20 (held out)": []}
for path in sorted((HERE / "analysis").glob("T*.json")):
    tid = path.stem
    auto = json.loads(path.read_text(encoding="utf-8"))["auto_labels"]
    gold = truth((TEST6 / "transcripts" / f"{tid}.txt").read_text(encoding="utf-8"))
    if not auto:
        out.append(f"{tid}: NOT auto-labelled (labelling failed; plan used the unlabelled fallback)")
        continue
    if [s for _, s in auto["sentences"]] != [s for _, s in gold]:
        out.append(f"{tid}: sentences do not line up with the true transcript; not scored")
        continue
    final = [speaker for speaker, _ in auto["sentences"]]
    model = ["child" if i in auto["echoes_relabelled"] else p for i, p in enumerate(final)]
    g = [speaker for speaker, _ in gold]
    totals["model alone"].append((model, g))
    totals["after echo rule"].append((final, g))
    totals["after echo rule, T01-T10" if int(tid[1:]) <= 10 else "after echo rule, T11-T20 (held out)"].append((final, g))
    t = tally(final, g)
    out.append(f"{tid}: {t['ok']}/{t['n']} right; echo rule relabelled {len(auto['echoes_relabelled'])} "
               f"({sum(g[i] == 'therapist' for i in auto['echoes_relabelled'])} correctly)")
    for (speaker, sentence), p in zip(gold, final):
        if p != speaker:
            out.append(f"    {'therapist said, labelled child' if speaker == 'therapist' else 'child said, labelled therapist'}: {sentence}")

out.append("")
for name, runs in totals.items():
    if runs:
        out.append(line(f"OVERALL, {name}", tally([p for pred, _ in runs for p in pred],
                                                  [x for _, gold in runs for x in gold])))
(HERE / "label_accuracy.txt").write_text("\n".join(out) + "\n", encoding="utf-8")
print("\n".join(out))
