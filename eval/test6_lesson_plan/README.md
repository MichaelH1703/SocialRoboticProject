# Test 6 – Lesson plan accuracy

Does the transcript analysis (`lesson_planner.py`, qwen2.5:3b, unchanged) report
what is really in a transcript, and only that?

## Progress (updated after each chunk; resume from the first unchecked step)

- [x] Chunk 1a: planted features (`features.json`) and scoring rules (below), fixed before any run
- [x] Chunk 1b: transcripts T01–T05 written (`transcripts/`)
- [x] Chunk 2: transcripts T06–T10 written; `check_transcripts.py` passes for all 10
- [x] Chunk 3: each transcript run through the generator once (`run_generator.py`, outputs in `plans/`)
- [x] Chunk 4: scoring (`scoring.tsv`, `quotes.tsv`) and paste-ready tables (`results/`)

**Later addition.** T11–T20 were added as a held-out set for testing
lesson planner v2; see `v2_autolabel/README.md`. The v1 results here cover
T01–T10 only.

## Transcripts

Ten practice transcripts in the style of Appendix B: one continuous block with
spoken "Therapist." / "Child." labels. The therapist tells a short story of her
own first, then the child recounts with prompts, then she says the story back
and closes. Each has 20–30 turns (labelled segments).

The planted features are in `features.json`:
- story parts the child leaves out;
- whether the child uses "because" or "so";
- every emotion word the child uses.

Unlike Appendix B, the therapist never supplies a story part the child left
out, so a planted gap really is a gap. She does deliberately use "because",
"so" and emotion words of her own (`therapist_traps`), to test whether the
analysis credits her words to the child.

`check_transcripts.py` checks each transcript against its planted features
automatically: the child's linking words, the child's emotion words, and the
turn count. Story-part omissions were checked by reading.

## Scoring rules (fixed before any run)

**Rows in the top table, one per planted feature:**
- each story part the child leaves out;
- one row for "because"/"so" (for example "uses 'because'", or "uses neither 'because' nor 'so'");
- one row per emotion word the child uses, or one row "uses no emotion words".

**Which part of the plan counts.** Hits and false alarms are judged on sections
1–4 (what the analysis says about the child). Section 5, Recommended Future
Lesson Focus, is a plan, not a finding, so it is not used for either. This
clarification was added when scoring began. No T01–T05 score depended on it.

**Reported (Y/N):**
- **Omitted story part.** Y only if the analysis names that specific part
  as missing or weak. For example, "did not say where it happened" or "no
  setting" for *where*, and "no ending" for *how it ended*. A general remark
  like "incomplete description of events" is N.
- **"because"/"so".**
  - *The child uses it:* Y if the analysis says the child gave a reason, or
    used "because"/"so" or linking language, and does not say the opposite.
  - *The child uses neither:* Y if the analysis says the child did not explain
    why, or lacks causal or linking words.
- **Emotion word X.** Y if the analysis names X as a feeling the child expressed.
- **"Uses no emotion words".** Y if the analysis says the child did not
  name or explain their feelings.

**Hit / miss.** A planted feature reported is a hit; not reported is a miss.

**False alarm.** A gap the analysis reports that was not planted, counted only
within the three planted categories:
- a story part the child did give;
- missing reasons or linking words when the child used "because"/"so";
- missing emotion words when the child used some.

Each false alarm is its own row with planted = N. Gaps outside these categories
(such as sentence length or vocabulary) are listed in `notes` and not counted,
because the test did not plant them.

**Credit to the wrong speaker.** Where the analysis credits one of the
therapist's trap words to the child (for example, says the child felt
"frustrated" when only the therapist said it), this is noted in `notes`.

**Quotes (bottom table).** Every piece of text the analysis puts in
quotation marks as something said in the session goes in the bottom table.
The "Suggested Reachy Prompts" section is excluded, because those are proposals,
not quotes. Each quote is marked:
- **exact:** it appears word for word, ignoring case and punctuation;
- **reworded:** the same thing was said in different words;
- **not there.**

Who actually said it is noted.

**Results.**
- Hit rate = hits ÷ planted features.
- False alarms per transcript = false alarms ÷ 10.
- Quotes not in transcript = count of "not there".
