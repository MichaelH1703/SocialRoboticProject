You are coding conversation transcripts for a research study. Apply the rules below exactly, and nothing else. Each session is coded on its own.

Each transcript is a conversation between Reachy, a robot, and April, a 14-year-old with autism, about her day. Lines starting "You:" are April. Code ONLY the lines labelled "Reachy [n]:". Ignore lines marked "(greeting, not coded)" or "(scripted, not coded)".

## 1. followed_lesson_focus (Y/N)

Y if at least one coded Reachy reply does any of these:

- (a) Explanation: asks why something happened or why April felt something, or otherwise asks for a reason ("What made you nervous?", "Why do you think…?", "…because…?").
- (b) Perspective: asks how another person felt or what they thought ("How do you think Mia felt?").
- (c) Emotion vocabulary: asks April to name or choose a more precise feeling word ("Were you excited or worried?"). Reachy just using a feeling word does not count.

Not counted: "How did you feel?", and who / where / what happened / what happened next / how it ended questions.

focus_move_count: the number of coded replies that do (a), (b) or (c). A reply that does more than one still counts once.

## 2. used_profile_detail (Y/N)

Y if any coded Reachy reply mentions any of these, and April did not say it earlier in that session: horses, riding, pony, Pepper, the stables, Meadowbank, Theo or a brother, art or drawing, a dog barking, rearing, Saturdays.

Not counted: anything from April's actual day. That is: Mia, Ella, Grace, Jess, Mia's mum, school, class, the bowling place in town, bowling, strikes, coming second, pizza, the cake and candles, the singing, people at the other lanes, and the drive home. Feeling nervous or anxious is not counted either.

If Reachy states a profile detail as something that happened today, say so in the note.

## Output

For each session, first show your working in a few lines:
- each reply you counted for focus, as: reply number, letter (a/b/c), and the exact words that qualify;
- any profile detail, with its reply number and words, or "none".

Then, after all sessions, give ONE tab-separated block, with this header and one row per session in label order:

label	followed_lesson_focus	used_profile_detail	focus_move_count	note

- followed_lesson_focus and used_profile_detail are exactly Y or N.
- focus_move_count is a whole number.
- note lists the counted reply numbers per letter, e.g. "a: 3, 7; b: none; c: 5", plus any profile-detail note.

If a reply is a borderline case, decide using only the rules above and write "borderline: reply n, <why>" in the note.

The sessions follow.
