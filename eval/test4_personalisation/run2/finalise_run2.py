"""Un-blind run 2 and produce the paste-ready tables, for the new 20 sessions and
pooled with run 1 (30). Run only once run 2's blind ratings
(blind_replies_rated.tsv) and session coding (blind_session_coding.tsv) are final.

Writes results/ (no header rows, as run 1's results/):
    top_table.tsv              W6-W15 then B6-B15: session_id, condition, focus, profile, words
    top_table_pooled.tsv       the same for all 30 (W1-W15, B1-B15)
    bottom_table.tsv           blind_id (41-120), condition, responsive, clear, technique, no_invention
    results_table.tsv          with / without / difference rows, new 20 (run 1's 4 columns)
    results_table_pooled.tsv   the same, pooled 30
    summary.md                 condition-level stats, tests and checks for both

Run 1 is recomputed from its own blind files, the way ../finalise.py did, and
checked against ../results/ before pooling. Tests are run 1's: Fisher's exact
(lesson focus), exact Mann-Whitney U (session words per reply) and a
permutation test on reply ratings (20,000 shuffles, seed 4). The Mann-Whitney
distribution is counted exactly rather than enumerated, so 15 v 15 is quick,
and uses midranks if any session means tie.
"""

import csv
import re
import sys
from pathlib import Path
from statistics import mean, stdev

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from finalise import DIMENSIONS, fisher_two_sided, fmt, permutation_p  # noqa: E402

RUN1 = HERE.parent
OUT = HERE / "results"


def read(path: Path) -> list:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def write(path: Path, rows: list) -> None:
    path.write_text("\n".join("\t".join(str(c) for c in row) for row in rows) + "\n", encoding="utf-8")


def load(folder: Path, n_replies: int) -> tuple:
    """One run's un-blinded session coding and reply ratings."""
    unblind = folder / "_unblinding"
    ratings = {r["blind_id"]: {d: int(r[d]) for d in DIMENSIONS} for r in read(folder / "blind_replies_rated.tsv")}
    reply_key = {r["blind_id"]: r for r in read(unblind / "key_replies.tsv")}
    session_key = {r["label"]: r for r in read(unblind / "key_sessions.tsv")}
    coding = {r["label"]: r for r in read(folder / "blind_session_coding.tsv")}
    stats = {r["session_id"]: r for r in read(unblind / "session_stats.tsv")}
    assert len(ratings) == n_replies and set(ratings) == set(reply_key), f"{folder.name}: ratings do not match the key"
    assert set(coding) == set(session_key), f"{folder.name}: coding does not cover every session"
    for label, code in coding.items():
        for col in ("followed_lesson_focus", "used_profile_detail"):
            assert code[col].strip().upper() in ("Y", "N"), f"{folder.name} {label}: {col} is not Y or N"

    sessions = {}
    for label, key in session_key.items():
        code = coding[label]
        moves = re.match(r"\s*(\d+)", code["focus_move_count"] or "0")
        sessions[key["session_id"]] = {
            "label": label, "condition": key["condition"],
            "focus": code["followed_lesson_focus"].strip().upper(),
            "profile": code["used_profile_detail"].strip().upper(),
            "moves": int(moves.group(1)) if moves else 0,
            "words": float(stats[key["session_id"]]["mean_words_per_reply"]),
            "stats": stats[key["session_id"]],
        }
    replies = {b: {"condition": reply_key[b]["condition"], "session": reply_key[b]["session_id"],
                   "scores": ratings[b], "mean": mean(ratings[b].values())} for b in ratings}
    return sessions, replies


def order(sessions: dict) -> list:
    return sorted(sessions, key=lambda s: (s[0] != "W", int(s[1:])))


def mann_whitney_exact(xs: list, ys: list) -> tuple:
    """Exact two-sided Mann-Whitney U (midranks for ties): (U, p). Same as run 1's when nothing ties."""
    values = sorted(xs + ys)
    twice_rank = {v: 2 * values.index(v) + values.count(v) + 1 for v in set(values)}  # 2 x midrank
    n1, n2 = len(xs), len(ys)
    # ways[k][s]: subsets of k sessions whose doubled ranks sum to s
    ways = [dict() for _ in range(n1 + 1)]
    ways[0][0] = 1
    for v in values:
        r = twice_rank[v]
        for k in range(n1 - 1, -1, -1):
            for s, count in ways[k].items():
                ways[k + 1][s + r] = ways[k + 1].get(s + r, 0) + count
    def u_of(twice_sum: int) -> float:
        return twice_sum / 2 - n1 * (n1 + 1) / 2
    u = u_of(sum(twice_rank[x] for x in xs))
    centre = n1 * n2 / 2
    total = sum(ways[n1].values())
    extreme = sum(c for s, c in ways[n1].items() if abs(u_of(s) - centre) >= abs(u - centre) - 1e-9)
    return u, extreme / total


def summarise(sessions: dict, replies: dict) -> dict:
    result = {}
    for cond in ("with", "without"):
        ss = [v for v in sessions.values() if v["condition"] == cond]
        rs = [r for r in replies.values() if r["condition"] == cond]
        result[cond] = {
            "focus": sum(v["focus"] == "Y" for v in ss), "profile": sum(v["profile"] == "Y" for v in ss),
            "moves": sum(v["moves"] for v in ss), "words_list": [v["words"] for v in ss],
            "words": mean(v["words"] for v in ss), "reply_means": [r["mean"] for r in rs],
            "rating": mean(r["mean"] for r in rs), "rating_sd": stdev(r["mean"] for r in rs),
            "dims": {d: mean(r["scores"][d] for r in rs) for d in DIMENSIONS},
            "n_sessions": len(ss), "n_replies": len(rs),
        }
    return result


def results_rows(res: dict) -> list:
    w, b = res["with"], res["without"]
    return [[w["focus"], w["profile"], fmt(w["words"]), fmt(w["rating"])],
            [b["focus"], b["profile"], fmt(b["words"]), fmt(b["rating"])],
            [w["focus"] - b["focus"], w["profile"] - b["profile"], fmt(w["words"] - b["words"]),
             fmt(w["rating"] - b["rating"])]]


def report(title: str, res: dict) -> list:
    w, b = res["with"], res["without"]
    n, nr = w["n_sessions"], w["n_replies"]
    u, p_u = mann_whitney_exact(w["words_list"], b["words_list"])
    return [
        f"## {title}", "",
        "| | with | without | difference |", "|---|---|---|---|",
        f"| Sessions following lesson focus (of {n}) | {w['focus']} | {b['focus']} | {w['focus'] - b['focus']:+d} |",
        f"| Focus moves (a/b/c replies, all {n} sessions) | {w['moves']} | {b['moves']} | {w['moves'] - b['moves']:+d} |",
        f"| Sessions using a profile detail (of {n}) | {w['profile']} | {b['profile']} | {w['profile'] - b['profile']:+d} |",
        f"| Mean words per reply | {fmt(w['words'])} | {fmt(b['words'])} | {w['words'] - b['words']:+.2f} |",
        f"| Mean rating, blind ({nr} replies each) | {fmt(w['rating'])} (SD {fmt(w['rating_sd'])}) | "
        f"{fmt(b['rating'])} (SD {fmt(b['rating_sd'])}) | {w['rating'] - b['rating']:+.2f} |",
        *[f"| – {d} | {fmt(w['dims'][d])} | {fmt(b['dims'][d])} | {w['dims'][d] - b['dims'][d]:+.2f} |"
          for d in DIMENSIONS],
        "",
        f"Fisher's exact test, sessions following lesson focus {w['focus']}/{n} vs {b['focus']}/{n}: "
        f"p = {fisher_two_sided(w['focus'], n, b['focus'], n):.3f} (two-sided).",
        f"Mann-Whitney U (exact), session mean words per reply: U = {u:g}, p = {p_u:.3f} (two-sided).",
        f"Permutation test, mean blind rating: p = {permutation_p(w['reply_means'], b['reply_means']):.3f} "
        "(two-sided, 20,000 shuffles, seed 4).", "",
    ]


def main() -> None:
    OUT.mkdir(exist_ok=True)
    s1, r1 = load(RUN1, 40)
    s2, r2 = load(HERE, 80)

    # Run 1 recomputed here must match what run 1 reported.
    top1 = [[s, s1[s]["condition"], s1[s]["focus"], s1[s]["profile"], fmt(s1[s]["words"])] for s in order(s1)]
    assert "\n".join("\t".join(r) for r in top1) == (RUN1 / "results" / "top_table.tsv").read_text(
        encoding="utf-8").strip(), "run 1 recomputed differs from ../results/top_table.tsv"
    assert "\n".join("\t".join(map(str, r)) for r in results_rows(summarise(s1, r1))) == (
        RUN1 / "results" / "results_table.tsv").read_text(encoding="utf-8").strip(), "run 1 results differ"

    pooled_s, pooled_r = {**s1, **s2}, {**r1, **r2}
    new, pooled = summarise(s2, r2), summarise(pooled_s, pooled_r)

    def top(sessions: dict) -> list:
        return [[s, sessions[s]["condition"], sessions[s]["focus"], sessions[s]["profile"],
                 fmt(sessions[s]["words"])] for s in order(sessions)]
    write(OUT / "top_table.tsv", top(s2))
    write(OUT / "top_table_pooled.tsv", top(pooled_s))
    write(OUT / "bottom_table.tsv",
          [[int(b[1:]), r2[b]["condition"], *(r2[b]["scores"][d] for d in DIMENSIONS)] for b in sorted(r2, key=lambda b: int(b[1:]))])
    write(OUT / "results_table.tsv", results_rows(new))
    write(OUT / "results_table_pooled.tsv", results_rows(pooled))

    idk = {s: v["stats"]["idk_turn"] for s, v in s2.items()}
    after_q = {s: v["stats"]["idk_after_question"] for s, v in s2.items()}
    cols = order(s2)
    auto_keys = ("auto_explanation_replies", "auto_perspective_replies", "auto_choice_replies",
                 "auto_profile_word_replies", "replaced_by_safety", "question_cuts")
    auto = {c: {k: sum(int(v["stats"][k]) for v in s2.values() if v["condition"] == c) for k in auto_keys}
            for c in ("with", "without")}
    lines = [
        "# Test 4 results, run 2 and pooled", "",
        *report("New 20 sessions (W6–W15, B6–B15)", new),
        *report("Pooled 30 sessions (W1–W15, B1–B15)", pooled),
        "Run 2's pairs share the child's seed and the \"I don't know\" turn. The tests above treat",
        "the two conditions as independent, as run 1 did.", "",
        "## Run 2: forced \"I don't know\" (turn, and whether Reachy's line before it was a question)", "",
        "| session | " + " | ".join(cols) + " |", "|---|" + "---|" * len(cols),
        "| turn | " + " | ".join(idk[s] for s in cols) + " |",
        "| after a question | " + " | ".join(after_q[s] for s in cols) + " |", "",
        "## Run 2: automatic keyword checks (cross-check only, 10 sessions per condition)", "",
        "| check | with | without |", "|---|---|---|",
        *[f"| {k} | {auto['with'][k]} | {auto['without'][k]} |" for k in auto_keys], "",
        "## Run 2: session coding, un-blinded", "",
        "| session | blind label | focus | moves | profile | mean words | complete |", "|---|---|---|---|---|---|---|",
        *[f"| {s} | {s2[s]['label']} | {s2[s]['focus']} | {s2[s]['moves']} | {s2[s]['profile']} | "
          f"{fmt(s2[s]['words'])} | {s2[s]['stats']['complete']} |" for s in cols],
    ]
    (OUT / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
