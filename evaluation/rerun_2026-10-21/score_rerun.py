"""Score the v1 and v2 re-runs and write the tables the workbook is built from.

Features
- v2: the rules of eval/test6_lesson_plan/v3/compare.py, loaded unchanged
  (scorer_loader.py), applied to v2/T##_analysis.json. These are the rules
  that produced v3's figures in the NFR3 (V3) sheet.
- v1: v1 returns free text, which compare.py cannot read, so v1 is scored by
  reading against the same truth sheets and the fixed rules (README.md for
  T01-T20, T21_T30_spec.md for T21-T60). The judgements are in
  v1_scoring.tsv; rows marked "unsure" there go to needs_manual_check.md.

Quotes (both versions)
- Extracted from sections 1-5 of each plan with the rule that reproduces the
  500 rows of the existing NFR3 (V3) sheet: a bullet of the form
  `- Label: "..."` is one quote; otherwise every "..." on the line is a quote;
  the feeling labels in `Named "x":` / `Showed "x":` and the words
  `"because" or "so"` are not quotes. Section 6 (Reachy prompts) is excluded.
- exact: the quote appears word for word in one turn of the labelled
  transcript (ignoring case and punctuation), as in find_quotes.py; or every
  sentence of it does (a quote joined from several turns).
- Anything else is NOT decided automatically. It gets a provisional mark
  (reworded if its closest turn is at least 60% similar, else not there) and
  is listed in needs_manual_check.md with the closest turn.

Writes v1_features.tsv, v2_features.tsv, v1_quotes.tsv, v2_quotes.tsv,
by_set.tsv, needs_manual_check.md and scoring_summary.md.
"""

import csv
import json
import re
from difflib import SequenceMatcher
from pathlib import Path

import scorer_loader

HERE = Path(__file__).resolve().parent
c = scorer_loader.load()
TEST6 = c["TEST6"]
norm, truth_turns = c["norm"], c["truth_turns"]
features = json.loads((TEST6 / "features.json").read_text(encoding="utf-8"))
sheet = c["read_tsv"]("T21_T30_features.tsv") + c["read_tsv"]("T31_T60_features.tsv")
SETS = {"T01–T10": range(1, 11), "T11–T20": range(11, 21), "T21–T30": range(21, 31),
        "T31–T60": range(31, 61), "All 60": range(1, 61)}
IDS = [f"T{i:02d}" for i in range(1, 61)]


def sheet_name(name: str, tid: str) -> str:
    """compare.py's row name in the wording of the NFR3 sheet."""
    if name.startswith("left out: "):
        return "Leaves out: " + name[10:]
    m = re.match(r"feeling \((\w+)\): (.*)", name)
    if m:
        return f"Feeling: {m.group(2)} ({m.group(1)})"
    if name.startswith("emotion: "):
        return "Emotion word: " + name[9:]
    if name == "uses because/so":
        f = features[tid]
        return "Uses 'because' and 'so'" if f["because"] and f["so"] else "Uses 'because'" if f["because"] else "Uses 'so'"
    if name == "uses neither":
        return "Uses neither 'because' nor 'so'"
    if name == "no emotion words":
        return "Uses no emotion words"
    if name.startswith("false alarm: "):
        rest = {"ending": "how it ended", "what_happened": "what happened"}.get(name[13:], name[13:])
        return "False alarm: " + rest
    return name[0].upper() + name[1:]


def extract_quotes(plan: str) -> list:
    """[(quote, section number)] from sections 1-5."""
    plan = re.split(r"(?im)^.*suggested reachy prompts.*$", plan)[0]
    plan = re.sub(r'(Named|Showed) "[^"\n]+":', ":", plan)
    plan = plan.replace('"because" or "so"', "")
    out, section = [], 0
    for line in plan.splitlines():
        heading = re.match(r"^\W*(\d)\.", line)
        if heading and not line.lstrip().startswith("-"):
            section = int(heading.group(1))
        whole = re.match(r'^\s*- [^"]*: "(.*)"\s*$', line)
        if whole and '", "' not in whole.group(1):
            out.append((whole.group(1), section))
        else:
            out += [(q, section) for q in re.findall(r'["“]([^"”\n]{2,})["”]', line)]
    return out


def coverage(q: str, turn: str) -> float:
    """Share of the quote's words found, in order, in the turn."""
    qw, tw = q.split(), turn.split()
    blocks = SequenceMatcher(None, qw, tw, autojunk=False).get_matching_blocks()
    return sum(b.size for b in blocks) / max(len(qw), 1)


def classify(quote: str, section: int, turns: list) -> dict:
    q = norm(quote)
    hit = [s for s, w in turns if q and q in norm(w)]
    if hit:
        return {"found": "exact", "how": "one turn", "speaker": "/".join(sorted(set(hit))), "closest": "", "sim": ""}
    pieces = [norm(s) for s in re.split(r"(?<=[.!?])\s+", quote) if norm(s)]
    where = [[s for s, w in turns if p in norm(w)] for p in pieces]
    if pieces and all(where):
        return {"found": "exact", "how": f"joined from {len(pieces)} sentences",
                "speaker": "/".join(sorted({s for w in where for s in w})), "closest": "", "sim": ""}
    best = max(turns, key=lambda t: coverage(q, norm(t[1])))
    cov = coverage(q, norm(best[1]))
    if section == 5 or quote.rstrip().endswith("?"):
        found = "excluded"  # a proposed question or a section-5 suggestion, not offered as the child's words
    else:
        found = "reworded" if cov >= 0.6 else "not there"
    return {"found": found, "how": "PROVISIONAL", "speaker": best[0], "closest": best[1], "sim": f"{cov:.2f}"}


def write_tsv(name: str, header: list, rows: list) -> None:
    with (HERE / name).open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)


# ── Features ─────────────────────────────────────────────────────────────────
failed = {v: {t for t in IDS if (HERE / v / f"{t}_FAILED.txt").exists()} for v in ("v1", "v2")}
feat = {"v1": [], "v2": []}
extra = {"v2_traps": {}, "v2_ther_only": {}}
for i, tid in enumerate(IDS, 1):
    path = HERE / "v2" / f"{tid}_analysis.json"
    if not path.exists():
        continue
    a = json.loads(path.read_text(encoding="utf-8"))
    p, turns = c["plan_facts"](a), truth_turns(tid)
    rows = c["score_t01_t20"](tid, p, features[tid]) if i <= 20 else c["score_t21_t60"](tid, p, sheet, turns)
    for planted, reported, name in rows:
        result = "false alarm" if planted == "N" else "hit" if reported else "miss"
        feat["v2"].append([tid, sheet_name(name, tid), planted, "Y" if reported else "N", result, name, ""])
    if i > 20:
        extra["v2_traps"][tid] = c["traps_credited"](tid, p, sheet)
    extra["v2_ther_only"][tid] = sum(c["therapist_only"](q, turns) for q in p["quotes"])

unsure_v1, v1_raw = [], []
v1_path = HERE / "v1_scoring.tsv"
if v1_path.exists():
    with v1_path.open(encoding="utf-8", newline="") as f:
        v1_raw = list(csv.DictReader(f, delimiter="\t", quoting=csv.QUOTE_NONE))
        for r in v1_raw:
            feat["v1"].append([r["transcript_id"], r["feature"], r["planted"], r["reported"], r["result"],
                               r["evidence"], r["note"]])
            if r["confidence"] == "unsure":
                unsure_v1.append(r)

header = ["transcript_id", "feature", "planted", "reported", "result", "scorer_row_or_evidence", "note"]
for v in ("v1", "v2"):
    write_tsv(f"{v}_features.tsv", header, feat[v])

# ── Quotes ───────────────────────────────────────────────────────────────────
quotes, all_quotes = {"v1": [], "v2": []}, {}
for v in ("v1", "v2"):
    for tid in IDS:
        path = HERE / v / f"{tid}_plan.md"
        if not path.exists():
            continue
        turns = truth_turns(tid)
        for q, section in extract_quotes(path.read_text(encoding="utf-8")):
            r = classify(q, section, turns)
            quotes[v].append([tid, q, r["found"], r["how"], r["speaker"], r["closest"], r["sim"], section])
    write_tsv(f"{v}_quotes.tsv", ["transcript_id", "quote", "found", "how", "speaker", "closest_turn", "coverage",
                                  "section"], quotes[v])
    all_quotes[v] = quotes[v]
    quotes[v] = [r for r in quotes[v] if r[2] != "excluded"]  # kept in the TSV and the manual list only

# ── By set ───────────────────────────────────────────────────────────────────
by_set = []
for v in ("v1", "v2"):
    for name, rng in SETS.items():
        ids = {f"T{i:02d}" for i in rng}
        f = [r for r in feat[v] if r[0] in ids]
        q = [r for r in quotes[v] if r[0] in ids]
        hits = sum(r[4] == "hit" for r in f)
        planted = sum(r[2] == "Y" for r in f)
        fa = sum(r[4] == "false alarm" for r in f)
        n = len(ids - failed[v])
        traps = [extra["v2_traps"][t] for t in ids if t in extra["v2_traps"]] if v == "v2" else []
        if v == "v1":  # by reading: every therapist trap (or yes-only part) noted in v1_scoring.tsv's last column
            credited = [x for r in v1_raw if r["transcript_id"] in ids
                        for x in (r.get("traps_credited") or "").split(";") if x.strip()]
            traps = [(len(credited), 0)]
        phrase = [r for r in f if r[1].startswith("Feeling:") and r[1].endswith("(phrase)")]
        by_set.append([v, name, hits, planted, f"{hits / planted:.2f}" if planted else "", fa,
                       f"{fa / n:.1f}" if n else "", len(q), sum(r[2] == "not there" for r in q),
                       sum(r[3] == "PROVISIONAL" for r in q), sum(r[4] == "therapist" for r in q),
                       (f"{traps[0][0]} credited (by reading)" if v == "v1" else
                        f"{sum(h for h, _ in traps)}/{sum(t for _, t in traps)}") if traps else "",
                       f"{sum(r[4] == 'hit' for r in phrase)}/{len(phrase)}" if phrase else "", n])
write_tsv("by_set.tsv", ["version", "set", "hits", "planted", "hit_rate", "false_alarms", "fa_per_transcript",
                         "quotes_checked", "quotes_not_there", "quotes_provisional", "quotes_therapist_only",
                         "traps_credited", "feelings_without_word_found", "transcripts_scored"], by_set)

# ── Manual checks ────────────────────────────────────────────────────────────
lines = ["# Needs manual check", "",
         "Nothing below was decided silently. Each case has a provisional value in the workbook (marked with a",
         "cell comment); confirm or change it by hand.", ""]
n = 0
for v in ("v1", "v2"):
    prov = [r for r in all_quotes[v] if r[3] == "PROVISIONAL"]
    lines += [f"## {v}: quotes not found word for word ({len(prov)})", "",
              "Decide `reworded` (same meaning), `not there` (not said, or meaning changed), or `excluded` (not",
              "offered as the child's words: a proposed question, an example of what they could say).",
              "Provisional marks: `excluded` for questions and section-5 suggestions; otherwise `reworded` if at",
              "least 60% of the quote's words appear in order in the closest turn, else `not there`.", ""]
    for r in prov:
        n += 1
        lines += [f"{n}. **{r[0]}** (section {r[7]}) — provisional `{r[2]}` (coverage {r[6]} of a {r[4]} turn)",
                  f"   - Plan quotes: \"{r[1]}\"", f"   - Closest turn ({r[4]}): \"{r[5]}\"", ""]
lines += [f"## v1: feature judgements marked unsure ({len(unsure_v1)})", ""]
for r in unsure_v1:
    n += 1
    lines += [f"{n}. **{r['transcript_id']}** — {r['feature']}: reported {r['reported']} → {r['result']}",
              f"   - Plan: {r['evidence']}", f"   - Why unsure: {r['note']}", ""]
(HERE / "needs_manual_check.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

summary = ["# Scoring summary (automatic part; provisional quote marks included)", "",
           f"compare.py SHA-256: `{scorer_loader.COMPARE_SHA}`", "",
           "| Version | Set | Hit rate | False alarms / transcript | Quotes not there / checked | Provisional quotes | "
           "Quotes said only by therapist | Traps credited | Feelings without a feeling word found |",
           "|---|---|---|---|---|---|---|---|---|"]
for r in by_set:
    summary.append(f"| {r[0]} | {r[1]} | {r[4]} ({r[2]}/{r[3]}) | {r[6]} ({r[5]}) | {r[8]}/{r[7]} | {r[9]} | {r[10]} | "
                   f"{r[11]} | {r[12]} |")
summary += ["", f"Failed runs: v1 {sorted(failed['v1']) or 'none'}, v2 {sorted(failed['v2']) or 'none'}.",
            f"Quotes and v1 judgements needing a manual check: {n}.",
            "v2 quoted sentences only the therapist said (compare.py rule), by set: "
            + ", ".join(f"{k} {sum(extra['v2_ther_only'].get(f'T{i:02d}', 0) for i in rng)}" for k, rng in SETS.items())]
(HERE / "scoring_summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
print("\n".join(summary))
