You are helping to build a test set for research on a tool that turns transcripts of speech and language therapy sessions into lesson plans. Write 30 realistic, fictional transcripts of one-to-one sessions. In each, an autistic young person aged 11 to 17 tells the therapist about something that really happened to them (a personal recount). Record exactly what each young person did and did not say.

Realism matters more than anything else. Write sessions that a UK speech and language therapist who works with autistic teenagers would recognise from real practice. Do not write them to test or trick any software. Everyone in them is fictional.

## The young people

- 30 different autistic young people aged 11 to 17, spread across that range (about 4 at each age).
- Mixed genders, and varied names and backgrounds.
- UK settings and British English: secondary school, Year 7 to Year 13, form tutor, Mum, the chippy and so on.
- Autistic young people differ a great deal from one another. Vary communication profiles across the set and avoid stereotypes. Draw on features like these, but do not put them all in one transcript:
  - very short answers to open questions ("Fine.", "Nothing really.", "Don't know"), with more detail when a question is specific;
  - long, detailed turns about a special interest, sometimes drifting away from the event;
  - precise details (times, numbers, names of games, trains or brands) while the main point of the story is left out;
  - taking a question literally ("How did it go?" "By bus.");
  - mentioning people as if the listener already knows them ("Then Callum took it.");
  - showing feelings through body sensations, actions or facts rather than emotion words ("My hands went all fizzy", "I went to the toilets and stayed there"), or saying they don't know how they felt;
  - sensory experiences (noise, crowds, smells, lights) as a big part of the story;
  - quoting or scripting lines from games, YouTube or TV;
  - unusually formal or precise wording, or very flat, minimal answers;
  - correcting the therapist's wording ("It wasn't a fight, it was an argument.");
  - ordinary teenage reluctance or impatience ("Do we have to do this?"), changing the subject, asking the therapist questions;
  - needing time to think: "um", pauses written as "...", false starts, self-corrections.
- Events should suit 11 to 17 year olds. For example:
  - school: a lesson, a supply teacher, a fire alarm, a group project, a detention, a school trip, the canteen;
  - gaming online with friends;
  - a club or sport;
  - a family event;
  - a medical appointment;
  - a change of routine;
  - a falling-out;
  - a concert or a shop;
  - public transport;
  - a holiday;
  - for older ones, a part-time job or volunteering.

  Use no event type twice.

## The therapist

- Experienced with autistic teenagers and neurodiversity-affirming: respectful, never babyish, gives processing time, and accepts the young person's way of communicating.
- Session shape:
  - often opens with a short story of their own as a model (in at least 15 of the 30);
  - invites the young person to tell theirs, and prompts;
  - sometimes says the story back to them (in at least 15 of the 30);
  - closes.
- Words questions differently each time. Mixes open questions, specific questions and choices ("Was that at school or at home?"), and sometimes refers to a visual story planner ("who, where, what happened…"). Does not ask about every part of the story.
- Echoes and rephrases the young person's words. Sometimes says a feeling or a reason the young person never expressed ("That must have been really stressful", "That's because the bus was late").
- **Must never state a part of the story the young person left out.** The therapist may ask about it, or offer a guess as a question, but must not supply it. Any recap contains only what the young person said.

## Format

- Plain text, one block per transcript, in this style: `Therapist. Hi Sam, how's your week been? Child. Fine. Therapist. ...`
- Every turn starts with exactly `Therapist.` or `Child.` followed by a space. Use `Child.` for the young person whatever their age, because the analysis software expects that label.
- A turn is everything one person says before the other speaks. Use 20–45 turns per transcript, with at least 6 transcripts over 30 turns.
- At least 6 transcripts should read like raw speech-recognition output: lower case, little or no punctuation, speaker changes in the middle of sentences, repeated words and false starts. Keep the labels exact.
- Number the transcripts T31 to T60.

## Definitions (these decide what you record)

**The five story parts.** The young person gives a part if their own words say it:

| Part | What it means |
|---|---|
| who | who was there or took part (people or animals); naming someone counts even if they are not introduced |
| where | where it happened |
| what happened | the main events, or what the young person did |
| how they felt | any feeling they had (see "a feeling" below) |
| how it ended | how the event finished, or what happened at the very end of it |

**A part is left out** if the young person's own words never give it. Record how:
- **asked:** the therapist asked about it and they did not give it ("I don't know", changed the subject, answered something else);
- **silent:** nobody asked, and they never said it;
- **yes-only:** the therapist suggested it and they only said "yes" or "no". A bare yes or no never counts as giving a part.

**A feeling** is anything that makes clear how the young person felt, in any words:
- a common emotion word ("angry", "anxious", "happy");
- any other way, such as "I hated it", "it was actually decent", "I just wanted to go home", "my hands went all fizzy", "I was laughing so much".

Only record expressions where a listener would clearly know the feeling, and write down which feeling it shows. A bare "fine", "OK", "good" or "alright" does not count as a feeling.

**A reason** is the young person saying why something happened or why they felt something. It can use:
- "because" or "so";
- another link ("cos", "that's why");
- no linking word at all ("I left. It was too loud.").

A reason may come in a different turn from the thing it explains.

## Totals across all 30 transcripts

Write naturally first, then check these totals and adjust.

| What | Across the 30 |
|---|---|
| Parts left out | 36 to 54 in total, with each of the five parts left out at least 6 times |
| …left out silently | at least 18 |
| …asked about but not given | at least 12 |
| …yes-only | at least 3 |
| Per transcript | at most 3 parts left out |
| Nothing left out | at least 3 transcripts |
| Feelings shown without a common emotion word | in at least 15 transcripts |
| No feelings at all ("how they felt" left out) | at least 6 transcripts (these count towards the parts above) |
| Two or more different feelings | at least 6 transcripts |
| A reason with no "because" or "so" | in at least 9 transcripts |
| No reasons at all | at least 6 transcripts |
| A reason using "because" or "so" | in at least 6 transcripts |
| Therapist expresses a feeling or reason the young person never does | in at least 18 transcripts |
| Rough speech-recognition style | at least 6 transcripts |
| More than 30 turns | at least 6 transcripts |

## Recording what you planted

Make a tab-separated features sheet with these columns:

| Column | What to put |
|---|---|
| transcript_id | T31 … T60 |
| type | `given`, `left_out`, `feeling`, `reason`, `no_reasons` or `trap` |
| part_or_feeling | the story part (who, where, what happened, how it ended), or for feeling/reason/trap rows, what it is ("anxious", "why they left") |
| how | for `left_out`: asked / silent / yes-only. For `feeling`: word (common emotion word) or phrase (any other way). For `reason`: because-so / other-link / no-link |
| words | the exact words, copied from the transcript: the young person's for given/feeling/reason; the therapist's for a trap; for an asked or yes-only part, the therapist's question and the reply, as `Therapist. <question> Child. <reply>` |
| note | anything a scorer should know |

Rows each transcript needs:
- **`given`:** one row for each of who, where, what happened and how it ended that the young person gives. Separate pieces from different turns with " … ".
- **`left_out`:** one row for each part left out, including "how they felt" if they show no feeling.
- **`feeling`:** one row for each different feeling they show.
- **`reason`:** one row for each reason they give, or a single `no_reasons` row if there are none.
- **`trap`:** one row for each feeling or reason that only the therapist expresses.

## Example (format only; do not reuse its content)

Transcript:

`Therapist. So how was Saturday? Child. Fine. Therapist. Fine. Did anything happen? Child. We went to the trampoline park with my cousin Leah. It was really loud, like the music and everyone screaming. I hated it. Therapist. That sounds really overwhelming. What did you do? Child. I sat in the café bit with my headphones on. Then I did dodgeball when it was quieter. Therapist. You did dodgeball when it was quieter. Child. Can we stop now?`

Features rows:

```
T00	given	where		We went to the trampoline park	
T00	given	who		with my cousin Leah	
T00	given	what happened		I sat in the café bit with my headphones on. Then I did dodgeball when it was quieter.	
T00	left_out	how it ended	silent		never says how the visit ended
T00	feeling	dislike	phrase	I hated it.	
T00	reason	why they hated it	no-link	It was really loud, like the music and everyone screaming.	
T00	trap	overwhelmed		That sounds really overwhelming.	the young person never says this
```

## Output, in batches

Write the 30 transcripts in 6 batches of 5, starting with T31–T35. For each batch, output:
1. each transcript in its own code block, headed with its file name (for example, T31.txt);
2. one code block with that batch's features rows, tab-separated (with the header row in the first batch only);
3. a running tally against the totals table.

Before outputting each batch, check two things:
- every `words` entry is copied exactly from its transcript and said by the right speaker;
- the therapist never supplies a part that was left out.

Then stop and wait for me to say "next".
