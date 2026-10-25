# Test 6 results: lesson planner v2, speaker labels removed and added automatically

| Measure | v1, T01-T10 | v2, T01-T10 (development) | v2, T11-T20 (held out) | v2, all 20 |
|---|---|---|---|---|
| Hit rate | 0.73 (27/37) | 0.95 (35/37) | 0.97 (35/36) | 0.96 (70/73) |
| False alarms per transcript | 1.1 (11) | 0.3 (3) | 0.4 (4) | 0.3 (7) |
| Quotes not in transcript | 1 of 27 | 0 of 74 | 0 of 79 | 0 of 153 |

| Planted feature type (hits / planted) | v1, T01-T10 | v2, T01-T10 (development) | v2, T11-T20 (held out) | v2, all 20 |
|---|---|---|---|---|
| Story parts left out | 8/12 | 11/12 | 10/11 | 21/23 |
| Uses 'because' / 'so' | 5/6 | 6/6 | 7/7 | 13/13 |
| Uses neither 'because' nor 'so' | 0/4 | 4/4 | 3/3 | 7/7 |
| Emotion words (or none) | 14/15 | 14/15 | 15/15 | 29/30 |

## Automatic speaker labels

- OVERALL, model alone: 908/959 sentences right (94.7%); child's sentences found 323/327 (98.8%); labelled child and really were 323/370 (87.3%)
- OVERALL, after echo rule: 937/959 sentences right (97.7%); child's sentences found 318/327 (97.2%); labelled child and really were 318/331 (96.1%)
- OVERALL, after echo rule, T01-T10: 463/472 sentences right (98.1%); child's sentences found 155/160 (96.9%); labelled child and really were 155/159 (97.5%)
- OVERALL, after echo rule, T11-T20 (held out): 474/487 sentences right (97.3%); child's sentences found 163/167 (97.6%); labelled child and really were 163/172 (94.8%)
