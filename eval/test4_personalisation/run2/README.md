# Test 4, run 2 – ten more pairs (W6–W15, B6–B15)

Extends Test 4 (`../README.md`) from 5 to 15 sessions per condition, so the new
20 and the pooled 30 can be reported. Same code, prompts and materials as run 1
(`reachy_text_chat.py` and `../materials.json` unchanged; both system prompts
checked byte-identical to run 1's before running).

## What differs from run 1 (fixed 2026-10-12, before any session)

- **Seeds:** the child's seed is the pair number (6–15), as in run 1 (1–5). The
  reply sampling and shuffling seed is 6 (run 1: 4). All in `settings.json`.
- **Paired "I don't know" turn.** In run 1 it landed at turn 6 in 4 of 5 W
  sessions and turn 10 in 4 of 5 B sessions. Here Wn and Bn share the child's
  seed *and* the turn, which is forced at exactly that turn in both sessions.
  The turns 6–10 are each used for 2 pairs, in an order shuffled with seed 6:
  6→6, 7→9, 8→9, 9→10, 10→6, 11→8, 12→7, 13→8, 14→7, 15→10.
  The raw logs record whether Reachy's line before it asked a question. In run 1,
  that line was a question 47 times out of 50 at turns 6–10.
- **Isolation, as Test 3's runner did it:** every Ollama model is unloaded before each
  session. Each session warms Reachy's model up first, as `reachy_text_chat.py`'s
  main does. April's rows are snapshotted before and after the run
  (`isolation_check.txt`). Run 1's runner used a fresh process only.
- **Blind IDs continue from run 1:** replies R41–R120, sessions S11–S30.

## Database

Before run 2, the database had moved on from run 1. April's profile had Test B's
canary sentence ("She has a pet axolotl called Biscuit."), and both Aprils had
Test 3's 4th and 5th event titles. With your approval, `db_restore.sql`
removed them (applied 2026-10-12). `db_undo.sql` puts them back exactly.
Test B's own `cleanup.sql` and Test 3's `cleanup.sql` still work afterwards; for
these rows they now do nothing.

## Progress

- [x] 1. Database restored to run 1's state (`db_restore.sql`); both prompts
      identical to run 1's (`_unblinding/prompt_*.txt`).
- [x] 2. Run the 20 sessions: `python run_pairs.py run` (from this folder, with
      the venv's Python). It resumes: finished sessions are skipped.
- [x] 3. Build the blind materials: `python analyse_run2.py`. All 20 complete, database unchanged (`isolation_check.txt`), "I don't know" turn matched in every pair; in 7 of 20 sessions Reachy's line before it was not a question.
- [x] 4. **You:** rate `blind_replies.tsv` (80 replies, R41–R120) into
      `blind_replies_rated.tsv` (columns `blind_id responsive clear technique
      no_invention`, 1–5 on the Test 3 scale, as in run 1).
- [x] 5. **You:** code `blind_sessions/S11–S30.txt` into `blind_session_coding.tsv`
      (`../criteria.md`).
- [x] 6. Say "unblind": `python finalise_run2.py` writes `results/` (new 20 and pooled 30).

**Do not open `_unblinding/` until steps 4 and 5 are done.**

## Files

| File | What it is |
|---|---|
| `settings.json` | Seeds, "I don't know" turns, run order, sampling settings |
| `run_pairs.py` | `check` compares prompts with run 1's; `run` runs the sessions |
| `db_restore.sql`, `db_undo.sql` | The pre-run database change and its undo |
| `snapshot_before.json`, `isolation_log.txt`, `isolation_check.txt` | Isolation evidence |
| `_unblinding/raw/` | Full console output of every session |

## Results (un-blinded 2026-10-12)

`results/summary.md` has every number and test, for the new 20 and the pooled 30.
The `.tsv` files are paste-ready for the sheet (no header rows, as in run 1).
Checks made after un-blinding:
- The keyword check flagged 2 "with" replies (both in W6). Both say "ride home", which
  is the drive home from the fact sheet, so the N coding stands.
- The forced "I don't know" followed a non-question in 6 of the 10 W sessions but
  only 1 of the 10 B sessions. The turn is paired; what Reachy said just before it is not.
