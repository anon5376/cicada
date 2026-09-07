# Hypotheses

Updated: 2026-09-07T20:10:00Z

## LP-HYP-000001

- Claim: unresolved LP2 pages use a mechanism already demonstrated on a solved page (direct, atbash, atbash+3, totient-prime, or Vigenere on a short historically attested key list).
- Motivation: cheapest discriminating transfer test.
- Status: FAILED_WITHIN_TESTED_SCOPE on rtkd splits 15–17 (`EXP-LP-TRANSFER-split015` / `016` / `017`).
- Falsification: none of the listed methods produce English-like output under the preregistered uncalibrated threshold. That does **not** falsify Vigenere in general.

## LP-HYP-000002

- Claim: remaining pages are one-time-pad-class relative to publicly available key material.
- Status: SPECULATIVE as a global claim. The measured doublet deficit is compatible with a filter over a high-entropy stream, but does not identify the stream.

## LP-HYP-000003

- Claim: split_015 is Caesar, atbash+Caesar, or totient-prime with start offset 0–29.
- Status: FAILED_WITHIN_TESTED_SCOPE (`EXP-LP-CAESAR-TOTIENT-OFFSET-001`, 88 candidates).

## LP-HYP-000004

- Claim: unsolved pages are Vigenere/Beaufort against recovered LP1 plaintext as a running key.
- Status: FAILED_WITHIN_TESTED_SCOPE (2305-rune keystream, 8 relations, chance-like scores).

## LP-HYP-000005

- Claim: the 15.jpg C-grid, in some geometric reading order, is a repeating mod-29 key for onion 15 or neighbors.
- Status: FAILED_WITHIN_TESTED_SCOPE (`EXP-LP-PAGE15-CRIB-001`). The C values themselves are independently reproduced.

## LP-HYP-000006

- Claim: a short Cicada-semantic seed through SHA-256-CTR (no anti-repeat model) decrypts the unsolved prefix.
- Status: FAILED_WITHIN_TESTED_SCOPE (40 seeds, 468 configs). Does not close other KDFs, counter encodings, or skip-aware decoders.

## LP-HYP-000007

- Claim: unsolved section openings use a solved-page heading cipher (atbash / totient / DIVINITY / Caesar).
- Status: FAILED_WITHIN_TESTED_SCOPE (1980 heading tests, 0 vocabulary hits).

## LP-HYP-000008

- Claim: the 2014 signed hash-block or other held PGP bodies are a pad / CTR seed for the unsolved stream.
- Status: FAILED_WITHIN_TESTED_SCOPE (`EXP-LP-PGP-HASHBLOCK-001`).

## LP-HYP-000009

- Claim: the shared Ghostscript ICC/DQT, or the pp49–51 grid after the four bar-height token edits, is an additive key.
- Status: FAILED_WITHIN_TESTED_SCOPE (`EXP-LP-GRID-ICC-HEADING-001`).

## LP-HYP-000010

- Claim: unsolved pages are Playfair 5×6 or Bifid on an attested Cicada word, or keyless delta/cumsum of the ciphertext.
- Status: FAILED_WITHIN_TESTED_SCOPE (`EXP-LP-PLAYFAIR-BIFID-HEADING-001`, `EXP-LP-DELTA-SKELETON-LSB-001`).

## LP-HYP-000011

- Claim: unsolved word-length sequences match KJV, Milton, Alice, Liber AL, Moby-Dick, or a 1.6 MB Latin corpus (letterwise).
- Status: FAILED_WITHIN_TESTED_SCOPE (max exact run 9 on KJV; 7 on Latin).

## LP-HYP-000012

- Claim: the AN END leftover 352 bits, or the 2012/2013 “never-used” hint strings, are a CTR/AES key for the unsolved stream.
- Status: FAILED_WITHIN_TESTED_SCOPE. The two v2 hostnames are a measurement, not a retrieve.

## LP-HYP-000013

- Claim: page-57 isolated-rune NCC yields control-valid heading lengths on pages 56/57.
- Status: FAILED_WITHIN_TESTED_SCOPE (`EXP-LP-NCC-TEMPLATE-001`).

## LP-HYP-000014

- Claim: Shakespeare, the English Quran JSON, or the Cicada OS wisdom/folly blob decrypts the unsolved stream (skeleton or CTR/AES).
- Status: FAILED_WITHIN_TESTED_SCOPE.

## LP-HYP-000015

- Claim: foursquare on attested Cicada words opens the unsolved prefix or section 0–2.
- Status: FAILED_WITHIN_TESTED_SCOPE (240 pairs).

## LP-HYP-000016

- Claim: the anti-doublet rule is applied per word (or per line), resetting at the
  transcribed `-` / `/` boundaries, so a word-local encoder would explain the 86
  surviving doublets as boundary pairs left at chance.
- Motivation: 86 observed is close to the ~99 that a word-local rule predicts, and the
  pooled statistic used by every prior experiment cannot distinguish the two.
- Status: **FAILED** (`EXP-LP-BOUNDARY-DOUBLET-001`). Cross-word pairs are suppressed
  at ratio 0.238 (z −7.32) and cross-line at 0.228 (z −3.28), indistinguishable from
  the within-word 0.183. The rule is stream-level.
- Falsification: decisive for word/line resets. Does not exclude a reset at some
  boundary the transcription does not mark (page start, section start, stanza).

## LP-HYP-000017

- Claim: the encoder enforced the rule by nudging its own output (`c := c+1` when the
  output would repeat), the cheapest rule a human scribe could apply at the page.
- Status: **FAILED** (`EXP-LP-BOUNDARY-DOUBLET-001`, −16.7σ). The missing mass does not
  land on d = +1; it spreads uniformly over d ≠ 0, which is the key-advance signature
  already assumed by `encrypt_reject`.
- Falsification: decisive for the +1 nudge and, by the same statistic, for any fixed
  nudge to a single difference. Does not exclude a nudge drawn from the key.

## LP-HYP-000018

- Claim: the anti-doublet rule is a Cicada-wide convention that also governs the solved
  pages.
- Status: **WEAKENED** (`EXP-LP-BOUNDARY-DOUBLET-001`). Page 56, the only verified
  polyalphabetic solved page, carries 2 ct doublets in 84 pairs against λ = 0.56 under
  the filter, P(X≥2) = 0.109. Suggestive, not an exclusion at n = 84.
- Consequence if true: pages 0–55 use a different mechanism from page 56, and the
  filter is a property of the unsolved section specifically.
