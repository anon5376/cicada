# Discoveries

Updated: 2026-09-07T20:10:00Z

No verified new Liber Primus decryption is claimed. Progress toward 5% of unknown: **0 / 648 runes**.

## Doublet deficit on unresolved pages — REPRODUCED measurement

- Claim: rtkd splits hypothesized as onion 0–55 have far fewer adjacent repeated runes than an iid uniform 29-symbol model.
- Observation: 86 doublets / 12901 pairs vs ~445 expected (ratio ≈ 0.19).
- Record: `reports/candidates/doublet_constraint.json`
- Novelty: UNKNOWN (already discussed in public solver writeups).
- Not a plaintext and not a proof of a one-time pad.

## Anti-doublet rule is stream-level and lag-1 only — VERIFIED measurement

- Claim: the lag-1 doublet deficit on splits 15–70 ignores transcribed word and line
  boundaries, and does not extend to lag 2.
- Observation (2000 within-page shuffles as the null): within-word 60/9640 ratio 0.183
  (z −14.59), across `-` 21/2588 ratio 0.238 (z −7.32), across `/` 4/515 ratio 0.228
  (z −3.28). Lags 2 and 3 pooled z −0.12 and −0.08.
- Consequence: a per-word or per-line encoder reset is excluded. The pooled count (86)
  could not have shown this — a word-local rule predicts ~99, which is *closer* to the
  observed total than a stream-level rule would naively suggest. Only the class split
  separates them.
- Record: `experiments/EXP-LP-BOUNDARY-DOUBLET-001/result.json`
- This validates, for the first time by measurement rather than assumption, the
  `encrypt_reject` stream model used by every skip-aware beam in this tree.
- Not a plaintext.

## Output-nudge enforcement excluded; key-advance survives — VERIFIED measurement

- Claim: the 353 missing doublet pairs redistribute uniformly over the 28 nonzero
  first differences, not onto d = +1.
- Observation: `c := c+1` on collision predicts d=+1 at ~798, observed 456 → **−16.7σ**.
  Key-advance/resample predicts ~458, observed 456 → −0.09σ.
- Residual non-flatness (chi² p 0.032, family-wise max|z| p 0.038 at d=9) **fails
  split-half replication**: cross-half correlation of the 28 residual z-scores is
  +0.061 and the best cell moves (d=2 / d=13), while d=0 replicates at −11.96 / −12.22.
  Recorded as noise, not structure.
- Record: `experiments/EXP-LP-BOUNDARY-DOUBLET-001/result.json` parts 2–4.
- Not a plaintext.

## Page 56 does not show the filter — DISCOVERY CANDIDATE

- `lp2.page56_an_end` is the only solved page that is both polyalphabetic and verified
  85/85. Its ciphertext has **2** doublets in 84 pairs against λ = 0.56 under the
  unsolved-page filter rate: P(X≥2) = 0.109.
- The other three fixtures cannot test this: two are `direct` (no cipher) and one is
  `atbash` (monoalphabetic — a reject rule would break the bijection).
- Weak evidence that the anti-doublet rule is **specific to the unsolved section**
  rather than a Cicada-wide convention. Not an exclusion at n = 84. If it holds, the
  pages 0–55 mechanism is not the page-56 mechanism.
- Promotion requires another verified polyalphabetic Cicada page, which does not
  currently exist.

## 2013 book-code copy damage — DISCOVERY CANDIDATE

krisyotam `2013-01-opening-book-code.asc` is INVALID as stored; VALID after inserting the RFC blank line after `Hash:`.

## 15.jpg number square — REPRODUCED measurement

rtkd split_030 contains the printed 4×4 grid. Values equal community C = |3301 − (A+1)th prime| for A = 0,1,2,3,5,…,987. Image 15.jpg (SHA-256 `5543cfce…`) shows 3299 in red and an infinity mark. Using C as a repeating key in several reading orders does not decrypt the page. Not a plaintext.

## Page 56 F-skip rule — REPRODUCED

Fourth ciphertext F only (index 56). Full plaintext:
`ANENDWITHINTHEDEEPWEBTHEREEXISTSAPAGETHATHASHESTOITISTHEDVTYOFEVERYPILGRIMTOSEECOVTTHISPAGE`
Command: `python3 -m cicada replay-known`. Not unknown-page decrypt.

## Red-ink section map — VERIFIED measurement

All 58 onion JPEGs measured. Substantial red on 0, 3, 6–8, 15, 23, 27, 33, 39, 40, 53, 54, 56, 57. Record: `experiments/EXP-LP-RED-INK-001/red_map.json`. Matches the community “rubricated incipit” sectioning. Using recovered openings as section keys did not decrypt the bodies.

## p53 51-rune word-shape crib — located in this transcription

rtkd split_068 tail words have rune lengths (5,4,4,11,2,3,2,6,5,5,2,2), matching artwaste’s longest red passage. Located only. Not decrypted.

## scream314 05.jpg trailer — DISCOVERY CANDIDATE

72 700 post-EOI bytes, entropy ≈ 6.90 bits/byte, gzip magic at +602 is a false positive.
Do not treat this file as original for steganography.

## AN END 5×8 hex → two v2 hostnames — REPRODUCED measurement

Concatenating the first eight hex digits of each printed hash line yields 20 bytes. RFC 4648 base32 is `gy3hoy2zizvuzvdbrxxemt626fcwretk`. The first 16 characters match the published `gy3hoy2zizvuzvdb` claim; the second 16 are `rxxemt626fcwretk`. This is not a retrieval and not a decrypt. v2 is retired; this lab does not probe onions. Leftover 44 bytes as a local key: no English.

## Shared Ghostscript ICC/DQT — REPRODUCED measurement

Onion JPEGs 0, 15, 49, 56, 57 all embed the same 2576-byte ICC (SHA-256 `942e0f66212eb8ad252706559da5007d893d7350652704f8d115d5e6074479d0`, header `acspAPPL`) and the same 130-byte DQT (SHA-256 `0f81986f36a37e1309c4d4d18e2c4c6966ad7c49385ef79cbcc0bbef3ccb7a2e`). Matches artwaste’s single-render claim. Used as keys: no English. Not a plaintext.

## pp49–51 four token locations — REPRODUCED on this transcription

rtkd tokens at indices 45=`1L`, 50=`0L`, 165=`0l`, 246=`3i` are exactly the four artwaste named. Applying `1l`/`0l`/`0I`/`3I` changes the base-60 blob SHA-256. Independent bar-height measure was not completed here (no scipy). Corrected bytes as a key: no English.

Items that may later be promoted, if they survive review:

- None at discovery-candidate rank yet beyond infrastructure findings (key-byte fingerprints, successful historical replays of already-public methods).

## Marsaglia CDROM slice — acquisition only

All 60 `bits.*` files plus `canada.bit` / `calif.bit` / `germany.bit` from jeffThompson/DiehardCDROM are in CAS. File-aligned skip-aware and rigid slides are null. Not a decrypt. First six hashes:

| file | SHA-256 |
| --- | --- |
| bits.01 | `32d18ec597c9bbc40791a039d1a217a0cd5db322db400b095f9e85c708e479f7` |
| bits.15 | `ab20e9e98c337fbd4cee4aa3fa0ab7c765a7c9c61bb2fd966f6f7291eb8d2097` |
| bits.33 | `7267739e21656180a094202e19b2d830978eebac4889989af1629107b017791b` |
| bits.56 | `da0dc1b7c8ebae90b7b2559489cb7e6ebc77f21e75ad51cbbe70438ae8c30683` |
| canada.bit | `6e4b4364cfbddb0f5ba479851ec1403771a49198775928d487f819f9ec63f735` |
| calif.bit | `cf58e4590e8df99e4a46f28abafea43b23fe74e429d27f24ffe698cbb63a75a6` |

Infrastructure findings are recorded in AUTHENTICITY_LEDGER.md and SOLVED_STAGES.md. They are not novel solutions.

## rtkd splits 0-14 contain duplicated transcription runs -- MEASURED

Found as the instrument control for `EXP-LP-DEPTH-KAPPA-001`, not as a decryption. Longest common rune run between split pairs in the early region: **split004/split006 = 40**, **004/005 = 37**, **005/006 = 29**, 009/010 = 17. The 009/010 run is `MOSTTHNGSARENOTWORTH` at 009 offset 73 and 010 offset 0 (009 continues `CONSVMNG…`, 010 continues `PRESERVNG…`) — not a page-end join. Splits 4/5/6 overlap mutually at three different offsets.

In the unsolved region the same scan gives a maximum common run of **5 runes** between any pair of splits 15-70 (4 between adjacent ones), which is what chance gives for 29 symbols at these lengths. So the duplication is confined to the early region and the 12 956-rune unsolved count is **not** inflated by it. That matters because the 5% gate (648 runes) is computed from that count. Three of the 56 unsolved splits fall under the 80-rune bar: split064 (66), split065 (**0**), split070 (76).

Not novel cryptanalysis. It is a transcription property that any depth, Kasiski or n-gram search over the rtkd master will trip over, and it is why the early splits must be held out of a pad-reuse scan.

## Word boundaries survive the cipher — VERIFIED on solved pages

The rtkd transcription marks words with `-`, and those separators are **not** enciphered. Checked against the replayed plaintexts: page 56's ciphertext word lengths are 2,3,5,2,4,3,4,6,1,4,3,6,2,2,2,2,4,2 and its plaintext is AN(2) END(3) WITHIN(5) THE(2) DEEP(4) WEB(3) THERE(4) EXISTS(6) A(1) PAGE(4) THAT(3) HASHES(6) TO(2) IT(2) IS(2) THE(2) DVTY(4) OF(2) — an exact match once TH, NG, EO, AE, IA and EA are counted as single runes. The same holds for the other three fixtures.

Consequence: every unsolved page ships a free, unencrypted structural constraint. Splits 15-70 contain **2 928 words**, mean length 4.42 runes, with a length histogram (99 of length 1, 465 of 2, 726 of 3, 514 of 4, 318 of 5, ...) that matches English. Any additive-cipher hypothesis must produce a plaintext that parses into exactly those lengths as real words. `EXP-LP-WORD-DEPTH-001` is the first experiment here to use that; it is a constraint available to every future family, not just depth.

Second, methodological: a beam decoder that maximises an English word model **manufactures** keep-bar English from anything. Shuffled ciphertext put through the stage-3 beam clears n>=80 / trigram>=3.5 / IoC>=0.045 / vowelish 0.28-0.55 on 38-40 of 40 outputs. The keep bar cannot be used to judge the output of any language-model search; only a calibrated score against surrogates can.
