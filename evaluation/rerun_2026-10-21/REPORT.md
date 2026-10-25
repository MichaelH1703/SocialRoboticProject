# Test 6 (NFR3) re-run of lesson planner v1 and v2 — 21 October 2026

Everything here is new; nothing outside this folder was written. The planners, transcripts, truth sheets,
scorer and the v3 results are unchanged (SHA-256 checked before and after; see `run_log.md`).

## Figures by set

| Set | v1 hit rate | v1 FA / transcript | v2 hit rate | v2 FA / transcript | v3 (existing sheet) |
|---|---|---|---|---|---|
| T01–T10 | 0.73 (27/37) | 0.7 (7) | 0.95 (35/37) | 0.3 (3) | 0.95 / 0.3 |
| T11–T20 | 0.64 (23/36) | 1.1 (11) | 0.97 (35/36) | 0.4 (4) | 0.94 / 0.5 |
| T21–T30 | 0.64 (25/39) | 0.2 (2) | 0.62 (24/39) | 0.6 (6) | 0.69 / 0.2 |
| T31–T60 | 0.83 (57/69) | 0.5 (14) | 0.51 (35/69) | 1.5 (46) | 0.86 / 0.7 |
| All 60 | 0.73 (132/181) | 0.6 (34) | 0.71 (129/181) | 1.0 (59) | 0.86 / 0.5 |

Quotes not in transcript (provisional until the manual check): v1 8 of 110 (T01–T10: 1 of 25); v2 5 of 395.
Precision: v1 79.5%, v2 68.6%. Feelings shown without a feeling word, found: v1 27/30 (T31–T60 16/18),
v2 1/30 (T31–T60 1/18). Therapist traps credited to the child: v2 7/35 on T21–T60 (scorer); v1 29 noted by
reading across all 60 (`v1_scoring.tsv`, last column).

## Against the draft thesis

| Figure | Thesis | Re-run | Same? |
|---|---|---|---|
| v1 T01–T10 hit rate | 0.73 (27/37) | 0.73 (27/37) | yes (but 4 features changed result, cancelling out) |
| v1 T01–T10 false alarms | 1.1 per transcript | 0.7 (7) | **no** |
| v1 T01–T10 quotes not there | 1 of 27 | 1 of 25 (provisional) | **no** (count of quotes differs) |
| v1 "uses neither because nor so" | 0 of 4 | 0 of 4 | yes |
| v2 T01–T10 | 0.95 / 0.3 | 0.95 / 0.3 | yes |
| v2 T11–T20 | 0.97 (35/36) / 0.4 | 0.97 (35/36) / 0.4 | yes |
| v2 T21–T30 | hand 0.69 (27/39) / 0.5; automatic 0.62 / 0.6 | 0.62 (24/39) / 0.6 | matches automatic; the hand figure is a different scorer |
| v2 T31–T60 | hand 0.54 (37/69) / 1.5; automatic 0.51 / 1.5 | 0.51 (35/69) / 1.5 | matches automatic; the hand figure is a different scorer |
| v2 T31–T60 feelings without an emotion word | 1 of 18 | 1 of 18 | yes |

v2 reproduced the original run byte for byte on 59 of 60 transcripts (`compare_with_original.md`). T01 differs:
two sentences were auto-labelled differently on the first call of the run, which changed the summary and one
quote but not T01's score. v1 (no seed set in the file) produced new text, as expected; on T01–T10 the changed
results are T02 ending (hit→miss), T06 "because" (miss→hit), T09 ending (miss→hit), T10 who (hit→miss).

## Not done automatically, and deviations

- **v1 was scored by reading, not by compare.py**, because v1 writes free text that compare.py cannot read.
  Same truth sheets and rules; 62 judgement calls are listed in `needs_manual_check.md`.
- **36 quotes need a manual check** (29 v1, 7 v2), listed in `needs_manual_check.md` with the closest turn.
  16 of the v1 ones are provisionally *excluded* as proposals (questions, section-5 suggestions) rather than
  the child's words. The workbook cells carry a comment saying "Provisional".
- **Formula range.** In the template, C13 (false alarms per transcript) counts rows 17–228 while C12/C15 count
  17–258. Here all three use 17–258, otherwise v2's rows 229–240 would be left out.
- **The by-set table is in G11:N16**, beside the Results block, so that no template row moves.
- **The existing V3 sheet's quotes table is truncated:** it stops at 500 rows (rows 267–766), so the last 17 v3
  quotes (7 from T59, all 10 from T60) are missing, and 17 long quotes are cut to 300 characters. It was left as is.
- No runs failed; no hash mismatches.

## Files

- `v1/T##_plan.md`, `v2/T##_plan.md`, `v2/T##_analysis.json`, `v2/unlabelled/T##.txt`: raw outputs.
- `run_log.md`: environment, `ollama list` and digests, SHA-256 of every input, start/end per transcript.
- `NFR3_v1_v2_rerun.xlsx`: sheets `NFR3 Version 1`, `NFR3 Version 2`, `NFR3 Version comparison`.
- `v1_scoring.tsv` (hand scores with evidence), `v1_features.tsv`, `v2_features.tsv`, `v1_quotes.tsv`,
  `v2_quotes.tsv`, `by_set.tsv`, `scoring_summary.md`, `needs_manual_check.md`, `compare_with_original.md`.
- Scripts: `write_header.py`, `run_rerun.py`, `scorer_loader.py` (loads compare.py's rules without running its
  file-writing part), `score_rerun.py`, `check_v1_planted.py`, `compare_with_original.py`,
  `build_workbook.py` (needs openpyxl).
