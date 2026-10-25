"""The hand judgements for T21-T30, written out as scoring.tsv and quotes.tsv.

Each judgement was made by reading the plan (sections 1-4) against the planted
sheet (../T21_T30_features.tsv), using the rules in ../T21_T30_spec.md. The
planted sheet is the truth: nothing is counted that it does not record.
"""

import csv
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
DNS = "Did not say {}."
R = []


def row(t, f, p, r, res, ev="", note=""):
    R.append([t, f, p, r, res, ev, note])


# T21: speaker labelling failed (no punctuation), so the plan used the unlabelled fallback
row("T21", "Leaves out: who (silent)", "Y", "Y", "hit", DNS.format("who was there"))
row("T21", "Leaves out: how it ended (asked)", "Y", "Y", "hit", DNS.format("how it ended"))
row("T21", "Feeling: dislike (phrase)", "Y", "N", "miss", "Section 4: Not checked.",
    "Labelling failed (no punctuation), so feelings were not counted")
row("T21", "Gives a reason", "Y", "N", "miss", "", "Unlabelled fallback: reasons not checked")
row("T21", "False alarm: what happened", "N", "Y", "false alarm", DNS.format("what happened"),
    "The child described the chair, the cape, the scissors and the clippers")
row("T21", "(not scored)", "", "", "", "", "Summary says the clippers went up like a rocket (it was the chair)")
# T22
row("T22", "Leaves out: where (yes-only)", "Y", "Y", "hit", DNS.format("where it happened"))
row("T22", "Leaves out: how they felt (silent)", "Y", "Y", "hit", "Did not name any feelings.")
row("T22", "Gives a reason", "Y", "Y", "hit", "Gave a reason: \"The car stopped because it didn't have no petrol. Mum said.\"")
row("T22", "Credited to the child: why the man used a torch", "", "", "wrong speaker",
    "Gave a reason: \"... because it was getting dark.\"", "The therapist's reason, labelled as the child's")
# T23 (nothing left out)
row("T23", "Feeling: scared (phrase)", "Y", "N", "miss", "", "\"My tummy went all funny, like, wobbly.\" not mentioned")
row("T23", "Feeling: upset (phrase)", "Y", "N", "miss", "", "\"I was crying.\" not mentioned")
row("T23", "Feeling: happy (word)", "Y", "Y", "hit", "Named feelings: happy")
row("T23", "Gives a reason", "Y", "Y", "hit", "Gave a reason: \"... cos I was a good girl.\"")
row("T23", "(not scored)", "", "", "", "",
    "Section 4 says the child did not say why they felt happy: arguably wrong (\"Mummy came running ... I was "
    "happy then\"), but the planted sheet records no reason for happy. Summary credits the therapist's "
    "\"I've never tried one\" to the child")
# T24
row("T24", "Leaves out: who (yes-only)", "Y", "Y", "hit", DNS.format("who was there"))
row("T24", "Leaves out: how it ended (silent)", "Y", "Y", "hit", DNS.format("how it ended"))
row("T24", "Feeling: scared (phrase)", "Y", "N", "miss",
    "Quoted only as a reason; sections 3-4 say \"Did not name any feelings.\"")
row("T24", "Feeling: enjoyment (phrase)", "Y", "N", "miss", "", "\"I loved the diplodocus. It was so cool.\" not mentioned")
row("T24", "Gives a reason", "Y", "Y", "hit", "Gave a reason: \"It was a bit scary because it had really big teeth ...\"")
row("T24", "False alarm: missing feelings", "N", "Y", "false alarm", "Did not name any feelings.",
    "\"It was a bit scary\", \"I loved the diplodocus\"")
# T25
row("T25", "Leaves out: who (asked)", "Y", "Y", "hit", DNS.format("who was there"))
row("T25", "Leaves out: how it ended (silent)", "Y", "Y", "hit", DNS.format("how it ended"))
row("T25", "Feeling: scared (phrase)", "Y", "N", "miss", "", "\"My heart went really fast\" not mentioned")
row("T25", "Feeling: enjoyment (phrase)", "Y", "N", "miss", "", "\"It was fun with the candles.\" not mentioned")
row("T25", "Gives a reason", "Y", "Y", "hit", "Gave a reason: \"You're not allowed to touch them cos they're hot ...\"")
row("T25", "False alarm: missing feelings", "N", "Y", "false alarm", "Did not name any feelings.",
    "\"My heart went really fast\", \"It was fun with the candles\"")
row("T25", "(not scored)", "", "", "", "",
    "Summary credits the therapist's \"I had to feel around for my towel\" to the child; the sequencing word "
    "\"first\" is the therapist's \"You go first\"")
# T26
row("T26", "Leaves out: how they felt (asked)", "Y", "Y", "hit", "Did not name any feelings.")
row("T26", "Leaves out: where (silent)", "Y", "Y", "hit", DNS.format("where it happened"))
row("T26", "Gives no reasons", "Y", "Y", "hit", "Did not give any reasons (no \"because\" or \"so\").")
# T27
row("T27", "Leaves out: what happened (asked)", "Y", "N", "miss", "Said what happened: \"I wore my glitter top ...\"",
    "Took what she wore, and the disco being the best, as what happened")
row("T27", "Feeling: enjoyment (phrase)", "Y", "Y", "hit", "Summary: the child said the disco was the best one ever")
row("T27", "Feeling: sad (word)", "Y", "Y", "hit", "Named feelings: sad")
row("T27", "Gives a reason", "Y", "Y", "hit", "Gave a reason: \"Cos it's my best one ...\"")
# T28: one unpunctuated sentence, all labelled as the child's
row("T28", "Leaves out: where (silent)", "Y", "Y", "hit", DNS.format("where it happened"))
row("T28", "Leaves out: how it ended (silent)", "Y", "Y", "hit", DNS.format("how it ended"))
row("T28", "Feeling: amused (phrase)", "Y", "Y", "hit", "Summary: the child laughed",
    "Right only because the whole transcript was labelled as the child's")
row("T28", "Feeling: enjoyment (phrase)", "Y", "Y", "hit", "Summary: The child said it was so fun", "As above")
row("T28", "Gives no reasons", "Y", "Y", "hit", "Did not give any reasons (no \"because\" or \"so\").")
row("T28", "Credited to the child: proud", "", "", "wrong speaker", "Named feelings: proud",
    "The therapist's \"you must have felt really proud\": the whole transcript was one sentence, labelled as the child's")
# T29 (nothing left out)
row("T29", "Feeling: scared (word)", "Y", "Y", "hit", "Named feelings: scared")
row("T29", "Feeling: embarrassed (phrase)", "Y", "N", "miss", "",
    "\"my face went all hot. Everyone was looking at me.\" quoted only as part of what happened")
row("T29", "Gives a reason", "Y", "Y", "hit", "Gave a reason: \"Then I had to go to the office because it wouldn't stop.\"")
row("T29", "False alarm: missing reasons", "N", "Y", "false alarm", "Did not say why they felt that way.",
    "\"There was loads of blood on my book. I was scared.\"")
# T30
row("T30", "Leaves out: what happened (asked)", "Y", "N", "miss",
    "Said what happened: \"I had a sparkly dress ... I don't remember.\"",
    "Took her dress and shoes, and even \"I don't remember\", as what happened")
row("T30", "Feeling: enjoyment (phrase)", "Y", "N", "miss", "", "\"It was the best day ever.\" not mentioned")
row("T30", "Gives no reasons", "Y", "Y", "hit", "Did not give any reasons (no \"because\" or \"so\").")
row("T30", "False alarm: missing feelings", "N", "Y", "false alarm", "Did not name any feelings.", "\"It was the best day ever.\"")
row("T30", "(not scored)", "", "", "", "",
    "Summary credits the therapist's own story (restaurant, mum's birthday, sparkler cake) to the child: "
    "it was labelled as the child's")

with (HERE / "scoring.tsv").open("w", encoding="utf-8", newline="") as f:
    f.write("transcript_id\tfeature\tplanted\treported\tresult\tevidence (plan, sections 1-4)\tnote\n")
    f.writelines("\t".join(r) + "\n" for r in R)


def norm(x: str) -> str:
    x = x.lower().replace("’", "'")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9' ]+", " ", x)).strip()


with (HERE / "quotes_auto.tsv").open(encoding="utf-8", newline="") as f:
    quotes = list(csv.DictReader(f, delimiter="\t", quoting=csv.QUOTE_NONE))
with (HERE / "quotes.tsv").open("w", encoding="utf-8", newline="") as f:
    f.write("transcript_id\tquote\tresult\tsaid_by\tnote\n")
    for q in quotes:
        p = re.split(r"\b(Therapist|Child)\.\s*",
                     (HERE.parent / "transcripts" / f"{q['transcript_id']}.txt").read_text(encoding="utf-8"))
        child = " | ".join(norm(p[i + 1]) for i in range(1, len(p) - 1, 2) if p[i] == "Child")
        session = norm(" ".join(p[i + 1] for i in range(1, len(p) - 1, 2)))
        sents = [s for s in re.split(r"(?<=[.!?])\s+", q["quote"]) if norm(s)]
        theirs = [s for s in sents if not re.search(rf"(?<![a-z0-9']){re.escape(norm(s))}(?![a-z0-9'])", child)]
        assert q["auto_match"] == "exact" or norm(q["quote"]) in session, q
        note = ""
        if q["auto_match"] != "exact":
            said, note = "therapist/child", "runs across many turns of both speakers (one unlabelled sentence)"
        elif not theirs:
            said = "child"
        elif len(theirs) == len(sents):
            said, note = "therapist", "the therapist's words, labelled as the child's"
        else:
            said, note = "therapist/child", f"includes {len(theirs)} sentence(s) of the therapist's, labelled as the child's"
        f.write(f"{q['transcript_id']}\t{q['quote']}\texact\t{said}\t{note}\n")
print(len(R), "scoring rows;", len(quotes), "quotes")
