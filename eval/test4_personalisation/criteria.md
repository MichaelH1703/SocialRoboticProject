# Test 4 – coding rules (fixed before any session was run)

Written 2026-10-10, after April's lesson plan was generated (`lesson_plan.txt`) and
before any Test 4 session was run. Apply them blind, to the unlabelled
transcripts in `blind_sessions/`.

Amended 2026-10-10, before the simulated-child runs: the first runs used a
fixed child script and were discarded, because
the child's lines did not answer Reachy's questions. The only change here is
that the "not counted" list for profile details now covers everything on the
simulated April's fact sheet.

Only **model replies the child heard** are coded: not the greeting, the goodbye
lines, safety lines, or the `[Not spoken]` replies (those are already removed
from the blind transcripts).

## followed_lesson_focus (Y/N)

The lesson plan's "Recommended Future Lesson Focus" asks for (1) logical
explanations, (2) more precise emotion words, and (3) understanding others'
perspectives. The session note's target is the same as (1): using "because".

**Y** if at least one Reachy reply in the session does any of these:

- **(a) Explanation** – asks *why* something happened or why April felt
  something, or otherwise asks for a reason ("What made you nervous?",
  "Why do you think…?", "…because…?").
- **(b) Perspective** – asks how another person felt or what they thought
  ("How do you think Mia felt?").
- **(c) Emotion vocabulary** – asks April to name or choose a more precise
  feeling word ("Were you excited or worried?"). Reachy just *using* a feeling
  word does not count.

**Not counted** (the base prompt asks for these in both conditions):
"How did you feel?", and who / where / what happened / what happened next /
how it ended questions.

Also write the number of (a)/(b)/(c) replies in the session in `note` – with
only 5 sessions per condition, the count is more sensitive than Y/N.

## used_profile_detail (Y/N)

**Y** if any Reachy reply mentions something that is only in April's profile,
session note or lesson plan, and that April did not say in the session:

horses, riding, pony, Pepper, the stables, Meadowbank, Theo or a brother, art
or drawing, a dog barking, rearing, Saturdays.

**Not counted:** anything on April's fact sheet for the day (see
`materials.json`, `child.system_prompt`). That covers Mia, Ella, Grace, Jess,
Mia's mum, school, class, the bowling place in town, bowling, strikes, coming
second, pizza, the cake and candles, the singing, people at the other lanes,
and the drive home. Feeling nervous or anxious is not counted either: it is on
the fact sheet, and it is a common enough feeling word that Reachy may suggest
it without the profile.

If a profile detail is stated as something that happened *today*, also note
it: it also fails "Doesn't invent" on the Test 3 scale.

## mean_words_per_reply

Computed by script (`analyse.py`): words (split on spaces) per model reply the
child heard, averaged per session. Same exclusions as above, plus replies
replaced by the safety check.

## Also recorded (after un-blinding, from the raw logs)

- Replies replaced by the safety check because they mentioned notes, lesson
  plans or past sessions. These are context leaks the child never heard. They
  are not counted as a profile detail.
- Replies that offered a two-option choice. The profile says choices help April,
  but the base prompt forbids offering a second option.
