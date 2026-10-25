# Test 4, run 4 – you play April, blind, 4 April contexts (H11–H50)

40 sessions you type as April: 20 "with" context and 20 "without" (the blank April),
in a hidden order. The "with" sessions use 4 different April contexts, 5 sessions
each (`versions.json`):

| Version | Therapist account | Context |
|---|---|---|
| v1 | eval-test@reachy.local | April's profile and lesson plan from runs 1–3 (unchanged; the profile says DLD) |
| v2 | eval-test-v2@reachy.local | Football, literal language, one question at a time |
| v3 | eval-test-v3@reachy.local | Minecraft, short sentences and everyday words |
| v4 | eval-test-v4@reachy.local | Swimming, specific praise, comments between questions |

v2–v4 are autistic in their profiles. Their lesson plans were generated once by
`lesson_planner.py` from their recap transcripts, as v1's was, and used as-is
(`lesson_plan_v2.txt`…). v3's plan adds a detail that isn't in its transcript
(April confused about whether Peanut was fed); that is the planner's own output.

The session itself is run 3's (`../run3_human/play.py`, reused unchanged): you see
only Reachy's spoken lines, slash commands are off, and the condition is never shown.

**Do not open `_unblinding/` until the coding and ratings are done.**

## Design (fixed 2026-10-16, before any session)

- Order: 10 blocks of 4 (2 with + 2 without), each shuffled; versions 5 each,
  shuffled; seed 9. Checked blind: every block is 2 + 2, every version is used 5
  times, and turns 6–10 are each used 4 times per condition.
- "I don't know" reminders: turns 6–10, each 4 times per condition.
- Before every session: April's database rows (every therapist's April) must
  match the snapshot taken before the first session, and `reachy_text_chat.py`
  and `reachy_safety.py` must be unchanged. If either has changed, nothing runs.
- Isolation: models unloaded, fresh process, Reachy's model warmed up, database
  snapshot before and after the run (`isolation_check.txt`).
- An abandoned session (Ctrl+C) is replayed under the same ID and condition:
  recorded in `attempts.tsv` and in `guesses.tsv`'s `abandoned_attempts`.

## Database changes (approved 2026-10-16, by `setup_versions.py`)

- Removed the 4 event-title rows ("Played netball in PE", "Made pasta in food
  tech") re-added on 12 Oct at 14:32, after run 3, so both original Aprils are
  back to run 3's 3 titles. Saved in `removed_titles.json`; `restore_titles.sql`
  puts them back.
- Added v2–v4 (rows in `setup_rows.json`); `cleanup.sql` removes them.
- April has 62 conversation-log rows and 2 safety events that weren't there in
  run 3 (from another test). Reachy doesn't read them, and they are in the
  snapshot, so any change during the run will be caught.

## How to play

From the project folder, once per session:

```
venv/Scripts/python.exe eval/test4_personalisation/run4_human/play.py
```

## Progress

- [x] 1. Database checked and set up (`setup_versions.py`). The blank April's
      prompt is identical to run 1's, and v1's matches the database's run-1 profile.
- [x] 2. Dry run (`python play.py dryrun`): one
      abandoned attempt, then a full session. Every output file checked.
- [x] 3. Hidden schedule made (`python play.py setup`).
- [x] 4. **You:** play H11–H50 (`guesses.tsv` shows how far you are).
      H14 and H15 were reset at your request on 2026-10-16 15:04 and played again
      under the same IDs and conditions. Their first plays are kept as
      `_unblinding/raw/H1x.reset-*.txt`, and their first guesses in `resets.tsv`.
- [x] 5. Blind materials built (`python analyse_run4.py`, seed 10). All 40 played,
      database unchanged (`isolation_check.txt`); 30 of 40 ended with `/end`.
      - Coding: 50 transcripts S41–S90 (H11–H50 plus run 3's H01–H10, so the pooled
        50 share Q1/Q2), each with its lesson focus and style checklist on top.
        "Without" sessions are shown with a version assigned for coding (5 per
        version, seed 10); run 3's with v1.
      - Ratings: 40 replies R161–R200, 1 per run 4 session (20 per condition).
- [x] 6. **You:** `python code_sessions.py` (Q1/Q2, saves as you go), and rate
      `blind_replies.tsv` into `blind_replies_rated.tsv`. **LLM:** `llm_coding_prompt.md`
      + `blind_sessions/` into `blind_session_coding_llm.tsv`; `llm_rating_prompt.md`
      (add your rubric) + `blind_replies.tsv` into `blind_replies_rated_llm.tsv`.
- [x] 7. Un-blinded 2026-10-16 (`python finalise_run4.py`). Q1/Q2 were coded by the LLM
      only (merged into `blind_session_coding_llm.tsv`); ratings by you and the LLM.
      `results/`: `sessions_H11-H50.tsv` (sheet A28), `blind_human.tsv` (A113),
      `blind_llm.tsv` (H113)
