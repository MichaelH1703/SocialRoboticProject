"""Score v2 and v3 on all 60 transcripts with the same automatic rules, so they can be compared.

Hand scoring 120 plans is not practical, so the Test 6 rules are applied in
code to each plan's analysis (the facts behind sections 2-4). Section 1, the
summary, is not scored. The hand scores sometimes credited a feeling the
summary mentioned, so these figures can be a little lower for feelings. To
check the automatic scorer, its v2 figures are printed next to the v2 hand
scores.

Truth: features.json (T01-T20, keyword rules), T21_T30_features.tsv and
T31_T60_features.tsv (meaning rules), and the labelled transcripts.

Rules
- Story part left out: reported if the part is not given. "How they felt" is
  reported if the plan says there were no feelings.
- T01-T20 emotion word X: found if X is one of the plan's feelings or in its
  quote. T21-T60 feeling: found if the plan has a feeling with the same word
  stem, or whose quote holds the planted words (and is no more than three
  times as long).
- Reasons (T21-T60): "gives a reason" is found if the plan quotes a reason
  that is really the child's and does not say there are none; "gives no
  reasons" is found if it says there are none. T01-T20 use the because/so
  rows, where "did not link them with because or so" also reports "neither".
- False alarms:
  - a part given but reported missing;
  - "no feelings" when there were some;
  - "no reasons" when there were some;
  - "did not say why they felt" when the child explained a feeling.
  For v3 there are also "did not name the feeling" when the child used a
  feeling word, and "did not link them" when the child used because/so.
  Whether a child explained a feeling is the literal rule for T01-T20 (the
  child used because/so). For T21-T60 it is the set EXPLAINED below, taken
  from the reason rows of the frozen truth sheets that explain a feeling.
- Wrong speaker:
  - the therapist's traps credited to the child (same word stem, or the
    trap's words quoted);
  - the share of quoted sentences that only the therapist said.
"""

import csv
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEST6 = HERE.parent
RUNS = {"v2": {**{f"T{i:02d}": TEST6 / "v2_autolabel" for i in range(1, 21)},
               **{f"T{i}": TEST6 / "v2_T21_T30" for i in range(21, 31)},
               **{f"T{i}": TEST6 / "v2_T31_T60" for i in range(31, 61)}},
        "v3": {f"T{i:02d}": HERE for i in range(1, 61)}}
SETS = {"T01-T10 (development)": range(1, 11), "T11-T20 (tidy)": range(11, 21),
        "T21-T30 (realistic)": range(21, 31), "T31-T60 (autistic teens)": range(31, 61)}
EXPLAINED = {"T21", "T23", "T24", "T27", "T29", "T31", "T33", "T34", "T35", "T36", "T37", "T39", "T40", "T41",
             "T42", "T44", "T46", "T47", "T49", "T50", "T51", "T53", "T55", "T56", "T58", "T59", "T60"}
PART_KEY = {"who": "who", "where": "where", "what happened": "what_happened", "how it ended": "ending"}
HAND = {"v2": {"T01-T10 (development)": (0.95, 0.3), "T11-T20 (tidy)": (0.97, 0.4),
               "T21-T30 (realistic)": (0.69, 0.5), "T31-T60 (autistic teens)": (0.54, 1.5)}}


def norm(text: str) -> str:
    text = text.lower().replace("’", "'")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9' ]+", " ", text)).strip()


def stem(word: str) -> str:
    return norm(word)[:5]


def truth_turns(tid: str) -> list:
    text = (TEST6 / "transcripts" / f"{tid}.txt").read_text(encoding="utf-8")
    parts = re.split(r"\b(Therapist|Child)\.\s*", text)
    return [(parts[i].lower(), parts[i + 1].strip()) for i in range(1, len(parts) - 1, 2)]


def childs(quote: str, turns: list) -> bool:
    """Whether at least one sentence of the quote is the child's (word for word)."""
    child = " | ".join(norm(w) for s, w in turns if s == "child")
    return any(norm(s) and norm(s) in child for s in re.split(r"(?<=[.!?])\s+", quote))


def therapist_only(quote: str, turns: list) -> int:
    """How many sentences of the quote only the therapist said."""
    child = " | ".join(norm(w) for s, w in turns if s == "child")
    ther = " | ".join(norm(w) for s, w in turns if s == "therapist")
    return sum(1 for s in re.split(r"(?<=[.!?])\s+", quote) if norm(s) and norm(s) not in child and norm(s) in ther)


def plan_facts(a: dict) -> dict:
    """The plan's claims, in the same shape for v2 and v3."""
    f, labelled = a["facts"], a["labelled"]
    feelings = [(x["word"], x["child_words"], x.get("named", True)) for x in f.get("feelings", [])]
    raw_reasons = f.get("reasons", [])
    reasons = [r if isinstance(r, str) else r["child_words"] for r in raw_reasons]
    # Only v3 says "did not link them with because or so" (its reasons are dicts with "linked").
    v3_unlinked = bool(raw_reasons) and isinstance(raw_reasons[0], dict) and not any(r["linked"] for r in raw_reasons)
    return {
        "labelled": labelled, "feelings": feelings, "reasons": reasons,
        "no_feelings": labelled and not feelings,
        "not_named": labelled and bool(feelings) and not any(n for _, _, n in feelings),
        "no_reasons": labelled and not reasons,
        "not_linked": labelled and v3_unlinked,
        "no_feeling_reason": labelled and bool(feelings) and not f.get("feeling_reasons"),
        "missing": {k for k, v in a["checked"].items() if k != "event" and not v["given"]},
        "quotes": [v["child_words"] for k, v in a["checked"].items() if k != "event" and v["given"]]
                  + [q for _, q, _ in feelings] + reasons,
    }


def feeling_found(planted_name: str, planted_words: str, feelings: list) -> bool:
    stems = {stem(w) for w in re.findall(r"[a-z]+", planted_name.lower()) if len(w) > 2}
    for word, quote, _ in feelings:
        if stem(word) in stems:
            return True
        for piece in re.split(r"…|\.\.\.", planted_words):
            p = norm(piece)
            if p and p in norm(quote) and len(norm(quote)) <= 3 * len(p):
                return True
    return False


def score_t01_t20(tid: str, p: dict, f: dict) -> list:
    rows = []
    for part in f["omits"]:
        reported = (p["no_feelings"] or p["not_named"]) if part == "how they felt" else PART_KEY[part] in p["missing"]
        rows.append(("Y", reported, f"left out: {part}"))
    uses = f["because"] or f["so"]
    if uses:
        rows.append(("Y", bool(p["reasons"]) and not p["no_reasons"], "uses because/so"))
    else:
        rows.append(("Y", p["no_reasons"] or p["not_linked"], "uses neither"))
    for word in f["emotions"]:
        rows.append(("Y", any(word in norm(w) or word in norm(q).split() for w, q, _ in p["feelings"]),
                     f"emotion: {word}"))
    if not f["emotions"]:
        rows.append(("Y", p["no_feelings"] or p["not_named"], "no emotion words"))
    for part, key in PART_KEY.items():
        if key in p["missing"] and part not in f["omits"]:
            rows.append(("N", True, f"false alarm: {part}"))
    if uses and (p["no_reasons"] or p["not_linked"]):
        rows.append(("N", True, "false alarm: missing reasons"))
    if f["emotions"] and (p["no_feelings"] or p["not_named"]):
        rows.append(("N", True, "false alarm: missing feelings"))
    if uses and p["no_feeling_reason"]:
        rows.append(("N", True, "false alarm: why they felt"))
    return rows


def score_t21_t60(tid: str, p: dict, sheet: list, turns: list) -> list:
    rows = []
    mine = [r for r in sheet if r["transcript_id"] == tid]
    for r in mine:
        if r["type"] == "left_out":
            part = r["part_or_feeling"]
            rows.append(("Y", p["no_feelings"] if part == "how they felt" else PART_KEY[part] in p["missing"],
                         f"left out: {part} ({r['how']})"))
        elif r["type"] == "feeling":
            rows.append(("Y", feeling_found(r["part_or_feeling"], r["words"], p["feelings"]),
                         f"feeling ({r['how']}): {r['part_or_feeling']}"))
    has_reasons = any(r["type"] == "reason" for r in mine)
    if has_reasons:
        rows.append(("Y", not p["no_reasons"] and any(childs(q, turns) for q in p["reasons"]), "gives a reason"))
    else:
        rows.append(("Y", p["no_reasons"], "gives no reasons"))
    given = {PART_KEY[r["part_or_feeling"]] for r in mine if r["type"] == "given"}
    for key in sorted(given & p["missing"]):
        rows.append(("N", True, f"false alarm: {key}"))
    has_feelings = any(r["type"] == "feeling" for r in mine)
    if has_feelings and p["no_feelings"]:
        rows.append(("N", True, "false alarm: missing feelings"))
    if any(r["type"] == "feeling" and r["how"] == "word" for r in mine) and p["not_named"]:
        rows.append(("N", True, "false alarm: feelings not named"))
    if has_reasons and p["no_reasons"]:
        rows.append(("N", True, "false alarm: missing reasons"))
    if any(r["type"] == "reason" and r["how"] == "because-so" for r in mine) and p["not_linked"]:
        rows.append(("N", True, "false alarm: reasons not linked"))
    if tid in EXPLAINED and p["no_feeling_reason"]:
        rows.append(("N", True, "false alarm: why they felt"))
    return rows


def traps_credited(tid: str, p: dict, sheet: list) -> tuple:
    traps = [r for r in sheet if r["transcript_id"] == tid and r["type"] == "trap"]
    hit = 0
    for t in traps:
        words = norm(t["words"])
        stems = {stem(w) for w in re.findall(r"[a-z]+", t["part_or_feeling"].lower()) if len(w) > 3}
        if any(stem(w) in stems for w, _, _ in p["feelings"]) or any(words and words in norm(q) for q in p["quotes"]):
            hit += 1
    return hit, len(traps)


def word_accuracy(a: dict, turns: list) -> tuple:
    auto = a.get("auto_labels")
    gold = [s for s, w in turns for _ in w.split()]
    if not auto:
        return 0, len(gold)
    segs = auto.get("segments") or auto.get("sentences")
    pred = [s for s, seg in segs for _ in seg.split()]
    return sum(x == y for x, y in zip(pred, gold)), len(gold)


def read_tsv(name: str) -> list:
    with (TEST6 / name).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t", quoting=csv.QUOTE_NONE))


features = json.loads((TEST6 / "features.json").read_text(encoding="utf-8"))
sheet = read_tsv("T21_T30_features.tsv") + read_tsv("T31_T60_features.tsv")
detail = ["version\ttranscript_id\tplanted\treported\tfeature"]
lines = ["# Test 6: v2 and v3 scored by the same automatic rules", "",
         "| Set | Version | Hit rate | False alarms / transcript | Traps credited | Quoted sentences only the "
         "therapist said | Words labelled right | v2 hand score (hit rate, false alarms) |",
         "|---|---|---|---|---|---|---|---|"]
for set_name, ids in SETS.items():
    for version, folders in RUNS.items():
        hits = planted = alarms = trap_hits = trap_n = ther = quoted = right = words = 0
        n = 0
        for i in ids:
            tid = f"T{i:02d}"
            path = folders[tid] / "analysis" / f"{tid}.json"
            if not path.exists():
                continue
            n += 1
            a = json.loads(path.read_text(encoding="utf-8"))
            p = plan_facts(a)
            turns = truth_turns(tid)
            rows = score_t01_t20(tid, p, features[tid]) if i <= 20 else score_t21_t60(tid, p, sheet, turns)
            detail += [f"{version}\t{tid}\t{pl}\t{'Y' if rep else 'N'}\t{name}" for pl, rep, name in rows]
            planted += sum(pl == "Y" for pl, _, _ in rows)
            hits += sum(pl == "Y" and rep for pl, rep, _ in rows)
            alarms += sum(pl == "N" for pl, _, _ in rows)
            if i > 20:
                h, t = traps_credited(tid, p, sheet)
                trap_hits, trap_n = trap_hits + h, trap_n + t
            for q in p["quotes"]:
                parts = [s for s in re.split(r"(?<=[.!?])\s+", q) if norm(s)]
                quoted += len(parts)
                ther += therapist_only(q, turns)
            r, w = word_accuracy(a, turns)
            right, words = right + r, words + w
        if not n:
            continue
        hand = HAND.get(version, {}).get(set_name)
        lines.append(f"| {set_name} | {version} | {hits / planted:.2f} ({hits}/{planted}) | {alarms / n:.1f} ({alarms}) | "
                     + (f"{trap_hits}/{trap_n}" if trap_n else "-") + f" | {ther}/{quoted} | {right / words:.1%} | "
                     + (f"{hand[0]:.2f}, {hand[1]:.1f}" if hand else "") + (f" | ({n} transcripts)" if n < len(ids) else " |"))
(HERE / "compare_detail.tsv").write_text("\n".join(detail) + "\n", encoding="utf-8")
(HERE / "compare.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
