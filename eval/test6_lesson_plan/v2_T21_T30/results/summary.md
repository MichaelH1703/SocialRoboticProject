# Test 6, held-out set T21-T30: lesson planner v2, labels added automatically

- Hit rate: 27/39 = 0.69
- False alarms: 5 over 10 transcripts = 0.5 per transcript (T21 what happened, T24 missing feelings, T25 missing feelings, T29 missing reasons, T30 missing feelings)
- Quotes: 63 checked; 63 exact, 0 reworded, 0 not there; 10 include the therapist's words
- Therapist's traps credited to the child: 2 of 10 (T22 why the man used a torch, T28 proud)

| Planted feature (hits / planted) | |
|---|---|
| Story parts left out | 12/14 |
| …left out silently (never asked) | 7/7 |
| …asked about but not given | 3/5 |
| …only a yes to the therapist's guess | 2/2 |
| Feelings | 6/15 |
| …named with an emotion word | 3/3 |
| …shown any other way | 3/12 |
| Reasons (gives a reason / gives none) | 9/10 |

## Automatic speaker labels (word by word)

- OVERALL, model alone: 2829/3391 words right (83.4%); child's words found 1265/1414 (89.5%); labelled child and really were 1265/1678 (75.4%)
- OVERALL, after echo rule: 2860/3391 words right (84.3%); child's words found 1262/1414 (89.3%); labelled child and really were 1262/1641 (76.9%)
- T21: NOT auto-labelled (labelling failed; the plan used the unlabelled fallback)
- T22: 339/386 words right (87.8%), 54 sentences
- T23: 320/349 words right (91.7%), 48 sentences
- T24: 468/522 words right (89.7%), 76 sentences
- T25: 342/391 words right (87.5%), 68 sentences
- T26: 300/346 words right (86.7%), 60 sentences
- T27: 315/344 words right (91.6%), 56 sentences
- T28: 160/340 words right (47.1%), 1 sentences
- T29: 354/380 words right (93.2%), 60 sentences
- T30: 262/333 words right (78.7%), 55 sentences

## For context: v2 on T11-T20 (scored by keyword, not meaning)

- Hit rate 0.97; false alarms per transcript 0.4
