# Test 6 (NFR3) re-run: lesson planner v1 and v2

- Started: 2026-10-21 17:45:21 +0800
- Host: MichaelsLaptop (Windows-11-10.0.26200-SP0)
- Python: 3.12.7 (C:\ThesisProject\ReachyVoiceCode\venv\Scripts\python.exe)
- Ollama: 0.20.5
- GPU: NVIDIA GeForce RTX 4060 Laptop GPU, 566.26, 2405 MiB, 8188 MiB

## `ollama list`

```
NAME           ID              SIZE      MODIFIED     
llama3.2:3b    a80c4f17acd5    2.0 GB    2 months ago    
qwen2.5:3b     357c53fb659c    1.9 GB    2 months ago    
qwen3:4b       359d7dd4bcda    2.5 GB    6 months ago    
qwen3:8b       500a1f067a9f    5.2 GB    6 months ago
```

Full digests (`/api/tags`):

- `llama3.2:3b`: `a80c4f17acd55265feec403c7aef86be0c25983ab279d83f3bcd3abbcb5b8b72`
- `qwen2.5:3b`: `357c53fb659c5076de1d65ccb0b397446227b71a42be9d1603d46168015c9e4b`
- `qwen3:4b`: `359d7dd4bcdab3d86b87d73ac27966f4dbb9f5efdfcc75d34a8764a09474fae7`
- `qwen3:8b`: `500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41`

## SHA-256 of planners, scorer and helpers

```
5377933a2560226439bf3623c7689ba8a5c7663786e6f839cb788227dff3a8c9  lesson_planner.py
ae77ac982f51d1f781c1e5396eb293a42300e2a6136e1012af0ad093670b4f5f  lesson_planner_v2.py
6203179a191f569227bfd4f8eb02fea5a539c33166d0f14c54fbe98af7bd63b4  lesson_planner_v3.py
cadced930f3c1c882ce367c0b8c80e635d8978da86c8c7451382b62976285b3a  eval/test6_lesson_plan/v3/compare.py
7944f71a99da05e20f00ef0ec9c59c63e5903b1901d4cbd1436935411d9e7a8e  eval/test6_lesson_plan/find_quotes.py
59a6999db3340beffd88d2fd0b6aed24dfd4d1c9699e5d65526fd0e3e90c9a2f  eval/test6_lesson_plan/run_generator.py
4721f3137268e88b05395b3ff33842f6f32287435b3b3b1a246e24ae92e7b7e7  eval/test6_lesson_plan/v2_autolabel/run_v2.py
```

## SHA-256 of truth sheets

```
286825ab72c2d43c9eda80e258cd86c3f9f8fb3ffe37180cc4f231843736a88d  eval/test6_lesson_plan/features.json
aa3ab6c9efbf7f8ad476af0fcd1fe2de55e825cc1f65398efa8ff84484aa9c32  eval/test6_lesson_plan/T21_T30_spec.md
5122e387da1472463779cd1a92f2b8775350d904377c56361a98fd5e8ca79477  eval/test6_lesson_plan/T21_T30_features.tsv
0d22695d0eb37ad174e73953dd8cf3b6dd345b2e86f98ab881fedfe9e829c742  eval/test6_lesson_plan/T31_T60_features.tsv
```

## SHA-256 of transcripts (labelled originals)

```
e2b4fb12cb80efa77a7b9cf5b625805e6a85ffbfbd034f0d6b7b1c6da7f8fa2f  eval/test6_lesson_plan/transcripts/T01.txt
d41f40668629e6c01fc7886541babbeef7486bb11ad664b32bafad34cfd41681  eval/test6_lesson_plan/transcripts/T02.txt
1ecc0b7aceff5291fefb6ecc123a4f665b3e638c3dfe3a84deda2f5ba52c610f  eval/test6_lesson_plan/transcripts/T03.txt
a9d9d971bef5e37297011583deb35d838b837b2b05974fbb8089eb8dcc3324ac  eval/test6_lesson_plan/transcripts/T04.txt
5a821f3d30b3a2fb9a74e8e9b7164ea9ece36e96268fd6673282e76c410813dc  eval/test6_lesson_plan/transcripts/T05.txt
20572f479720c7ff5f0768f8bf2bc88202811c5d6045b963af69ec8f13628e68  eval/test6_lesson_plan/transcripts/T06.txt
affbe92affc05c804ba0490d0168b487e6851bb0d72c0a96b1e6385740e390a9  eval/test6_lesson_plan/transcripts/T07.txt
e2d5f044ac8a162770040feea368fd8f602dc94a19f9c07acee9d352fde0e583  eval/test6_lesson_plan/transcripts/T08.txt
4a77a859eac2ef7581e3f0fcfe5583ef13dcd6c8d849b62824ed6151fc679edd  eval/test6_lesson_plan/transcripts/T09.txt
edd478bc9ceb90643959caae17cfd5a4d6e74b3fc6538e71444ff68b3f3854fe  eval/test6_lesson_plan/transcripts/T10.txt
f373c7d0b85a085e41ef1990fb1a25c2270f6621d69f89c4f2d817ab1b789b71  eval/test6_lesson_plan/transcripts/T11.txt
f7262954f9d91caf3e8ee5d1e64ca164b94fcc7298128e3cba5f2f1166f9675f  eval/test6_lesson_plan/transcripts/T12.txt
0d4fc0626f86df630014ea8a56fe0f45de44c3eb7073d95f7e8b07a51caedaa1  eval/test6_lesson_plan/transcripts/T13.txt
cdfe2377bdd00ade7d1405c63bb129cf33871e7b178d459471b31e30cdf58db5  eval/test6_lesson_plan/transcripts/T14.txt
db3b20cf46fadfcd6ecd2efbdb5168b376b361c552a741bf0d06c9b1f70f0b63  eval/test6_lesson_plan/transcripts/T15.txt
6853c2c30d555c0b57e0300e388e3ee2696ddde4024eeec31ed10e62b27ff89e  eval/test6_lesson_plan/transcripts/T16.txt
847e6557eb9ca90d01a3689ee0d1b22646e823637ff424a33881832f3cf2fa8a  eval/test6_lesson_plan/transcripts/T17.txt
860b70573efe3a35c5ded46773c3044aed5b05f0b7109ddcab17fc9c9a9f143b  eval/test6_lesson_plan/transcripts/T18.txt
8e359c7001eb33870684b6224cdec01e5185a0a144ada4e0260f04ef8e7eb7a1  eval/test6_lesson_plan/transcripts/T19.txt
d9e31a15821cd93d548f363c93b85159be62a01ed21a4428520accb3ef619043  eval/test6_lesson_plan/transcripts/T20.txt
eb8e0ff0f0e4f0c6aa94845e6105c7e61bc42a891994cfe396b8bd7e3f1fa37b  eval/test6_lesson_plan/transcripts/T21.txt
75ebe26038c978eaf166cd91230e4a312d3586f2ce5d2fa9c8247e8b19eacd42  eval/test6_lesson_plan/transcripts/T22.txt
ea3630d737ce958ca9c60ba689c5597087ed5c9a83a3071b9947b22e65c7a409  eval/test6_lesson_plan/transcripts/T23.txt
745371ff45effe2f407aac6087cedf1f227919d4694e2ecfa04eb5dcaeb24bb7  eval/test6_lesson_plan/transcripts/T24.txt
20afa26c3ab313555f1125067f7249e4f555688a0970937e33162c1f0e46aafe  eval/test6_lesson_plan/transcripts/T25.txt
2275c746f132ccccb6ebd3f6608e364579b4339a0ec5c119c6bf2048dbefe140  eval/test6_lesson_plan/transcripts/T26.txt
1ea1e05639b0a91d4f1bcfcb74f1777a0224613b1a6f46712bb2ec55a8b8f158  eval/test6_lesson_plan/transcripts/T27.txt
a9c2324ddb4604803492d14220aafa69d8cb1da3de8eadc3cddb3e0d406067b5  eval/test6_lesson_plan/transcripts/T28.txt
9c006a1cb51e113137cdf2aa9ecb2d099a97a7cc0d02693b112b9b1b4d6f17a1  eval/test6_lesson_plan/transcripts/T29.txt
1d5e0ec32e79d73cbb573b323c2676a50a941d897c54ea5cbead0655b10d1370  eval/test6_lesson_plan/transcripts/T30.txt
c6a1b6d4f54fd858717cdaa8fe36cd1d8164fb1da8034be1cddbfbba1914a0e7  eval/test6_lesson_plan/transcripts/T31.txt
e33ff6a316ee997c7ee01cc8b7191a179d50f885398257a855fca5e31c90cdd7  eval/test6_lesson_plan/transcripts/T32.txt
5817382fc6184956df440832db56f9b686d640fab3e3622be6822beddfdd7554  eval/test6_lesson_plan/transcripts/T33.txt
4635f2613d691ecff7cdafcbe3d836070349a0f3c5046dd81cab4dc9c6c9c6c0  eval/test6_lesson_plan/transcripts/T34.txt
422adc9e6f78bdd721aebbc09d0c2050e263e733a27d382557142c1c40e8a453  eval/test6_lesson_plan/transcripts/T35.txt
9df89b3de1b8ea92a2cb043206470e64771d822271b96ee359d557178db823a5  eval/test6_lesson_plan/transcripts/T36.txt
e6fc931a937912152e25407220021bf97ce65f1162b4882db3043e0dd7f4f432  eval/test6_lesson_plan/transcripts/T37.txt
1eca2cd4bc50ade276e526c6206fc42742a8f804f06ebf4f1051d85a5fa9833c  eval/test6_lesson_plan/transcripts/T38.txt
812f2d504547807d18f85c1c1b64efa486238d2e84601336635287cd0c7d3841  eval/test6_lesson_plan/transcripts/T39.txt
baa80fe7e27d73160dd5119d2b9bb0ac8e9655a0bb3c11dc026ca31e5a0d5530  eval/test6_lesson_plan/transcripts/T40.txt
5e841bce97f38d0a4d9007f71e57f49dae33e4bf45bdb468d5a82d3de8af159b  eval/test6_lesson_plan/transcripts/T41.txt
a42ce4c6b82c982b9c1914546320e8a3101b4abd5abf5fd5cdc432f5c8398148  eval/test6_lesson_plan/transcripts/T42.txt
5a2a99711be4efd87dc92fb17fa639f14a7b64d244292601945e587b26e9a49b  eval/test6_lesson_plan/transcripts/T43.txt
34315f9d2d61dd03a2ad0d7f4cba2f49750ddefc2f14305c70effc70c51090a5  eval/test6_lesson_plan/transcripts/T44.txt
0801610f1654f0853ce3ef476760d8d043c6d8688401bf2d4fdbdd781fed44a1  eval/test6_lesson_plan/transcripts/T45.txt
028adca14b9c39211dcef5f8c2b337e6e6ef1000b972f0f078ae33f0131a8c26  eval/test6_lesson_plan/transcripts/T46.txt
033bc1e131b7acab8484219251d73ee8f84b861c6f7b7e78100908611383d053  eval/test6_lesson_plan/transcripts/T47.txt
a644fbbfa3972b5e7e4cbc4bba1b6c563ce855647c5b0dc688fe70254883ef83  eval/test6_lesson_plan/transcripts/T48.txt
2dcdd693a5f21d7b234c0b3f493ccdd610c01d39385a53ba7ad372586e1d73ba  eval/test6_lesson_plan/transcripts/T49.txt
32f9d748b1e196068a3061979ba62655e9e8543038c1563996f30a39d63c552f  eval/test6_lesson_plan/transcripts/T50.txt
68f97aa7b78a53947d440fb29732c9fde05e34a692114e035b9158e4e4a9d0af  eval/test6_lesson_plan/transcripts/T51.txt
e60e1c11ba083b0720424b6ba01545b71230d182448dee469138558ac095ad2a  eval/test6_lesson_plan/transcripts/T52.txt
57c326231a39244a3cfa66801c8add81d370af5e86775effd5b91c396db76c7e  eval/test6_lesson_plan/transcripts/T53.txt
77b7bb154510df896551381b31f411e18ea6675874dd3bd572fc05b70b418f3b  eval/test6_lesson_plan/transcripts/T54.txt
a6199f88399ace9320ae57cc0212c014df0558ff999794d8063319b2c8de6faf  eval/test6_lesson_plan/transcripts/T55.txt
daa49769088b8588150fe41ec143d27bfeb8e166d4d5ed549ce9b7cedb7f4adf  eval/test6_lesson_plan/transcripts/T56.txt
05b8a62b453689976569aadfe354febc8f09a0639681350e3a11c5a11982b2fc  eval/test6_lesson_plan/transcripts/T57.txt
68a8f41e0341f786a4ca0bb96e7120763dc3419c2f49828b665d84942187cd1f  eval/test6_lesson_plan/transcripts/T58.txt
da9a7ebe9ec284b8f0ffa0459181033636ffd59840a81dc07acf2b3c9fb3f665  eval/test6_lesson_plan/transcripts/T59.txt
9144f5c62be89301b5483613fba4349e5bfadf8434d0c93b75c273bcdd2afe70  eval/test6_lesson_plan/transcripts/T60.txt
```

## Runs

One line per attempt. Status `ok`, `retry` (first attempt failed) or `FAILED` (both attempts failed).


### v1 (qwen2.5:3b), started 2026-10-21 17:45:28 on MichaelsLaptop
- before first transcript, ollama ps: qwen2.5:3b 100% GPU
- T01: ok, start 2026-10-21 17:45:30, end 2026-10-21 17:45:37 (7s), 340 words
  - ollama ps: qwen2.5:3b 100% GPU
- T02: ok, start 2026-10-21 17:45:39, end 2026-10-21 17:45:45 (6s), 259 words
- T03: ok, start 2026-10-21 17:45:45, end 2026-10-21 17:45:51 (6s), 290 words
- T04: ok, start 2026-10-21 17:45:51, end 2026-10-21 17:45:58 (6s), 304 words
- T05: ok, start 2026-10-21 17:45:58, end 2026-10-21 17:46:04 (6s), 334 words
- T06: ok, start 2026-10-21 17:46:04, end 2026-10-21 17:46:11 (7s), 356 words
- T07: ok, start 2026-10-21 17:46:11, end 2026-10-21 17:46:16 (5s), 197 words
- T08: ok, start 2026-10-21 17:46:16, end 2026-10-21 17:46:22 (6s), 257 words
- T09: ok, start 2026-10-21 17:46:22, end 2026-10-21 17:46:28 (6s), 291 words
- T10: ok, start 2026-10-21 17:46:28, end 2026-10-21 17:46:34 (6s), 289 words
- T11: ok, start 2026-10-21 17:46:34, end 2026-10-21 17:46:41 (7s), 339 words
- T12: ok, start 2026-10-21 17:46:41, end 2026-10-21 17:46:47 (6s), 268 words
- T13: ok, start 2026-10-21 17:46:47, end 2026-10-21 17:46:54 (7s), 336 words
- T14: ok, start 2026-10-21 17:46:54, end 2026-10-21 17:47:01 (7s), 366 words
- T15: ok, start 2026-10-21 17:47:01, end 2026-10-21 17:47:07 (6s), 323 words
- T16: ok, start 2026-10-21 17:47:07, end 2026-10-21 17:47:12 (5s), 225 words
- T17: ok, start 2026-10-21 17:47:12, end 2026-10-21 17:47:19 (7s), 346 words
- T18: ok, start 2026-10-21 17:47:19, end 2026-10-21 17:47:26 (7s), 342 words
- T19: ok, start 2026-10-21 17:47:26, end 2026-10-21 17:47:33 (7s), 376 words
- T20: ok, start 2026-10-21 17:47:33, end 2026-10-21 17:47:39 (6s), 268 words
- T21: ok, start 2026-10-21 17:47:39, end 2026-10-21 17:47:45 (6s), 314 words
- T22: ok, start 2026-10-21 17:47:45, end 2026-10-21 17:47:52 (7s), 329 words
- T23: ok, start 2026-10-21 17:47:52, end 2026-10-21 17:47:59 (7s), 400 words
- T24: ok, start 2026-10-21 17:47:59, end 2026-10-21 17:48:08 (8s), 475 words
- T25: ok, start 2026-10-21 17:48:08, end 2026-10-21 17:48:14 (6s), 283 words
- T26: ok, start 2026-10-21 17:48:14, end 2026-10-21 17:48:21 (7s), 325 words
- T27: ok, start 2026-10-21 17:48:21, end 2026-10-21 17:48:28 (7s), 374 words
- T28: ok, start 2026-10-21 17:48:28, end 2026-10-21 17:48:35 (7s), 310 words
- T29: ok, start 2026-10-21 17:48:35, end 2026-10-21 17:48:40 (6s), 246 words
- T30: ok, start 2026-10-21 17:48:40, end 2026-10-21 17:48:47 (7s), 321 words
  - ollama ps: qwen2.5:3b 100% GPU
- T31: ok, start 2026-10-21 17:48:49, end 2026-10-21 17:48:57 (8s), 453 words
- T32: ok, start 2026-10-21 17:48:57, end 2026-10-21 17:49:03 (6s), 274 words
- T33: ok, start 2026-10-21 17:49:03, end 2026-10-21 17:49:11 (8s), 403 words
- T34: ok, start 2026-10-21 17:49:11, end 2026-10-21 17:49:17 (6s), 306 words
- T35: ok, start 2026-10-21 17:49:17, end 2026-10-21 17:49:24 (7s), 372 words
- T36: ok, start 2026-10-21 17:49:24, end 2026-10-21 17:49:30 (6s), 287 words
- T37: ok, start 2026-10-21 17:49:30, end 2026-10-21 17:49:38 (8s), 392 words
- T38: ok, start 2026-10-21 17:49:38, end 2026-10-21 17:49:45 (7s), 398 words
- T39: ok, start 2026-10-21 17:49:45, end 2026-10-21 17:49:53 (8s), 420 words
- T40: ok, start 2026-10-21 17:49:53, end 2026-10-21 17:49:59 (6s), 282 words
- T41: ok, start 2026-10-21 17:49:59, end 2026-10-21 17:50:06 (7s), 360 words
- T42: ok, start 2026-10-21 17:50:06, end 2026-10-21 17:50:13 (7s), 342 words
- T43: ok, start 2026-10-21 17:50:13, end 2026-10-21 17:50:20 (6s), 279 words
- T44: ok, start 2026-10-21 17:50:20, end 2026-10-21 17:50:25 (6s), 267 words
- T45: ok, start 2026-10-21 17:50:25, end 2026-10-21 17:50:33 (8s), 423 words
- T46: ok, start 2026-10-21 17:50:33, end 2026-10-21 17:50:39 (6s), 249 words
- T47: ok, start 2026-10-21 17:50:39, end 2026-10-21 17:50:47 (7s), 342 words
- T48: ok, start 2026-10-21 17:50:47, end 2026-10-21 17:50:54 (7s), 364 words
- T49: ok, start 2026-10-21 17:50:54, end 2026-10-21 17:51:01 (7s), 402 words
- T50: ok, start 2026-10-21 17:51:01, end 2026-10-21 17:51:07 (6s), 250 words
- T51: ok, start 2026-10-21 17:51:07, end 2026-10-21 17:51:13 (6s), 306 words
- T52: ok, start 2026-10-21 17:51:13, end 2026-10-21 17:51:20 (7s), 341 words
- T53: ok, start 2026-10-21 17:51:20, end 2026-10-21 17:51:26 (6s), 274 words
- T54: ok, start 2026-10-21 17:51:26, end 2026-10-21 17:51:33 (6s), 305 words
- T55: ok, start 2026-10-21 17:51:33, end 2026-10-21 17:51:39 (6s), 280 words
- T56: ok, start 2026-10-21 17:51:39, end 2026-10-21 17:51:45 (6s), 278 words
- T57: ok, start 2026-10-21 17:51:45, end 2026-10-21 17:51:51 (7s), 352 words
- T58: ok, start 2026-10-21 17:51:51, end 2026-10-21 17:51:58 (7s), 329 words
- T59: ok, start 2026-10-21 17:51:58, end 2026-10-21 17:52:05 (7s), 378 words
- T60: ok, start 2026-10-21 17:52:05, end 2026-10-21 17:52:12 (7s), 325 words
  - ollama ps: qwen2.5:3b 100% GPU
### v1 finished 2026-10-21 17:52:14

### v2 (qwen3:8b), started 2026-10-21 17:52:14 on MichaelsLaptop
- before first transcript, ollama ps: qwen2.5:3b 100% GPU
- T01: ok, start 2026-10-21 17:52:17, end 2026-10-21 17:52:54 (38s), speakers auto, input identical to original v2 run
  - ollama ps: qwen3:8b 100% GPU
- T02: ok, start 2026-10-21 17:52:56, end 2026-10-21 17:53:38 (42s), speakers auto, input identical to original v2 run
- T03: ok, start 2026-10-21 17:53:38, end 2026-10-21 17:54:14 (36s), speakers auto, input identical to original v2 run
- T04: ok, start 2026-10-21 17:54:14, end 2026-10-21 17:54:48 (34s), speakers auto, input identical to original v2 run
- T05: ok, start 2026-10-21 17:54:48, end 2026-10-21 17:55:30 (42s), speakers auto, input identical to original v2 run
- T06: ok, start 2026-10-21 17:55:30, end 2026-10-21 17:56:03 (34s), speakers auto, input identical to original v2 run
- T07: ok, start 2026-10-21 17:56:03, end 2026-10-21 17:56:43 (39s), speakers auto, input identical to original v2 run
- T08: ok, start 2026-10-21 17:56:43, end 2026-10-21 17:57:23 (41s), speakers auto, input identical to original v2 run
- T09: ok, start 2026-10-21 17:57:23, end 2026-10-21 17:58:01 (38s), speakers auto, input identical to original v2 run
- T10: ok, start 2026-10-21 17:58:01, end 2026-10-21 17:58:40 (39s), speakers auto, input identical to original v2 run
- T11: ok, start 2026-10-21 17:58:40, end 2026-10-21 17:59:17 (37s), speakers auto, input identical to original v2 run
- T12: ok, start 2026-10-21 17:59:17, end 2026-10-21 17:59:52 (35s), speakers auto, input identical to original v2 run
- T13: ok, start 2026-10-21 17:59:52, end 2026-10-21 18:00:34 (42s), speakers auto, input identical to original v2 run
- T14: ok, start 2026-10-21 18:00:34, end 2026-10-21 18:01:16 (42s), speakers auto, input identical to original v2 run
- T15: ok, start 2026-10-21 18:01:16, end 2026-10-21 18:01:51 (35s), speakers auto, input identical to original v2 run
- T16: ok, start 2026-10-21 18:01:51, end 2026-10-21 18:02:29 (38s), speakers auto, input identical to original v2 run
- T17: ok, start 2026-10-21 18:02:29, end 2026-10-21 18:03:08 (39s), speakers auto, input identical to original v2 run
- T18: ok, start 2026-10-21 18:03:08, end 2026-10-21 18:03:47 (39s), speakers auto, input identical to original v2 run
- T19: ok, start 2026-10-21 18:03:47, end 2026-10-21 18:04:21 (34s), speakers auto, input identical to original v2 run
- T20: ok, start 2026-10-21 18:04:21, end 2026-10-21 18:05:02 (41s), speakers auto, input identical to original v2 run
- T21: ok, start 2026-10-21 18:05:02, end 2026-10-21 18:05:30 (28s), speakers none, input identical to original v2 run
- T22: ok, start 2026-10-21 18:05:30, end 2026-10-21 18:06:09 (39s), speakers auto, input identical to original v2 run
- T23: ok, start 2026-10-21 18:06:09, end 2026-10-21 18:06:47 (38s), speakers auto, input identical to original v2 run
- T24: ok, start 2026-10-21 18:06:47, end 2026-10-21 18:07:37 (50s), speakers auto, input identical to original v2 run
- T25: ok, start 2026-10-21 18:07:37, end 2026-10-21 18:08:28 (51s), speakers auto, input identical to original v2 run
- T26: ok, start 2026-10-21 18:08:28, end 2026-10-21 18:09:11 (42s), speakers auto, input identical to original v2 run
- T27: ok, start 2026-10-21 18:09:11, end 2026-10-21 18:09:48 (38s), speakers auto, input identical to original v2 run
- T28: ok, start 2026-10-21 18:09:48, end 2026-10-21 18:10:35 (46s), speakers auto, input identical to original v2 run
- T29: ok, start 2026-10-21 18:10:35, end 2026-10-21 18:11:13 (38s), speakers auto, input identical to original v2 run
- T30: ok, start 2026-10-21 18:11:13, end 2026-10-21 18:11:51 (38s), speakers auto, input identical to original v2 run
  - ollama ps: qwen3:8b 100% GPU
- T31: ok, start 2026-10-21 18:11:53, end 2026-10-21 18:12:43 (50s), speakers auto, input identical to original v2 run
- T32: ok, start 2026-10-21 18:12:43, end 2026-10-21 18:13:20 (37s), speakers auto, input identical to original v2 run
- T33: ok, start 2026-10-21 18:13:20, end 2026-10-21 18:14:07 (48s), speakers auto, input identical to original v2 run
- T34: ok, start 2026-10-21 18:14:07, end 2026-10-21 18:14:50 (43s), speakers auto, input identical to original v2 run
- T35: ok, start 2026-10-21 18:14:50, end 2026-10-21 18:15:28 (38s), speakers none, input identical to original v2 run
- T36: ok, start 2026-10-21 18:15:28, end 2026-10-21 18:16:11 (43s), speakers auto, input identical to original v2 run
- T37: ok, start 2026-10-21 18:16:11, end 2026-10-21 18:16:56 (45s), speakers auto, input identical to original v2 run
- T38: ok, start 2026-10-21 18:16:56, end 2026-10-21 18:17:27 (31s), speakers auto, input identical to original v2 run
- T39: ok, start 2026-10-21 18:17:27, end 2026-10-21 18:18:06 (39s), speakers auto, input identical to original v2 run
- T40: ok, start 2026-10-21 18:18:06, end 2026-10-21 18:18:49 (43s), speakers auto, input identical to original v2 run
- T41: ok, start 2026-10-21 18:18:49, end 2026-10-21 18:19:28 (39s), speakers auto, input identical to original v2 run
- T42: ok, start 2026-10-21 18:19:28, end 2026-10-21 18:20:14 (46s), speakers auto, input identical to original v2 run
- T43: ok, start 2026-10-21 18:20:14, end 2026-10-21 18:20:55 (41s), speakers auto, input identical to original v2 run
- T44: ok, start 2026-10-21 18:20:55, end 2026-10-21 18:21:28 (33s), speakers auto, input identical to original v2 run
- T45: ok, start 2026-10-21 18:21:28, end 2026-10-21 18:22:04 (36s), speakers auto, input identical to original v2 run
- T46: ok, start 2026-10-21 18:22:04, end 2026-10-21 18:22:45 (42s), speakers auto, input identical to original v2 run
- T47: ok, start 2026-10-21 18:22:45, end 2026-10-21 18:23:24 (39s), speakers auto, input identical to original v2 run
- T48: ok, start 2026-10-21 18:23:24, end 2026-10-21 18:24:06 (42s), speakers auto, input identical to original v2 run
- T49: ok, start 2026-10-21 18:24:06, end 2026-10-21 18:24:49 (42s), speakers auto, input identical to original v2 run
- T50: ok, start 2026-10-21 18:24:49, end 2026-10-21 18:25:23 (35s), speakers auto, input identical to original v2 run
- T51: ok, start 2026-10-21 18:25:23, end 2026-10-21 18:26:00 (36s), speakers auto, input identical to original v2 run
- T52: ok, start 2026-10-21 18:26:00, end 2026-10-21 18:26:34 (34s), speakers auto, input identical to original v2 run
- T53: ok, start 2026-10-21 18:26:34, end 2026-10-21 18:27:09 (35s), speakers auto, input identical to original v2 run
- T54: ok, start 2026-10-21 18:27:09, end 2026-10-21 18:27:52 (43s), speakers auto, input identical to original v2 run
- T55: ok, start 2026-10-21 18:27:52, end 2026-10-21 18:28:31 (39s), speakers auto, input identical to original v2 run
- T56: ok, start 2026-10-21 18:28:31, end 2026-10-21 18:29:12 (42s), speakers auto, input identical to original v2 run
- T57: ok, start 2026-10-21 18:29:12, end 2026-10-21 18:29:48 (35s), speakers auto, input identical to original v2 run
- T58: ok, start 2026-10-21 18:29:48, end 2026-10-21 18:30:20 (32s), speakers auto, input identical to original v2 run
- T59: ok, start 2026-10-21 18:30:20, end 2026-10-21 18:30:55 (36s), speakers auto, input identical to original v2 run
- T60: ok, start 2026-10-21 18:30:55, end 2026-10-21 18:31:34 (38s), speakers auto, input identical to original v2 run
  - ollama ps: qwen3:8b 100% GPU
### v2 finished 2026-10-21 18:31:36
