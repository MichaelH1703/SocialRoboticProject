"""Un-blind Test 4 and produce the paste-ready tables. Run only once the blind
ratings (blind_replies_rated.tsv) and session coding (blind_session_coding.tsv)
are final.

Writes results/:
    top_table.tsv        10 rows for the sheet's top table (W1-W5, then B1-B5)
    results_table.tsv    with / without / difference rows for the Results table
    bottom_table.tsv     the sheet's blind-ratings table, rows 1-40 (= R01-R40)
    summary.md           condition-level stats and checks
"""

import csv
import json
import random
import re
from math import comb
from pathlib import Path
from statistics import mean, stdev

HERE = Path(__file__).resolve().parent
UNBLIND = HERE / "_unblinding"
OUT = HERE / "results"
DIMENSIONS = ["responsive", "clear", "technique", "no_invention"]


def read(path: Path) -> list:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def write(path: Path, rows: list) -> None:
    path.write_text("\n".join("\t".join(str(c) for c in row) for row in rows) + "\n", encoding="utf-8")


def fmt(x: float) -> str:
    return f"{x:.2f}"


def fisher_two_sided(a: int, n1: int, c: int, n2: int) -> float:
    """Fisher's exact test for a/n1 vs c/n2 (two-sided, summing tables no likelier than observed)."""
    total, k = n1 + n2, a + c
    def p(x: int) -> float:
        return comb(n1, x) * comb(n2, k - x) / comb(total, k)
    observed = p(a)
    return sum(p(x) for x in range(max(0, k - n2), min(k, n1) + 1) if p(x) <= observed + 1e-12)


def mann_whitney_exact(xs: list, ys: list) -> tuple:
    """Exact two-sided Mann-Whitney U for small samples without ties: (U, p)."""
    from itertools import combinations
    ranked = sorted(xs + ys)
    rank = {v: i + 1 for i, v in enumerate(ranked)}
    n1, n2 = len(xs), len(ys)
    def u_of(ranks: tuple) -> float:
        return sum(ranks) - n1 * (n1 + 1) / 2
    u = u_of(tuple(rank[x] for x in xs))
    u_min = min(u, n1 * n2 - u)
    all_u = [u_of(c) for c in combinations(range(1, n1 + n2 + 1), n1)]
    extreme = sum(1 for v in all_u if min(v, n1 * n2 - v) <= u_min)
    return u, extreme / len(all_u)


def permutation_p(xs: list, ys: list, rounds: int = 20000, seed: int = 4) -> float:
    """Two-sided permutation test on the difference in means."""
    observed = abs(mean(xs) - mean(ys))
    pooled, n = xs + ys, len(xs)
    rng = random.Random(seed)
    hits = 0
    for _ in range(rounds):
        rng.shuffle(pooled)
        if abs(mean(pooled[:n]) - mean(pooled[n:])) >= observed - 1e-12:
            hits += 1
    return (hits + 1) / (rounds + 1)


def main() -> None:
    OUT.mkdir(exist_ok=True)
    ratings = {r["blind_id"]: {d: int(r[d]) for d in DIMENSIONS} for r in read(HERE / "blind_replies_rated.tsv")}
    reply_key = {r["blind_id"]: r for r in read(UNBLIND / "key_replies.tsv")}
    session_key = {r["label"]: r for r in read(UNBLIND / "key_sessions.tsv")}
    coding = {r["label"]: r for r in read(HERE / "blind_session_coding.tsv")}
    stats = {r["session_id"]: r for r in read(UNBLIND / "session_stats.tsv")}
    turns = json.loads((UNBLIND / "turns.json").read_text(encoding="utf-8"))
    assert len(ratings) == 40 and set(ratings) == set(reply_key), "ratings do not match the 40 blind replies"
    assert set(coding) == set(session_key), "coding does not cover S01-S10"

    # Session-level coding, un-blinded.
    by_session = {}
    for label, key in session_key.items():
        code = coding[label]
        moves = re.match(r"\s*(\d+)", code["focus_move_count"] or "0")
        by_session[key["session_id"]] = {
            "label": label, "condition": key["condition"],
            "focus": code["followed_lesson_focus"].strip().upper(),
            "profile": code["used_profile_detail"].strip().upper(),
            "moves": int(moves.group(1)) if moves else 0,
            "words": float(stats[key["session_id"]]["mean_words_per_reply"]),
        }
    order = [f"W{i}" for i in range(1, 6)] + [f"B{i}" for i in range(1, 6)]
    write(OUT / "top_table.tsv",
          [[s, by_session[s]["condition"], by_session[s]["focus"], by_session[s]["profile"],
            fmt(by_session[s]["words"])] for s in order])

    # Reply-level ratings, un-blinded.
    reply_mean = {b: mean(r.values()) for b, r in ratings.items()}
    cond_of = {b: reply_key[b]["condition"] for b in ratings}
    # The sheet's blind-ratings table: blind_id is pre-filled 1-40 (= R01-R40),
    # then condition, responsive, clear, technique, no_invention.
    write(OUT / "bottom_table.tsv",
          [[cond_of[b], *(ratings[b][d] for d in DIMENSIONS)] for b in sorted(ratings)])

    result = {}
    for cond in ("with", "without"):
        sessions = [v for v in by_session.values() if v["condition"] == cond]
        replies = [b for b in ratings if cond_of[b] == cond]
        result[cond] = {
            "focus": sum(v["focus"] == "Y" for v in sessions),
            "profile": sum(v["profile"] == "Y" for v in sessions),
            "words": mean(v["words"] for v in sessions),
            "rating": mean(reply_mean[b] for b in replies),
            "rating_sd": stdev(reply_mean[b] for b in replies),
            "moves": sum(v["moves"] for v in sessions),
            "dims": {d: mean(ratings[b][d] for b in replies) for d in DIMENSIONS},
            "reply_means": [reply_mean[b] for b in replies],
            "n_sessions": len(sessions), "n_replies": len(replies),
        }
    w, b = result["with"], result["without"]
    write(OUT / "results_table.tsv", [
        [w["focus"], w["profile"], fmt(w["words"]), fmt(w["rating"])],
        [b["focus"], b["profile"], fmt(b["words"]), fmt(b["rating"])],
        [w["focus"] - b["focus"], w["profile"] - b["profile"], fmt(w["words"] - b["words"]),
         fmt(w["rating"] - b["rating"])],
    ])

    # Where the forced "I don't know" landed, and the automatic keyword checks.
    idk = {s["session"]: next(t["turn"] for t in s["turns"] if t["child"] == "I don't know.") for s in turns}
    auto = {cond: {k: sum(int(stats[s][k]) for s in stats if stats[s]["condition"] == cond)
                   for k in ("auto_explanation_replies", "auto_perspective_replies", "auto_choice_replies",
                             "auto_profile_word_replies", "replaced_by_safety", "question_cuts")}
            for cond in ("with", "without")}

    lines = [
        "# Test 4 results",
        "",
        "| | with | without | difference |",
        "|---|---|---|---|",
        f"| Sessions following lesson focus (of 5) | {w['focus']} | {b['focus']} | {w['focus'] - b['focus']:+d} |",
        f"| Focus moves (a/b/c replies, all 5 sessions) | {w['moves']} | {b['moves']} | {w['moves'] - b['moves']:+d} |",
        f"| Sessions using a profile detail (of 5) | {w['profile']} | {b['profile']} | {w['profile'] - b['profile']:+d} |",
        f"| Mean words per reply | {fmt(w['words'])} | {fmt(b['words'])} | {w['words'] - b['words']:+.2f} |",
        f"| Mean rating, blind (20 replies each) | {fmt(w['rating'])} (SD {fmt(w['rating_sd'])}) | "
        f"{fmt(b['rating'])} (SD {fmt(b['rating_sd'])}) | {w['rating'] - b['rating']:+.2f} |",
        *[f"| – {d} | {fmt(w['dims'][d])} | {fmt(b['dims'][d])} | {w['dims'][d] - b['dims'][d]:+.2f} |"
          for d in DIMENSIONS],
        "",
        f"Fisher's exact test, sessions following lesson focus {w['focus']}/5 vs {b['focus']}/5: "
        f"p = {fisher_two_sided(w['focus'], 5, b['focus'], 5):.3f} (two-sided).",
        "Mann-Whitney U (exact), session mean words per reply: U = {:.0f}, p = {:.3f} (two-sided).".format(
            *mann_whitney_exact([by_session[f"W{i}"]["words"] for i in range(1, 6)],
                                [by_session[f"B{i}"]["words"] for i in range(1, 6)])),
        f"Permutation test, mean blind rating: p = {permutation_p(w['reply_means'], b['reply_means']):.3f} "
        "(two-sided, 20,000 shuffles, seed 4).",
        "",
        "## Forced \"I don't know\" (turn it landed on)",
        "",
        "| session | " + " | ".join(order) + " |",
        "|---|" + "---|" * len(order),
        "| turn | " + " | ".join(str(idk[s]) for s in order) + " |",
        "",
        "## Automatic keyword checks (cross-check only, all 5 sessions per condition)",
        "",
        "| check | with | without |",
        "|---|---|---|",
        *[f"| {k} | {auto['with'][k]} | {auto['without'][k]} |" for k in auto["with"]],
        "",
        "## Session coding, un-blinded",
        "",
        "| session | blind label | focus | moves | profile | mean words |",
        "|---|---|---|---|---|---|",
        *[f"| {s} | {by_session[s]['label']} | {by_session[s]['focus']} | {by_session[s]['moves']} | "
          f"{by_session[s]['profile']} | {fmt(by_session[s]['words'])} |" for s in order],
    ]
    (OUT / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
