"""Un-blind run 4 and write the sheet's paste-ready blocks and summary.md.

Inputs: the LLM's Q1/Q2 coding (llm_coding_batches/*.tsv, merged into
blind_session_coding_llm.tsv), your and the LLM's reply ratings, the keys in
_unblinding/, and run 3's ratings, keys and guesses for the pooled 50.

Writes results/ (no header rows), and prints each:
    sessions_H11-H50.tsv   A28: session_id, condition, followed_lesson_focus, followed_profile_instructions, mean words
    blind_human.tsv        A113: blind_id, condition, responsive, clear, technique, no_invention (your ratings)
    blind_llm.tsv          H113: the same, LLM's ratings, same row order
    summary.md             new 40 and pooled 50 (H01-H50)

Q1/Q2 were coded by the LLM only (you chose not to code them yourself), so there
is no you-v-LLM agreement for them. Tests: one-sided Fisher's exact (with >
without) for Q1/Q2, the tie-safe exact Mann-Whitney from ../run2/finalise_run2.py
for words per reply, and the permutation test (20,000 shuffles, seed 4) for ratings.
coding_corrections.tsv overrides single coded values after the merge (the merged
file keeps the LLM's own coding), as in ../run3_human/finalise_run3.py.
"""

import csv
import json
import sys
from math import comb
from pathlib import Path
from statistics import mean, stdev

HERE = Path(__file__).resolve().parent
T4 = HERE.parent
sys.path[:0] = [str(T4), str(T4 / "run2"), str(T4 / "run3_human")]
from finalise import DIMENSIONS, fmt, permutation_p  # noqa: E402
from finalise_run2 import mann_whitney_exact, write  # noqa: E402
from finalise_run3 import apply_corrections, correction_line, qwk  # noqa: E402

UNBLIND, OUT = HERE / "_unblinding", HERE / "results"
RUN3 = T4 / "run3_human"
NEW = [f"H{i}" for i in range(11, 51)]
ALL = [f"H{i:02d}" for i in range(1, 11)] + NEW


def read(path: Path) -> list:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def llm_coding() -> dict:
    """Every S41-S90 row in the batch outputs, merged (and saved) as one file."""
    labels = [f"S{i}" for i in range(41, 91)]
    rows = {}
    for f in sorted((HERE / "llm_coding_batches").glob("*.tsv")):
        for line in f.read_text(encoding="utf-8-sig").replace("\r", "").splitlines():
            cells = [c.strip() for c in line.split("\t")]
            if cells[0] in labels:
                assert cells[0] not in rows, f"{cells[0]} coded twice"
                rows[cells[0]] = {"label": cells[0], "followed_lesson_focus": cells[1].upper(),
                                  "followed_profile_instructions": cells[2].upper(),
                                  "note": cells[3] if len(cells) > 3 else ""}
    assert sorted(rows) == labels, "the LLM coding does not cover S41-S90"
    assert all(r[k] in ("Y", "N") for r in rows.values()
               for k in ("followed_lesson_focus", "followed_profile_instructions"))
    write(HERE / "blind_session_coding_llm.tsv",
          [["label", "followed_lesson_focus", "followed_profile_instructions", "note"]] +
          [[r["label"], r["followed_lesson_focus"], r["followed_profile_instructions"], r["note"]]
           for r in (rows[l] for l in labels)])
    return rows


def ratings(folder: Path, n: int) -> dict:
    """{rater: {blind_id: {dim: score}}}, plus each reply's condition."""
    key = {r["blind_id"]: r["condition"] for r in read(folder / "_unblinding" / "key_replies.tsv")}
    out = {}
    for rater, name in (("you", "blind_replies_rated.tsv"), ("LLM", "blind_replies_rated_llm.tsv")):
        rows = {r["blind_id"].strip(): {d: int(r[d]) for d in DIMENSIONS} for r in read(folder / name)}
        assert set(rows) == set(key) and len(rows) == n, f"{folder.name}/{name} does not match its key"
        out[rater] = rows
    return {"scores": out, "condition": key}


def guesses(folder: Path) -> list:
    schedule = {s["label"]: s["condition"] for s in
                json.loads((folder / "_unblinding" / "schedule.json").read_text(encoding="utf-8"))["sessions"]}
    return [{**g, "truth": "with" if schedule[g["label"]].startswith("W") else "without"}
            for g in read(folder / "guesses.tsv")]


def fisher_one_sided(a: int, n1: int, c: int, n2: int) -> float:
    """P(with-count >= a) given the margins: one-sided Fisher's exact, with > without."""
    total, k = n1 + n2, a + c
    return sum(comb(n1, x) * comb(n2, k - x) for x in range(a, min(k, n1) + 1)) / comb(total, k)


def section(title: str, ids: list, sess: dict, reps: list) -> list:
    """with v without for one set of sessions and the replies rated from them."""
    by = {c: [sess[s] for s in ids if sess[s]["condition"] == c] for c in ("with", "without")}
    n = {c: len(by[c]) for c in by}
    lines = [f"## {title}", "", "| | with | without | difference | test |", "|---|---|---|---|---|"]
    for key, label in (("q1", "Q1 steered towards the lesson focus (LLM)"),
                       ("q2", "Q2 followed the profile's style instructions (LLM)")):
        a, c = (sum(s[key] == "Y" for s in by[x]) for x in ("with", "without"))
        lines.append(f"| {label} | {a}/{n['with']} | {c}/{n['without']} | {a - c:+d} | "
                     f"one-sided Fisher p = {fisher_one_sided(a, n['with'], c, n['without']):.3f} |")
    w, b = ([s["words"] for s in by[x]] for x in ("with", "without"))
    u, p = mann_whitney_exact(w, b)
    lines.append(f"| Mean words per reply | {fmt(mean(w))} | {fmt(mean(b))} | {mean(w) - mean(b):+.2f} | "
                 f"Mann-Whitney U = {u:g}, p = {p:.3f} (exact, two-sided) |")
    for rater in ("you", "LLM"):
        m = {c: [mean(r["scores"][rater].values()) for r in reps if r["condition"] == c] for c in ("with", "without")}
        lines.append(f"| Mean rating, {rater} ({len(m['with'])} v {len(m['without'])} replies) | "
                     f"{fmt(mean(m['with']))} (SD {fmt(stdev(m['with']))}) | {fmt(mean(m['without']))} "
                     f"(SD {fmt(stdev(m['without']))}) | {mean(m['with']) - mean(m['without']):+.2f} | "
                     f"permutation p = {permutation_p(m['with'], m['without']):.3f} (two-sided) |")
        for d in DIMENSIONS:
            dw = mean(r["scores"][rater][d] for r in reps if r["condition"] == "with")
            db = mean(r["scores"][rater][d] for r in reps if r["condition"] == "without")
            lines.append(f"| – {d} ({rater}) | {fmt(dw)} | {fmt(db)} | {dw - db:+.2f} | |")
    lines += ["", "Agreement, you v LLM, on the same replies:", "",
              "| dimension | exact | within 1 | weighted kappa |", "|---|---|---|---|"]
    for d in DIMENSIONS:
        a = [r["scores"]["you"][d] for r in reps]
        l = [r["scores"]["LLM"][d] for r in reps]
        lines.append(f"| {d} | {sum(x == y for x, y in zip(a, l))}/{len(a)} | "
                     f"{sum(abs(x - y) <= 1 for x, y in zip(a, l))}/{len(a)} | {qwk(a, l):.2f} |")
    return lines + [""]


def guess_lines(title: str, gs: list) -> list:
    made = [g for g in gs if g["guess"] != "unsure"]
    right = sum(g["guess"] == g["truth"] for g in made)
    p = sum(comb(len(made), i) for i in range(right, len(made) + 1)) / 2 ** len(made)
    return [f"- {title}: {right} of {len(made)} guesses right ({len(gs) - len(made)} unsure); chance of "
            f"{right} or more right by guessing: p = {p:.3f} (one-sided binomial, 0.5)."]


def main() -> None:
    OUT.mkdir(exist_ok=True)
    coding = llm_coding()
    corrections = apply_corrections(coding, HERE / "coding_corrections.tsv")
    key ={r["label"]: r for r in read(UNBLIND / "key_sessions.tsv")}
    stats = {r["session_id"]: r for r in read(UNBLIND / "session_stats.tsv")}
    sess = {}
    for label, k in key.items():
        st = stats[k["session_id"]]
        sess[k["session_id"]] = {"condition": k["condition"], "version": k["version"], "label": label,
                                 "q1": coding[label]["followed_lesson_focus"],
                                 "q2": coding[label]["followed_profile_instructions"],
                                 "words": float(st["mean_words_per_reply"]), "ended_by": st["ended_by"],
                                 "idk": st["idk_turn"]}
    assert sorted(sess) == sorted(ALL)

    r4, r3 = ratings(HERE, 40), ratings(RUN3, 40)
    def replies(r: dict) -> list:
        return [{"id": b, "condition": r["condition"][b], "scores": {x: r["scores"][x][b] for x in ("you", "LLM")}}
                for b in sorted(r["condition"], key=lambda b: int(b[1:]))]
    reps4, reps3 = replies(r4), replies(r3)

    blocks = {
        "sessions_H11-H50.tsv": [[s, sess[s]["condition"], sess[s]["q1"], sess[s]["q2"], fmt(sess[s]["words"])]
                                 for s in NEW],
        "blind_human.tsv": [[int(r["id"][1:]), r["condition"], *(r["scores"]["you"][d] for d in DIMENSIONS)]
                            for r in reps4],
        "blind_llm.tsv": [[int(r["id"][1:]), r["condition"], *(r["scores"]["LLM"][d] for d in DIMENSIONS)]
                          for r in reps4],
    }
    for name, rows in blocks.items():
        write(OUT / name, rows)

    g4, g3 = guesses(HERE), guesses(RUN3)
    attempts = read(HERE / "attempts.tsv")
    check = (HERE / "isolation_check.txt").read_text(encoding="utf-8").strip().splitlines()[-1]
    run3_check = (RUN3 / "isolation_check.txt").read_text(encoding="utf-8").strip().splitlines()[-1]
    ended4 = [s for s in NEW if sess[s]["ended_by"].startswith("player")]
    ended3 = [s for s in ALL[:10] if sess[s]["ended_by"].startswith("player")]
    lines = [
        "# Test 4, run 4 (you played April, 4 April contexts) – results", "",
        "Q1/Q2 were coded by the LLM (`llm_coding_prompt.md`) on all 50 transcripts, blind, against each",
        "session's lesson focus and style checklist (\"without\" sessions: a version assigned for coding, 5",
        "per version; H01–H10: v1). There is no coding by you, so no you-v-LLM agreement for Q1/Q2.",
        *([correction_line(corrections)] if corrections else []), "",
        *section("New 40 (H11–H50)", NEW, sess, reps4),
        *section("Pooled 50 (H01–H50)", ALL, sess, reps3 + reps4),
        "Ratings: run 4 sampled 1 reply per session (seed 10), run 3 sampled 4 per session (seed 8). Each run's",
        "replies were rated in their own batch.", "",
        "## Run 4 \"with\" sessions by April version", "",
        "| version | sessions | Q1 Y | Q2 Y | mean words |", "|---|---|---|---|---|",
        *[f"| {v} | {len(vs)} | {sum(sess[s]['q1'] == 'Y' for s in vs)} | {sum(sess[s]['q2'] == 'Y' for s in vs)} | "
          f"{fmt(mean(sess[s]['words'] for s in vs))} |"
          for v in ("v1", "v2", "v3", "v4") for vs in [[s for s in NEW if sess[s]["condition"] == "with"
                                                         and sess[s]["version"] == v]]],
        "",
        "## Your condition guesses (blinding check)", "",
        *guess_lines("New 40", g4), *guess_lines("Pooled 50", g3 + g4), "",
        "## Replays, early endings and the database", "",
        f"- Replayed: H14 and H15 (reset by you, played again under the same ID and condition). Abandoned "
        f"attempts in run 4: {sum(a['outcome'] == 'abandoned' for a in attempts)}. Run 3: H02, H04, H06 "
        "(each abandoned once and replayed).",
        f"- Ended with /end: {len(ended4)} of 40 in run 4 ({', '.join(ended4)}); {len(ended3)} of 10 in run 3 "
        f"({', '.join(ended3)}).",
        "- Database, before run 4 (approved): 4 extra event-title rows re-added after run 3 were removed "
        "(`removed_titles.json`), and v2–v4 were added (`setup_rows.json`). v1 and the blank April are as in "
        "runs 1–3.",
        f"- Database during run 4: {check} (`isolation_check.txt`). Run 3: {run3_check}",
        "",
        "## Sessions, un-blinded", "",
        "| session | condition | version | blind label | Q1 | Q2 | mean words | \"I don't know\" turn | ended by |",
        "|---|---|---|---|---|---|---|---|---|",
        *[f"| {s} | {sess[s]['condition']} | {sess[s]['version'] if sess[s]['condition'] == 'with' else '(' + sess[s]['version'] + ')'} | "
          f"{sess[s]['label']} | {sess[s]['q1']} | {sess[s]['q2']} | {fmt(sess[s]['words'])} | {sess[s]['idk']} | "
          f"{sess[s]['ended_by']} |" for s in ALL],
        "", "Versions in brackets are the version a \"without\" session was coded against; Reachy had no context.",
    ]
    (OUT / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    for name in blocks:
        print(f"== {name}")
        print((OUT / name).read_text(encoding="utf-8"), end="")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
