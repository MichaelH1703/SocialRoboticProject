# Test 4, run 3 – you play April, blind (H01–H10)

You type April's replies in 10 sessions: 5 with April's context and 5 without,
in a hidden random order. Same robot code, prompts and database as runs 1 and 2
(`reachy_text_chat.py` unchanged, saving off). `play.py` takes each session's
condition from `_unblinding/schedule.json` and never shows it. You see only
Reachy's spoken lines. Everything else goes to the hidden raw logs.

This is a different method from runs 1 and 2 (a person, not the simulated
child, and the fact sheet is followed loosely), so report it separately rather
than pooled.

**Do not open `_unblinding/` until the ratings and coding are done.**

## Design (fixed 2026-10-12, before any session)

- 10 sessions, H01–H10: 5 W, 5 B, order shuffled (seed in the hidden schedule).
- Forced "I don't know": turns 6–10 once per condition, so the reminder's turn
  says nothing about the condition. `play.py` reminds you on that turn, and at
  turn 13 says it's time to say "Bye." and "No.".
- Isolation as run 2: prompts checked against run 1's before every session,
  models unloaded, fresh process, database snapshot before and after.
- After each session you guess the condition (`guesses.tsv`), to measure how
  blind you stayed.
- Ratings: you and an LLM both rate the same blind replies (4 per session, 40 in
  all, R121–R160). Sessions are relabelled S31–S40 for coding.

## How to play

In a terminal, from the project folder, once per session:

```
venv\Scripts\python.exe eval\test4_personalisation\run3_human\play.py
```

It shows April's fact sheet, then the session. `/end` stops a session early
(it still counts). Ctrl+C abandons it, and it is offered again next time.

## Progress

- [x] 1. `play.py` built and smoke-tested (a throwaway session, outside the schedule).
- [x] 2. Hidden schedule made (`python play.py setup`).
- [x] 3. **You:** play H01–H10 (`guesses.tsv` shows how far you are). Done 2026-10-12;
      database unchanged (`isolation_check.txt`). H02, H04 and H06 were each abandoned
      once and replayed (`_unblinding/raw/*.aborted-*.txt`), so you saw part of a
      session in that condition before playing it. 6 of 10 sessions ended with `/end`.
- [x] 4. Build the blind materials: `python analyse_run3.py` (sampling seed 8).
- [x] 5. **You** rate the replies; the **LLM** rates them too (its prompt needs your
      sheet's 1–5 definitions for responsive, clear, technique, no_invention).
- [x] 6. Code the sessions (`../run2/llm_coding_prompt.md`, and/or you).
- [x] 7. Say "unblind": results, the agreement between you and the LLM, and how
      often your guesses were right.

## Results (un-blinded 2026-10-12)

the `.tsv` files are paste-ready
(`_llm` = the LLM's ratings). Your guesses were right 3 times out of 8 (2 unsure),
so the blinding held. "I don't know" was said in 7 of 10 sessions, not always on
the reminded turn, as expected with the fact sheet followed loosely.
