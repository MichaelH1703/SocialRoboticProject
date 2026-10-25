"""How accurate were v2's automatic speaker labels on T21-T30, word by word?

Rough transcripts do not break sentences where the speaker changes, so a
sentence can hold both speakers' words. Each word therefore gets the speaker
v2 gave its sentence, and is compared with its true speaker from the labelled
transcript. Reports the model's labels alone and after the echo rule, and
lists stretches of words given to the wrong speaker. Writes label_accuracy.txt.
"""

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEST6 = HERE.parent


def true_words(text: str) -> list:
    parts = re.split(r"\b(Therapist|Child)\.\s*", text)
    return [("therapist" if parts[i] == "Therapist" else "child", w)
            for i in range(1, len(parts) - 1, 2) for w in parts[i + 1].split()]


def tally(pred: list, gold: list) -> dict:
    return {"n": len(gold), "ok": sum(p == g for p, g in zip(pred, gold)),
            "child": sum(g == "child" for g in gold), "said_child": sum(p == "child" for p in pred),
            "both": sum(p == g == "child" for p, g in zip(pred, gold))}


def line(name: str, t: dict) -> str:
    return (f"{name}: {t['ok']}/{t['n']} words right ({t['ok'] / t['n']:.1%}); "
            f"child's words found {t['both']}/{t['child']} ({t['both'] / t['child']:.1%}); "
            f"labelled child and really were {t['both']}/{t['said_child']} ({t['both'] / max(1, t['said_child']):.1%})")


out, totals = [], {"model alone": [], "after echo rule": []}
for path in sorted((HERE / "analysis").glob("T*.json")):
    tid = path.stem
    auto = json.loads(path.read_text(encoding="utf-8"))["auto_labels"]
    gold = true_words((TEST6 / "transcripts" / f"{tid}.txt").read_text(encoding="utf-8"))
    if not auto:
        out.append(f"{tid}: NOT auto-labelled (labelling failed; the plan used the unlabelled fallback)")
        continue
    final, model, words = [], [], []
    for i, (speaker, sentence) in enumerate(auto["sentences"]):
        for w in sentence.split():
            final.append(speaker)
            model.append("child" if i in auto["echoes_relabelled"] else speaker)
            words.append(w)
    if words != [w for _, w in gold]:
        out.append(f"{tid}: words do not line up with the true transcript; not scored")
        continue
    g = [s for s, _ in gold]
    totals["model alone"].append((model, g))
    totals["after echo rule"].append((final, g))
    t = tally(final, g)
    out.append(f"{tid}: {t['ok']}/{t['n']} words right ({t['ok'] / t['n']:.1%}), "
               f"{len(auto['sentences'])} sentences")
    i = 0
    while i < len(g):  # stretches of consecutive wrong words, with their true speaker
        if final[i] != g[i]:
            j = i
            while j < len(g) and final[j] != g[j] and g[j] == g[i]:
                j += 1
            out.append(f"    {g[i]} said, labelled {final[i]}: {' '.join(words[i:j])}")
            i = j
        else:
            i += 1

out.append("")
for name, runs in totals.items():
    if runs:
        out.append(line(f"OVERALL, {name}", tally([p for pred, _ in runs for p in pred],
                                                  [x for _, gold in runs for x in gold])))
(HERE / "label_accuracy.txt").write_text("\n".join(out) + "\n", encoding="utf-8")
print("\n".join(out))
