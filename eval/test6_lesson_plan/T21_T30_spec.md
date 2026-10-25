# Writing transcripts T21–T30: a spec for the writer

## What this is for

The Reachy project makes a lesson plan from a transcript of a speech therapy
session in which a child recounts something that happened to them. The plan
says which parts of the recount the child gave or left out, what feelings they
expressed, and whether they gave reasons.

To test that, we need transcripts where we already know the answers. You will
write 10 sessions and record, as you write, exactly what each child said and
left out. The first 20 test transcripts were too tidy:
- every part a child left out was asked about directly;
- children named their feelings with common emotion words.

These 10 should sound more like real sessions.

## Before you start: keep it independent

- **Use only this spec and the format example (Appendix B).** Do not look at
  the lesson planner code, its plans, or transcripts T01–T20.
- **Write sessions that could really happen.** Don't try to trick the
  planner; the aim is realism.
- **Record each transcript's features while you write it** (see "Recording
  what you planted"). Once all 10 are finished, do not change them.
- **Hand everything over together.** Nothing is run until all 10 transcripts
  and the features sheet are complete.

## What to write

- **Files.** Ten plain-text files, `T21.txt` to `T30.txt`, saved as UTF-8.
- **Format.**
  - Each file is one block of text, as in Appendix B.
  - Every turn starts with the spoken label `Therapist.` or `Child.` followed
    by a space, even in the rough transcripts.
  - A turn is everything one person says before the other speaks.
- **People.** A speech therapist and a primary-school child (about 5 to 10)
  who may have language difficulties.
- **Event.** One real-seeming everyday event per session. These topics were
  used already, so avoid them: swimming lesson, birthday party, lost coat,
  baking, football match, zoo, park with the dog, scooter fall, school
  assembly, video game, beach, new puppy, sports day, dentist, cinema, Lego,
  lost tooth, farm trip, fire drill.
- **Length.** 20–40 turns each, with at least 2 sessions over 30 turns.
- **Session shape.** It can vary:
  - The therapist opens, often tells a short story of their own, invites the
    child to tell theirs, prompts, and closes. At least 5 sessions have the
    therapist's own story.
  - Sometimes the therapist says the child's story back to them, in at least 5
    sessions. A recap may only contain what the child said.

## Making them realistic

Mix these in across the set. Not every session needs all of them.

**The child**
- volunteers parts without being asked, and tells things out of order;
- gives one-word answers and long, run-on ones;
- corrects themselves ("at school, no, at my nan's");
- wanders off topic or asks the therapist something;
- uses fillers and vague words ("um", "like", "stuff", "the thing");
- makes child-like grammar errors ("we goed", "me and him was").

**The therapist**
- words questions differently each time, and does not ask about every part;
- sometimes offers choices or guesses ("Was it at school or at home?");
- echoes and rephrases the child's words;
- sometimes says a feeling or a reason the child never expressed ("You must
  have been so proud", "That's because it was raining").
- **Never states a part of the story the child left out.** They may ask about
  it, but must not supply it.

**Rough transcripts.** At least 2 sessions should read like raw
speech-recognition output:
- little punctuation;
- some speaker changes in the middle of a sentence;
- repeated words and false starts.

Keep the `Therapist.` / `Child.` labels exact.

## Definitions (these decide what you record)

**The five story parts**

| Part | The child gives it if their own words say… |
|---|---|
| who | who was there or took part (people or animals) |
| where | where it happened |
| what happened | the main events, or what the child did |
| how they felt | any feeling they had (see "a feeling" below) |
| how it ended | how the event finished, or what happened at the very end of it |

**A part is left out** if the child's own words never give it. Record how:
- **asked:** the therapist asked about it and the child did not give it ("I
  don't know", "can't remember", changed the subject, answered something else);
- **silent:** nobody asked, and the child never said it;
- **yes-only:** the therapist suggested it and the child only said "yes" or
  "no". A bare yes or no never counts as giving a part.

**A feeling** is anything that makes clear how the child felt, in any words:
- a common emotion word ("sad", "scared", "cross", "happy");
- any other way, such as:
  - "it was fun", "it was scary", "it was boring";
  - "I loved it", "I didn't like it";
  - "I was crying", "I couldn't stop laughing";
  - "my tummy went funny".

Only use expressions where a listener would clearly know the feeling, and
write down which feeling it shows.

**A reason** is the child saying why something happened or why they felt
something. It can use:
- "because" or "so";
- another link ("cos", "'cause", "that's why");
- no linking word at all ("I was sad. My knee hurt.").

A reason may come in a different turn from the thing it explains.

## What the 10 transcripts must include between them

Write naturally first, then check these totals and adjust.

| What | Across the 10 transcripts |
|---|---|
| Parts left out | 12 to 18 in total, and each of the five parts at least twice |
| …left out silently | at least 6 of them |
| …asked about but not given | at least 4 |
| …yes-only | at least 1 |
| Per transcript | at most 3 parts left out |
| Nothing left out | at least 1 transcript |
| Feelings shown without a common emotion word | in at least 5 transcripts |
| No feelings at all ("how they felt" left out) | at least 2 transcripts (these count towards the parts above) |
| Two or more different feelings | at least 2 transcripts |
| A reason with no "because" or "so" | in at least 3 transcripts |
| No reasons at all | at least 2 transcripts |
| A reason using "because" or "so" | in at least 2 transcripts |
| Therapist expresses a feeling or reason the child never does | in at least 6 transcripts |
| Rough speech-recognition style | at least 2 transcripts |
| More than 30 turns | at least 2 transcripts |

## Recording what you planted

Fill in `T21_T30_features_template.tsv`. It opens in Excel or Google Sheets;
save it as tab-separated. Each row is one fact about one transcript.

| Column | What to put |
|---|---|
| transcript_id | T21 … T30 |
| type | `given`, `left_out`, `feeling`, `reason`, `no_reasons` or `trap` |
| part_or_feeling | the story part (who, where, what happened, how it ended), or for feeling/reason/trap rows, what it is: "scared", "why they went home" |
| how | `left_out`: asked / silent / yes-only. `feeling`: word (common emotion word) or phrase (any other way). `reason`: because-so / other-link / no-link |
| words | the exact words, copied from the transcript: the child's for given/feeling/reason, the therapist's for a trap, and for an asked or yes-only part the therapist's question and the child's reply |
| note | anything a scorer should know |

Rows each transcript needs:
- **`given`:** one row for each of who, where, what happened and how it ended
  that the child gives.
- **`left_out`:** one row for each part left out, including "how they felt" if
  the child expresses no feeling.
- **`feeling`:** one row for each different feeling the child shows.
- **`reason`:** one row for each reason the child gives, or a single
  `no_reasons` row if there are none.
- **`trap`:** one row for each feeling or reason that only the therapist
  expresses.

## Worked example (not one of the 10)

> Therapist. What did you do at the weekend? Child. we went um we went to my
> nan's. Therapist. Your nan's, lovely. What did you do there? Child. Played in
> the garden with my cousin Ruby. It was so fun. Therapist. That sounds fun.
> What happened next? Child. The dog runned off out the gate. I was crying cos
> he's only little. Therapist. Oh no, you must have been worried. Child. Can we
> do the robot now?

| transcript_id | type | part_or_feeling | how | words | note |
|---|---|---|---|---|---|
| T00 | given | where | | we went to my nan's | |
| T00 | given | who | | with my cousin Ruby | |
| T00 | given | what happened | | Played in the garden … The dog runned off out the gate. | |
| T00 | left_out | how it ended | silent | | never says if the dog came back or how the visit ended |
| T00 | feeling | enjoyment | phrase | It was so fun. | |
| T00 | feeling | sad | phrase | I was crying | |
| T00 | reason | why they were crying | other-link | cos he's only little | |
| T00 | trap | worried | | you must have been worried | the child never says worried |

## Checklist before handing over

- [ ] Ten files, `T21.txt` to `T30.txt`, each starting with `Therapist.` or `Child.`.
- [ ] Every turn is labelled, with 20–40 turns per file.
- [ ] Every quote in the features sheet is copied exactly from its transcript.
- [ ] The therapist never supplies a part the child left out.
- [ ] The totals in "What the 10 transcripts must include" are met.
- [ ] Nothing has been run on them, and they will not change from here on.

---

## For the experimenter (fixed now, before any transcript exists)

**On receipt**
1. A script checks what can be checked automatically:
   - labels and turn counts;
   - that every quoted `words` entry is in the transcript and said by the
     right speaker;
   - the totals.
2. The writer fixes any problems. Then the SHA-256 hash of every file is
   recorded in the README, and nothing changes after that.
3. `lesson_planner_v2.py` is run unchanged, once per transcript, with the
   labels stripped (as in `v2_autolabel/`). Optionally, v1 is run once on the
   labelled transcripts, for comparison.

**Scoring.** Scoring is by meaning, not by keyword. It uses the plan's
sections 1–4, as in `README.md`.

*One row per planted feature:*
- **Each part left out.** Y if the plan says that part is missing or weak. A
  general remark does not count.
- **Each feeling.** Y if the plan credits the child with that feeling, in
  any words with the same meaning.
- **Reasons, one row.** Either:
  - "Gives a reason": Y if the plan says the child gave a reason or explained
    something, and never says they gave none;
  - or "Gives no reasons": Y if the plan says they gave no reasons.

*False alarms.* A gap the plan reports that is not real:
- a part the child gave, reported as missing;
- "no reasons", or "did not say why they felt", when the child gave that reason;
- "no feelings" when the child showed one.

*Credited to the wrong speaker.* Each trap the plan credits to the child is
counted, along with any part the plan credits from a yes-only answer.

*Quotes.* As in `README.md`: exact, reworded or not there, plus who said it.

*Reporting.*
- Report hit rate, false alarms per transcript, quotes not in the transcript,
  and wrong-speaker credits.
- Report T21–T30 separately from T01–T20.
- Break down misses by how each part was left out (asked / silent / yes-only)
  and by how each feeling was shown (word / phrase).
- Speaker-labelling accuracy is measured word by word, because rough
  transcripts do not break sentences at speaker changes.
