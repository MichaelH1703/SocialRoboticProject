# Test 3 – Reply quality

Ten sessions run through `reachy_text_chat.py` (unchanged, saving off) as
client A, April, with her full context (the same database rows as Test 4's
"with" condition). There are five events, her five event titles, each run
twice. **100 replies** are rated, 10 per session.

| Story | Event title | Sessions |
|---|---|---|
| bowl | Went bowling for Mia's birthday | bowl-1, bowl-2 |
| sci | Had a science test | sci-1, sci-2 |
| fire | Fire drill at school | fire-1, fire-2 |
| net | Played netball in PE | net-1, net-2 |
| pasta | Made pasta in food tech | pasta-1, pasta-2 |

The run order puts the two runs of each story five sessions apart:
bowl-1, sci-1, fire-1, net-1, pasta-1, then bowl-2 … pasta-2.

April's 4th and 5th event titles were added for this test (`add_event_titles.py`),
to both Aprils so they stay identical apart from their context.

## Every session is independent

- **New process:** each session runs in a brand-new process, with a new
  `TextSession` and empty histories. Its raw log starts with an
  `[Isolation]` line showing the process id, empty histories and no model
  loaded.
- **Models unloaded:** before every session, every model is unloaded from
  Ollama, and the runner waits until Ollama reports none loaded. Nothing
  cached from one conversation can reach the next.
- **Nothing saved:** saving is off. April's rows in every table the robot reads
  or writes are snapshotted before and after the whole run.
  `isolation_check.txt` records all of this, ending with "Unchanged by the run".

A session's only inputs are April's database context (fixed), the story's fact
sheet, and its own conversation.

## How the child works

April is played by the same simulated child as Test 4 (`../simulated_child.py`,
llama3.2:3b), with a fact sheet per event. The bowling fact sheet is Test 4's,
word for word. Every session has the same shape:
- a fixed opening that picks the event;
- 11 generated answers, one of which is a forced "I don't know" given in answer
  to a question;
- "Bye." and "No." to end.

10 replies per session were picked with a fixed seed and kept in conversation
order. Only model replies the child heard can be picked: not the greeting,
the goodbye lines or other scripted lines.

**How the run went.** All 10 sessions completed, with 12 model replies each.
There were no errors, slow replies or safety replacements. Four of April's
lines needed regenerating for being too long. Once, in pasta-2 turn 3, every
attempt was too long and April said the fallback "Can't remember.". She gave
the detail on her next turn.

**Small slips by the simulated child, kept as they are.**
- sci-2: "Did my homework." is not on her fact sheet.
- bowl-1: "Mia's mum brought out pizza." On her sheet it was the cake.

No session was rerun: choosing which sessions to keep after seeing them would
bias the result. Reachy's replies still respond to what April actually said,
so rate them against her words.

An earlier 6-session run (3 stories) was replaced by this one. It was not rated.

**Not possible from a text run:** the phone recordings the protocol asks for
(reused in Test D).

## Your part

1. Clear the score columns of the Test 3 table, and add rows up to 100 if the
   sheet stops at 60.
2. Open `sheet_rows.tsv` in Notepad, press Ctrl+A and Ctrl+C, click the
   `session_id` cell of row 1, and press Ctrl+V. That fills session_id,
   child_said and reachy_said for rows 1–100.
3. Score responsive, clear, technique and no_invention, mark harm Y/N, and add
   notes. For context, open `sessions/<session_id>.txt` and find `(reply N)`.
4. Send the scores back. `python analyse.py results` then builds the
   Results row from them, saved as `ratings.tsv`.

## Cleanup

`cleanup.sql` removes the two added event titles. Run it before Test 4's
`cleanup.sql`.

## Files

| File | What it is |
|---|---|
| `materials.json` | Fact sheets, settings, run order, seeds |
| `add_event_titles.py` | Added April's 4th and 5th event titles (ids in `test3_rows.json`) |
| `run_sessions.py` | Runs the 10 sessions, with the isolation steps |
| `isolation_check.txt` | Proof of isolation: per-session unloads and the database before/after |
| `analyse.py` | Builds the sheet rows and transcripts; `results` builds the Results row |
| `sheet_rows.tsv` | Paste-ready for the sheet (100 rows, no header) |
| `replies.tsv` | The same 100 replies with reply_id and turn number |
| `sessions/` | Readable transcripts, with the rated replies marked |
| `session_stats.tsv` | Per-session counts |
| `raw/` | Full console output of every session |
