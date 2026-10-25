"""Un-blind run 3 (you played April) and produce the paste-ready tables.

Run only once both raters' ratings are final, and the session coding if it is
being used (blind_session_coding.tsv; if it is empty the Y/N columns are left
blank and Fisher's test is skipped).

Writes results/ (no header rows, as runs 1 and 2):
    top_table.tsv             H01-H10 in order: session_id, condition, focus, profile, words
    bottom_table.tsv          blind_id (121-160), condition, your 4 scores
    bottom_table_llm.tsv      the same with the LLM's scores
    results_table.tsv         with / without / difference rows, your ratings (runs 1-2's 4 columns)
    results_table_llm.tsv     the same with the LLM's ratings
    summary.md                stats and tests, you-v-LLM agreement, condition guesses, checks

coding_corrections.tsv, if present, overrides single coded values (label, column,
coded, corrected); each is checked against the coding file and listed in summary.md.

Tests are runs 1-2's (../run2/finalise_run2.py). Agreement between the two
raters is per dimension: exact agreement, agreement within 1 point, and
quadratic-weighted Cohen's kappa.
"""

import csv
import json
import re
import sys
from math import comb
from pathlib import Path
from statistics import mean, stdev

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent), str(HERE.parent / "run2")]
from finalise import DIMENSIONS, fisher_two_sided, fmt, permutation_p  # noqa: E402
from finalise_run2 import mann_whitney_exact, write  # noqa: E402

UNBLIND = HERE / "_unblinding"
OUT = HERE / "results"
RATERS = {"you": "blind_replies_rated.tsv", "LLM": "blind_replies_rated_llm.tsv"}


def read(path: Path) -> list:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def qwk(a: list, b: list, k: int = 5) -> float:
    """Quadratic-weighted Cohen's kappa for two raters' 1..k scores."""
    n = len(a)
    observed = [[0] * k for _ in range(k)]
    for x, y in zip(a, b):
        observed[x - 1][y - 1] += 1
    ra = [sum(row) for row in observed]
    rb = [sum(observed[i][j] for i in range(k)) for j in range(k)]
    w = [[(i - j) ** 2 / (k - 1) ** 2 for j in range(k)] for i in range(k)]
    num = sum(w[i][j] * observed[i][j] for i in range(k) for j in range(k))
    den = sum(w[i][j] * ra[i] * rb[j] / n for i in range(k) for j in range(k))
    return 1 - num / den if den else float("nan")


def apply_corrections(coding: dict, path: Path) -> list:
    """Override coded values from a corrections file, checking each was as recorded."""
    if not path.exists():
        return []
    rows = read(path)
    for r in rows:
        code = coding[r["label"]]
        assert code[r["column"]].strip().upper() == r["coded"], f"{r['label']} {r['column']} is not {r['coded']}"
        code[r["column"]] = r["corrected"]
    return rows


def correction_line(rows: list) -> str:
    return ("Corrected after coding (`coding_corrections.tsv`): " +
            ", ".join(f"{r['session_id']} {r['column']} {r['coded']}→{r['corrected']}" for r in rows) + ".")


def main() -> None:
    OUT.mkdir(exist_ok=True)
    reply_key = {r["blind_id"]: r for r in read(UNBLIND / "key_replies.tsv")}
    session_key = {r["label"]: r for r in read(UNBLIND / "key_sessions.tsv")}
    stats = {r["session_id"]: r for r in read(UNBLIND / "session_stats.tsv")}
    schedule = {s["label"]: s for s in json.loads((UNBLIND / "schedule.json").read_text(encoding="utf-8"))["sessions"]}
    ratings = {}
    for rater, name in RATERS.items():
        rows = {r["blind_id"].strip(): {d: int(r[d]) for d in DIMENSIONS} for r in read(HERE / name)}
        assert set(rows) == set(reply_key), f"{name} does not match the 40 blind replies"
        ratings[rater] = rows

    coding = {r["label"]: r for r in read(HERE / "blind_session_coding.tsv")}
    coded = all((c["followed_lesson_focus"] or "").strip() for c in coding.values())
    corrections = apply_corrections(coding, HERE / "coding_corrections.tsv")
    sessions = {}
    for label, key in session_key.items():
        code = coding[label]
        moves = re.match(r"\s*(\d+)", code["focus_move_count"] or "")
        sessions[key["session_id"]] = {
            "label": label, "condition": key["condition"],
            "focus": code["followed_lesson_focus"].strip().upper() if coded else "",
            "profile": code["used_profile_detail"].strip().upper() if coded else "",
            "moves": int(moves.group(1)) if moves else 0,
            "words": float(stats[key["session_id"]]["mean_words_per_reply"]),
            "stats": stats[key["session_id"]],
        }
    order = sorted(sessions)  # H01-H10, the order played
    write(OUT / "top_table.tsv", [[s, sessions[s]["condition"], sessions[s]["focus"], sessions[s]["profile"],
                                   fmt(sessions[s]["words"])] for s in order])

    by_cond = {c: [v for v in sessions.values() if v["condition"] == c] for c in ("with", "without")}
    n = len(by_cond["with"])
    words = {c: [v["words"] for v in by_cond[c]] for c in by_cond}
    u, p_u = mann_whitney_exact(words["with"], words["without"])
    focus = {c: sum(v["focus"] == "Y" for v in by_cond[c]) for c in by_cond}
    profile = {c: sum(v["profile"] == "Y" for v in by_cond[c]) for c in by_cond}
    moves = {c: sum(v["moves"] for v in by_cond[c]) for c in by_cond}

    lines = ["# Test 4, run 3 (you played April) – results", "",
             "## Sessions", "",
             "| | with | without | difference |", "|---|---|---|---|"]
    if coded:
        lines += [f"| Sessions following lesson focus (of {n}) | {focus['with']} | {focus['without']} | "
                  f"{focus['with'] - focus['without']:+d} |",
                  f"| Focus moves (a/b/c replies) | {moves['with']} | {moves['without']} | "
                  f"{moves['with'] - moves['without']:+d} |",
                  f"| Sessions using a profile detail (of {n}) | {profile['with']} | {profile['without']} | "
                  f"{profile['with'] - profile['without']:+d} |"]
    lines += [f"| Mean words per reply | {fmt(mean(words['with']))} | {fmt(mean(words['without']))} | "
              f"{mean(words['with']) - mean(words['without']):+.2f} |", ""]
    if coded:
        lines.append(f"Fisher's exact test, sessions following lesson focus {focus['with']}/{n} vs "
                     f"{focus['without']}/{n}: p = {fisher_two_sided(focus['with'], n, focus['without'], n):.3f} "
                     "(two-sided).")
        if corrections:
            lines.append(correction_line(corrections))
    else:
        lines.append("Session coding not filled in: lesson focus and profile detail not reported.")
    lines += [f"Mann-Whitney U (exact), session mean words per reply: U = {u:g}, p = {p_u:.3f} (two-sided).", ""]

    for rater, rows in ratings.items():
        suffix = "" if rater == "you" else "_llm"
        cond_of = {b: reply_key[b]["condition"] for b in rows}
        write(OUT / f"bottom_table{suffix}.tsv",
              [[int(b[1:]), cond_of[b], *(rows[b][d] for d in DIMENSIONS)] for b in sorted(rows, key=lambda b: int(b[1:]))])
        res = {}
        for c in ("with", "without"):
            ids = [b for b in rows if cond_of[b] == c]
            means = [mean(rows[b].values()) for b in ids]
            res[c] = {"means": means, "rating": mean(means), "sd": stdev(means),
                      "dims": {d: mean(rows[b][d] for b in ids) for d in DIMENSIONS}, "n": len(ids)}
        w, b = res["with"], res["without"]
        def counts(c: str) -> list:
            return [focus[c] if coded else "", profile[c] if coded else "", fmt(mean(words[c]))]
        write(OUT / f"results_table{suffix}.tsv", [
            [*counts("with"), fmt(w["rating"])], [*counts("without"), fmt(b["rating"])],
            [focus["with"] - focus["without"] if coded else "", profile["with"] - profile["without"] if coded else "",
             fmt(mean(words["with"]) - mean(words["without"])), fmt(w["rating"] - b["rating"])]])
        lines += [f"## Blind ratings: {rater}", "",
                  "| | with | without | difference |", "|---|---|---|---|",
                  f"| Mean rating ({w['n']} replies each) | {fmt(w['rating'])} (SD {fmt(w['sd'])}) | "
                  f"{fmt(b['rating'])} (SD {fmt(b['sd'])}) | {w['rating'] - b['rating']:+.2f} |",
                  *[f"| – {d} | {fmt(w['dims'][d])} | {fmt(b['dims'][d])} | {w['dims'][d] - b['dims'][d]:+.2f} |"
                    for d in DIMENSIONS], "",
                  f"Permutation test, mean blind rating: p = {permutation_p(w['means'], b['means']):.3f} "
                  "(two-sided, 20,000 shuffles, seed 4).", ""]

    ids = sorted(reply_key, key=lambda b: int(b[1:]))
    lines += ["## Agreement, you v LLM (40 replies)", "",
              "| dimension | exact | within 1 | weighted kappa | mean you | mean LLM |", "|---|---|---|---|---|---|"]
    for d in DIMENSIONS:
        a, l = [ratings["you"][b][d] for b in ids], [ratings["LLM"][b][d] for b in ids]
        lines.append(f"| {d} | {sum(x == y for x, y in zip(a, l))}/40 | {sum(abs(x - y) <= 1 for x, y in zip(a, l))}/40 | "
                     f"{qwk(a, l):.2f} | {fmt(mean(a))} | {fmt(mean(l))} |")
    lines.append("")

    guesses = {r["label"]: r for r in read(HERE / "guesses.tsv")}
    made = [g for g in guesses.values() if g["guess"] != "unsure"]
    right = [g for g in made if g["guess"] == {"W": "with", "B": "without"}[schedule[g["label"]]["condition"]]]
    k, total = len(right), len(made)
    p_guess = sum(comb(total, i) for i in range(k, total + 1)) / 2 ** total if total else float("nan")
    lines += ["## Your condition guesses (blinding check)", "",
              f"{k} of {total} guesses right ({len(guesses) - total} unsure). Chance of {k} or more right by "
              f"guessing: p = {p_guess:.3f} (one-sided binomial, 0.5).", "",
              "| session | condition | guess | sure (1-5) |", "|---|---|---|---|",
              *[f"| {h} | {'with' if schedule[h]['condition'] == 'W' else 'without'} | {guesses[h]['guess']} | "
                f"{guesses[h]['confidence']} |" for h in sorted(guesses)], "",
              "## Sessions, un-blinded", "",
              "| session | blind label | focus | moves | profile | mean words | \"I don't know\" turn (after a question) | ended by |",
              "|---|---|---|---|---|---|---|---|",
              *[f"| {s} | {sessions[s]['label']} | {sessions[s]['focus']} | {sessions[s]['moves']} | "
                f"{sessions[s]['profile']} | {fmt(sessions[s]['words'])} | {sessions[s]['stats']['idk_turn']} "
                f"({sessions[s]['stats']['idk_after_question'] or '-'}) | {sessions[s]['stats']['ended_by']} |"
                for s in order]]
    (OUT / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
