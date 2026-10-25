# Test 6, held-out set T21–T30 – lesson planner v2, labels added automatically

These transcripts were written to `../T21_T30_spec.md`, outside the sessions in
which the planner was developed, and supplied from
`SelfDoneEval/Test6-21-30/`. The planted features are in
`../T21_T30_features.tsv`. The scoring rules are in the spec's "For the
experimenter" section. They are by meaning, not by keyword, and were fixed
before any transcript existed.

## Progress (resume from the first unchecked step)

- [x] 1. `../check_T21_T30.py` passes, and all spec totals are met
- [x] 2. Frozen: SHA-256 of the 10 transcripts, the features sheet and `lesson_planner_v2.py` in `sha256_frozen.txt`
- [x] 3. `run_v2.py`: v2 run unchanged, once per transcript, with labels stripped (`unlabelled/`, `analysis/`, `plans/`, `run_log.txt`)
- [x] 4. `label_accuracy.py`: auto labels against the true labels, word by word (`label_accuracy.txt`)
- [x] 5. Scoring by hand into `scoring.tsv` and `quotes.tsv`
- [x] 6. `finalise.py`: paste-ready tables in `results/`

## Notes

- **One deviation from the spec.** In T24 the therapist opens with "I heard
  your class went somewhere special". That states the "who" the child leaves
  out (yes-only). The child still never names anyone, so the planted feature
  stands. If a plan credits "class" to the child, it counts as a
  wrong-speaker credit.
- **The spec names the kinds of case it wants,** such as silent omissions and
  feelings not stated with an emotion word. These were chosen after seeing
  v2's weak points on T01–T20. That makes this set harder than T01–T20, but
  not a random sample of real sessions.
