# Test 6 with lesson planner v2 – speaker labels added automatically

The planted features (`../features.json`) and scoring rules (`../README.md`)
are the same as in the v1 run. Three things change:

- **The generator** is `lesson_planner_v2.py` (qwen3:8b).
- **Speaker labels:** the "Therapist." / "Child." labels are removed before
  the transcript is given to v2, since real session transcripts have none. v2
  labels each sentence itself. Scoring still uses the original labelled
  transcript as the truth.
- **Twenty transcripts.** T01–T10 are the v1 set. T11–T20 are a held-out set
  written to the same specification.

## History

1. **v2 with auto-labelling, run on T01–T10.** Results:
   - hit rate 0.89;
   - 0.4 false alarms per transcript;
   - 0 quotes that are not in the transcript.

   It took the child's last event as the ending when the child could not say
   how it ended (T05, T09). It also missed a real ending (T10).
2. **T11–T20 written and frozen.** Their planted features were added to
   `features.json`, and `check_transcripts.py` passes. None of them had been
   run through any generator at this point.
3. **The ending check was fixed, using T01–T10 only:**
   - The ending no longer means "the last thing that happened".
   - A rule in code was added: if the therapist later asked how it ended and
     the child said they did not know, the earlier words were not the ending.
   - The second look now shows the therapist's question before each child turn.

   It was checked on T05, T09 and T10, which are development transcripts.
4. **Final run of the fixed v2, once, on all 20.** Every row in the results
   comes from this run.

## Progress (resume from the first unchecked step)

- [x] 1. `run_v2.py` on T01–T20, with labels stripped (`unlabelled/`, `analysis/`, `plans/`, `run_log.txt`)
- [x] 2. `label_accuracy.py`: auto labels against the true labels (`label_accuracy.txt`)
- [x] 3. `score_auto.py` proposes scores; checked by hand into `scoring.tsv` and `quotes.tsv`
- [x] 4. `finalise.py`: paste-ready tables in `results/`

## Two scoring decisions (v2's plan has lines v1's never had)

- **"Did not say why they felt that way."** (section 4) is treated as a
  "missing reasons" claim. It counts as a false alarm when the child gave a
  reason for a feeling:
  - they said what caused it, in the same turn as the feeling word;
  - or they described the cause in the turn just before naming the feeling,
    when asked how it felt.

  This is how v1's T03 was scored. It also matches the fixed rule that a
  missing-reasons claim is a false alarm when the child used "because"/"so".
  In all six cases (T01, T03, T09, T11, T15, T16) both held. v2 only looks for
  a reason in the same turn as the feeling word.
- **The words in `Did not give any reasons (no "because" or "so")`** are not
  counted as quotes. They name words the child did not say; they are not
  offered as something said in the session.

## Caveats for the write-up

- **T01–T10 are not held out.**
  - T06 and T08 were used while v2 was developed.
  - All ten were used in a trial of the labelling prompt, and the echo rule
    was added after seeing its errors there.
  - The ending fix was made from T05, T09 and T10.

  Report T11–T20 as the main result.
- **The same author wrote all 20 transcripts and the planner.** T11–T20 follow
  the same specification and were frozen before the fix, but they are not
  independent of someone who knew v2's weak points.
- **The transcripts are written, not transcribed speech.** Every speaker
  change falls at a sentence break and the punctuation is perfect, so
  labelling accuracy here is an upper bound for real recordings.
