# Test 6 – lesson planner v3 on all 60 transcripts

`lesson_planner_v3.py` fixes three weaknesses that Test 6 found in v2 on
realistic transcripts (T21–T60). v2 itself is unchanged, and its hash matches
every earlier run.

| Weakness in v2 | v3 |
|---|---|
| Feelings came from a word list, so "it was so fun" and "my stomach went all tight" were missed and the plan said "Did not name any feelings" | Feelings are found by meaning and verified like story parts (the young person's own words, plus a focused check). Whether they used a feeling word is reported separately: "Showed how they felt, but did not name the feeling". |
| Reasons came from "because"/"so", so "I'd done the work. It was just the upload." was missed | Reasons are found by meaning and verified. The check must say what the reason explains, or answer "nothing". Whether they linked a reason with "because"/"so" is reported separately. |
| Speakers were labelled a sentence at a time: unpunctuated transcripts became one "sentence", and the therapist's opening story was given to the young person | Text with little punctuation is first split into pieces by the model, which copies the words; the copy is lined up word by word with the original. The labelling prompt describes the therapist's opening story, with a short generic example. |

Also added: a cap on reply length, and timeouts treated as an empty answer.
One call (T39's feelings) got stuck repeating itself and stopped the first run.

## How v3 was developed (these numbers are not held-out)

- **The fixes were designed after reading v2's failures on T21–T60.** These
  transcripts were used directly while developing v3:
  - T01, T21, T24, T28, T36 and T48 (first check);
  - T34, T39, T46, T51, T53, T56, T57 and T59 (labelling check);
  - T26, T30, T31, T32, T34, T37, T47, T48, T50, T53, T54 and T57 (reasons
    check).
- **One idea was dropped.** Labelling speaker by turn made the model assume
  strict turn-taking, which put tidy transcripts out by one label.
- **The first full run was replaced.** It showed the reason
  check accepting plain answers ("The chippy", "Dad") as reasons, so the check
  was tightened and everything was rerun with the final version
  (`sha256_planner.txt`).

So v3's figures here show whether the fixes work on the cases that prompted
them. They are not an unbiased estimate. A fresh set written after v3 was
frozen is needed for that.

## Scoring

`compare.py` scores v2 and v3 with the same automatic rules (written at the
top of the file). On v2 it reproduces the hand scores:
- T01–T10: hand 0.95 / 0.3, automatic 0.95 / 0.3.
- T11–T20: hand 0.97 / 0.4, automatic 0.97 / 0.4.
- T21–T30: hand 0.69 / 0.5, automatic 0.62 / 0.6.
- T31–T60: hand 0.54 / 1.5, automatic 0.51 / 1.5.

The small gaps are feelings credited from the summary, which the automatic
rules do not read. Output: `compare.md`, and every row in `compare_detail.tsv`.

## Files

- `run_v3.py`: one run per transcript, labels stripped (`unlabelled/`, `analysis/`, `plans/`, `run_log.txt`)
- `compare.py`: v2 and v3 scored side by side
