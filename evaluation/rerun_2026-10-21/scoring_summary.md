# Scoring summary (automatic part; provisional quote marks included)

compare.py SHA-256: `cadced930f3c1c882ce367c0b8c80e635d8978da86c8c7451382b62976285b3a`

| Version | Set | Hit rate | False alarms / transcript | Quotes not there / checked | Provisional quotes | Quotes said only by therapist | Traps credited | Feelings without a feeling word found |
|---|---|---|---|---|---|---|---|---|
| v1 | T01–T10 | 0.73 (27/37) | 0.7 (7) | 1/25 | 2 | 4 | 2 credited (by reading) |  |
| v1 | T11–T20 | 0.64 (23/36) | 1.1 (11) | 1/10 | 1 | 2 | 9 credited (by reading) |  |
| v1 | T21–T30 | 0.64 (25/39) | 0.2 (2) | 3/24 | 4 | 5 | 4 credited (by reading) | 11/12 |
| v1 | T31–T60 | 0.83 (57/69) | 0.5 (14) | 3/51 | 6 | 4 | 14 credited (by reading) | 16/18 |
| v1 | All 60 | 0.73 (132/181) | 0.6 (34) | 8/110 | 13 | 15 | 29 credited (by reading) | 27/30 |
| v2 | T01–T10 | 0.95 (35/37) | 0.3 (3) | 0/62 | 0 | 1 |  |  |
| v2 | T11–T20 | 0.97 (35/36) | 0.4 (4) | 0/66 | 0 | 0 |  |  |
| v2 | T21–T30 | 0.62 (24/39) | 0.6 (6) | 2/59 | 3 | 4 | 2/10 | 0/12 |
| v2 | T31–T60 | 0.51 (35/69) | 1.5 (46) | 3/208 | 4 | 23 | 5/25 | 1/18 |
| v2 | All 60 | 0.71 (129/181) | 1.0 (59) | 5/395 | 7 | 28 | 7/35 | 1/30 |

Failed runs: v1 none, v2 none.
Quotes and v1 judgements needing a manual check: 98.
v2 quoted sentences only the therapist said (compare.py rule), by set: T01–T10 2, T11–T20 4, T21–T30 8, T31–T60 14, All 60 28
