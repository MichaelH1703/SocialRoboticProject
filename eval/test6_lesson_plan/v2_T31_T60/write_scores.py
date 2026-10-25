"""The hand judgements for T31-T60, written out as scoring.tsv and quotes.tsv.

Each judgement was made by reading the plan (sections 1-4) against the frozen
truth sheet (../T31_T60_features.tsv), with the rules in ../T21_T30_spec.md as
applied to T21-T30. Two refinements:
- "Gives a reason" is a hit only if at least one reason the plan quotes is
  the young person's own. In T52 the only one quoted is the therapist's.
- A plan can claim both "Did not give any reasons" (section 3) and "Did not
  say why they felt that way" (section 4). When both are false they count as
  two false alarms, because they are two separate claims.
"""

import csv
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
R = []
NF, NR, WHY = "Did not name any feelings.", 'Did not give any reasons (no "because" or "so").', \
    "Did not say why they felt that way."
PART = {"who": "who was there", "where": "where it happened", "how it ended": "how it ended"}


def row(t, f, p, r, res, ev="", note=""):
    R.append([t, f, p, r, res, ev, note])


def hit(t, f, ev="", note=""):
    row(t, f, "Y", "Y", "hit", ev, note)


def miss(t, f, ev="", note=""):
    row(t, f, "Y", "N", "miss", ev, note)


def fa(t, kind, note=""):
    ev = {"missing feelings": NF, "missing reasons": NR, "why they felt": WHY}.get(kind, f"Did not say {PART.get(kind, kind)}.")
    row(t, f"False alarm: {kind}", "N", "Y", "false alarm", ev, note)


def wrong(t, trap, ev, note=""):
    row(t, f"Credited to the child: {trap}", "", "", "wrong speaker", ev, note)


def note(t, text):
    row(t, "(not scored)", "", "", "", "", text)


GAVE = "Gave a reason (the young person's)"
# T31
miss("T31", "Feeling: dislike of the noise (phrase)", NF)
miss("T31", "Gives a reason", NR)
fa("T31", "how it ended", "\"We went back in.\" … \"Miss Patel told us to get our books out again.\"")
fa("T31", "missing reasons", "\"People were talking over the alarm ...\"")
fa("T31", "missing feelings", "\"I didn't like it.\"")
# T32
hit("T32", "Leaves out: how they felt (asked)", NF)
hit("T32", "Gives no reasons", NR)
# T33
miss("T33", "Feeling: enjoyment (phrase)", NF)
hit("T33", "Gives a reason", GAVE)
fa("T33", "who", "\"Nan. I've said that.\"")
fa("T33", "missing feelings", "\"I liked it.\"")
# T34
hit("T34", "Feeling: embarrassment (word)", "Summary: \"feeling embarrassed\"", "Sections 3-4 still say no feelings")
hit("T34", "Gives a reason", GAVE)
fa("T34", "missing feelings", "\"Embarrassing.\"")
note("T34", "Summary credits the therapist's own story (the library book) to the young person")
# T35: labelling failed (no punctuation), so the unlabelled fallback was used
miss("T35", "Feeling: annoyance (word)", "Section 4: Not checked.", "Unlabelled fallback")
miss("T35", "Gives a reason", "", "Unlabelled fallback: reasons not checked")
fa("T35", "where", "\"we went to my cousins\"")
fa("T35", "how it ended", "\"we went home\"; the summary itself mentions going home")
# T36
hit("T36", "Feeling: annoyed (word)", "Named feelings: annoyed")
hit("T36", "Gives a reason", GAVE)
fa("T36", "where", "\"In English. In the classroom.\"")
note("T36", "Summary credits the therapist's own story (bus, travel card) and \"thanks for correcting\" to the young person")
# T37
hit("T37", "Feeling: disappointed (word)", "Named feelings: disappointed")
miss("T37", "Gives a reason", NR, "The summary mentions the money reason, but section 3 says none")
fa("T37", "missing reasons", "\"No. I haven't got that much money.\"")
fa("T37", "why they felt", "\"I'd been looking forward to seeing it.\"")
# T38: two sentences, so the whole session was nearly all one speaker
hit("T38", "Leaves out: how they felt (asked)", NF)
miss("T38", "Gives a reason", NR)
fa("T38", "where", "\"the dentist\"")
fa("T38", "missing reasons", "\"it made a really high noise and i could feel it in my jaw\"")
# T39
miss("T39", "Feeling: dislike (the room) (phrase)", "", "\"It was horrible.\" not mentioned")
miss("T39", "Feeling: annoyance (the tapping) (phrase)", "Named \"angry\": \"I didn't say angry. I wanted the tapping to stop.\"",
     "Credits \"angry\", the word the young person rejected, instead")
hit("T39", "Gives a reason", GAVE)
fa("T39", "why they felt", "\"I could smell about four different perfumes ...\"")
wrong("T39", "angry", "Named feelings: angry", "The therapist's \"You were really angry\", which the young person rejected")
note("T39", "Summary credits the therapist's own story (birthday meal, repeating the menu) to the young person")
# T40
miss("T40", "Feeling: dislike of being late (phrase)", NF)
hit("T40", "Gives a reason", GAVE)
fa("T40", "who", "\"Nobody. I was going to swimming.\" … \"I rang Dad.\"")
fa("T40", "missing feelings", "\"I hate being late\"")
note("T40", "Summary says Dad couldn't come; he did")
# T41
miss("T41", "Feeling: pleased (word)", NF)
hit("T41", "Gives a reason", GAVE)
fa("T41", "missing feelings", "\"Pleased.\"")
wrong("T41", "why the therapist ended up at the entrance", "Gave a reason: \"... so I ended up back at the entrance.\"",
      "The therapist's own story, labelled as the young person's")
# T42
miss("T42", "Feeling: anxiety (felt sick) (phrase)", "", "\"I felt sick\" not mentioned")
hit("T42", "Feeling: confused (word)", "Named feelings: confused")
miss("T42", "Gives a reason", NR)
fa("T42", "missing reasons", "\"I don't know if we're friends like before.\"")
fa("T42", "why they felt", "\"Still confused. I don't know if we're friends like before.\"")
note("T42", "Names \"annoyed\" as the young person's feeling: it was what she thought her friend felt")
# T43: two sentences
miss("T43", "Feeling: stomach dropped (body reaction) (phrase)", NF)
hit("T43", "Gives a reason", GAVE, "The quoted reason spans most of the session")
fa("T43", "who", "\"me and coach and the under fifteens\"")
fa("T43", "where", "\"sports hall\"")
fa("T43", "how it ended", "\"we finished and coach said next week we are doing fitness\"")
fa("T43", "missing feelings", "\"my stomach dropped\"")
# T44
hit("T44", "Feeling: embarrassed (word)", "Named feelings: embarrassed")
hit("T44", "Gives a reason", GAVE)
fa("T44", "why they felt", "\"I should have got it.\" … \"Because I can see the board in class, mostly.\"")
note("T44", "Summary says the optician said black looked better; Dad said it")
# T45
hit("T45", "Feeling: enjoyment (phrase)", "Summary: \"the train scene being good\"")
hit("T45", "Gives a reason", GAVE)
wrong("T45", "frightened", "Named feelings: scared (\"It was just loud. I wasn't scared.\")",
      "Credits the fear the young person denied")
note("T45", "Section 4's \"did not say why\" refers to the wrongly named \"scared\"; no reason for the enjoyment is in the sheet, so not counted")
# T46
hit("T46", "Feeling: annoyed (word)", "Named feelings: annoyed")
miss("T46", "Feeling: dislike (the detention) (phrase)", "", "\"I still didn't like it.\" not mentioned")
miss("T46", "Gives a reason", NR)
fa("T46", "missing reasons", "\"I'd done the work. It was just the upload.\"")
fa("T46", "why they felt", "\"Annoyed. I'd done the work. It was just the upload.\"")
note("T46", "Summary credits the therapist's own story (email without the attachment) to the young person")
# T47
hit("T47", "Feeling: happy (word)", "Named feelings: happy")
miss("T47", "Gives a reason", NR)
fa("T47", "missing reasons", "\"I knew nearly all the words.\"")
fa("T47", "why they felt", "\"Happy. I knew nearly all the words.\"")
# T48
miss("T48", "Feeling: dislike (unannounced changes) (phrase)", NF)
miss("T48", "Gives a reason", NR, "The summary mentions the reason, but section 3 says none")
fa("T48", "how it ended", "\"We went to form.\"")
fa("T48", "missing reasons", "\"People had trays and bags and the floor was sticky.\"")
fa("T48", "missing feelings", "\"I hate it when things move and no one tells us.\"")
# T49
miss("T49", "Feeling: exhausted (phrase)", NF)
hit("T49", "Gives a reason", GAVE)
fa("T49", "where", "\"The gate changed. It said gate 18 ...\": an airport gate; she never says \"airport\" (borderline, as noted in the truth sheet)")
fa("T49", "missing feelings", "\"I was exhausted.\"")
# T50
hit("T50", "Feeling: relieved (word)", "Named feelings: relieved")
hit("T50", "Feeling: worried (word)", "Named feelings: worried")
miss("T50", "Gives a reason", NR, "The summary mentions the cage door, but section 3 says none")
fa("T50", "missing reasons", "\"The cage door wasn't shut properly.\"")
fa("T50", "why they felt", "\"I thought the cat might get him.\"")
# T51
hit("T51", "Feeling: worried (word)", "Named feelings: worried")
miss("T51", "Gives a reason", NR)
fa("T51", "missing reasons", "\"I didn't know if I was allowed to go in the back room without asking.\"")
fa("T51", "why they felt", "as above")
note("T51", "Summary credits the therapist's own story (sorting a cupboard) to the young person")
# T52
hit("T52", "Leaves out: how they felt (asked)", NF)
miss("T52", "Gives a reason", "Gave a reason: \"I went into a meeting room ... so I had to work out where to sit.\"",
     "The only reason quoted is the therapist's own story; the young person's \"It's not my name.\" is not reported")
note("T52", "That therapist story reason was not recorded as a trap in the truth sheet (annotation omission), so it is not counted as a wrong-speaker credit; the summary also credits the story to the young person")
# T53
miss("T53", "Feeling: stress (face hot) (phrase)", NF)
hit("T53", "Gives a reason", GAVE)
fa("T53", "missing feelings", "\"My face got hot and I kept checking the time.\"")
note("T53", "One quoted reason and the summary are the therapist's own story (cancelled bus); it was not recorded as a trap in the truth sheet (annotation omission), so it is not counted")
# T54
hit("T54", "Leaves out: how it ended (asked)", "Did not say how it ended.")
hit("T54", "Leaves out: how they felt (asked)", NF)
hit("T54", "Gives no reasons", NR)
note("T54", "Summary credits the therapist's \"I've probably forgotten a detail\" and \"thanks for correcting\" to the young person")
# T55
miss("T55", "Feeling: amusement (phrase)", NF)
miss("T55", "Feeling: annoyance (phrase)", NF)
hit("T55", "Gives a reason", GAVE)
fa("T55", "missing feelings", "\"I couldn't stop laughing\", \"A bit\" (annoyed)")
# T56
hit("T56", "Feeling: embarrassed (word)", "Named feelings: embarrassed")
hit("T56", "Gives a reason", GAVE)
fa("T56", "why they felt", "\"I thought I'd messed it up straight away.\"")
note("T56", "Summary credits the therapist's own story (pottery class) to the young person")
# T57
hit("T57", "Leaves out: how they felt (asked)", NF)
hit("T57", "Gives no reasons", NR)
note("T57", "Summary credits the therapist's own story (letters at the optician's) to the young person")
# T58: three sentences
miss("T58", "Feeling: distracted (phrase)", NF)
miss("T58", "Gives a reason", NR)
fa("T58", "who", "\"me ellie and harry and then miss put daniel in as well\"")
fa("T58", "where", "\"science room 12\"")
fa("T58", "missing feelings", "\"it was just distracting\"")
fa("T58", "missing reasons", "\"cos it kept changing\"")
note("T58", "The whole summary is the therapist's line \"The picture took longer than the font issue\"")
# T59
miss("T59", "Feeling: worry (stomach tight) (phrase)", NF)
miss("T59", "Feeling: pleased (word)", NF)
hit("T59", "Gives a reason", GAVE)
fa("T59", "missing feelings", "\"My stomach went all tight\", \"Properly pleased\"")
note("T59", "Summary credits the therapist's own story (swimming, water up the nose) to the young person")
# T60
hit("T60", "Feeling: annoyed (word)", "Named feelings: annoyed")
miss("T60", "Feeling: disgust (the coffee) (phrase)", "", "\"it was rank\" not mentioned")
miss("T60", "Feeling: satisfied with the draw (phrase)", "", "\"Better than losing.\" not mentioned")
hit("T60", "Gives a reason", GAVE)
fa("T60", "why they felt", "\"I was annoyed. The linesman was right there.\"")

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
        # A quote can join sentences from several turns; it is exact if every
        # sentence is in the session word for word (as for T01-T30).
        assert q["auto_match"] == "exact" or norm(q["quote"]) in session or \
            all(norm(s) in session for s in sents), q
        note_ = ""
        if q["auto_match"] != "exact" and norm(q["quote"]) in session:
            said, note_ = "therapist/child", "runs across many turns of both speakers (unlabelled sentence)"
        elif not theirs:
            said = "child"
        elif len(theirs) == len(sents):
            said, note_ = "therapist", "the therapist's words, labelled as the young person's"
        else:
            said, note_ = "therapist/child", f"includes {len(theirs)} sentence(s) of the therapist's, labelled as the young person's"
        f.write(f"{q['transcript_id']}\t{q['quote']}\texact\t{said}\t{note_}\n")
print(len(R), "scoring rows;", len(quotes), "quotes")
