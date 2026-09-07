# Handoff

- Run: `run-20260907T041550Z`
- Goal (still active): decrypt ≥5% of unresolved Liber Primus ciphertext (splits 15–70 = 12 956 runes; 5% = **648**). Known-page replays do not count. Verified new decrypt: **0 runes**.
- Resume: `export PYTHONPATH=src && python3 -m cicada validate && python3 -m cicada replay-known`

## This slice

- Method: CTR_DRBG / SPECK-SIMON / wiki2 / 2016 PGP (`EXP-LP-CTR-DRBG-001`, `EXP-LP-SPECK-SIMON-001`, `EXP-LP-SKIPAWARE-WIKI2-001`, `EXP-LP-PGP-2016-PATH-001`). Concurrent: KEYSHIFT plant failed (2/6 at n=400).
- 2016 “path lies empty” is **VALID** `7A35090F` (SHA `64ecef22…`); missing from krisyotam `pgp/messages/`. Pad/SHA/phrases **1318 / 0**.
- CTR_DRBG **7546 / 0**; SPECK/SIMON/xoroshiro128** **11154 / 0**; wiki2 **40 / 0**. Hash_DRBG / NEW-WIKI also 0.
- Verified new unsolved runes: **0**.
- Next unused angle: other iBotPeaches bodies not in the krisyotam ingest set, or an unpublished pad.

## Method verdict (this slice)

Unsolved onion 0–55 is **not** using a public key plus a solved-page or classical additive machine.

- CT IoC ≈ 0.034 (chance) → not monoalphabetic English (that would keep English IoC).
- Doublet rate ≈ 0.19× uniform → additive English (Vigenere / totient / running key / F-interrupters) is below its own floor (artwaste). Book-pad slides here confirmed that: keep-bar hits are split066 scorer junk.
- The only measured structure is the anti-repeat hole. Skip-on-doublet and skip-every-F totient/Vigenere (2 520 tests) still stay at chance IoC. They do not invert to English.

What that leaves is an **external pad or purpose-built anti-English alphabets**, neither of which is in this tree or in any retrieved signed message. That external pad is now known not to be **reused**: EXP-LP-DEPTH-KAPPA-001 measures ciphertext depth directly (894 452 pairwise alignments, 6 000 self-lags, pooled page-aligned n=303 540) and finds nothing above shuffle surrogates, while the same instrument recovers a planted shared pad 163/163 and fires at z 10.8 on the duplicated transcription runs in splits 0-14. If a pad is in play it is used once, or it is used behind the anti-repeat filter (which costs the instrument 8.6 -> 3.3 sigma). The whole Marsaglia CDROM (`bits.01`–`bits.60` plus canada/calif/germany) is now a file-aligned null: skip-aware at start-of-file, rigid at every offset (~1.89×10⁹ windows), 0 keeps. MT19937 marked seeds and the pp49 grid as a PRF seed are also null. Dukotah (2026-07-29) and artwaste reach the same wall. A new 7A35090F-signed release or the pad itself would reopen it.

## Do not treat as a decrypt

Chance skeleton runs (Quixote-10); split066 running-key TH-salad; two v2 hostnames; Hill THE/ING leftovers; NCC glyph counts.

## Do not re-run as if untested

Word-constrained / word-crib depth on the difference stream, and the keep bar as a judge of language-model output. `EXP-LP-WORD-DEPTH-001` plant-validated the first and disproved the second: a word-LM beam clears the keep bar on 38-40 of 40 shuffled ciphertexts, so trigram/IoC/vowelish say nothing about any LM search. Score against surrogates or do not score.

Ciphertext depth / coincidence (kappa) scanning in any of its forms: pairwise page alignment, self-lag periodicity, page-start or page-end pooling, and known-plaintext drag of the solved fixtures. `EXP-LP-DEPTH-KAPPA-001` closed all four with plant validation and surrogate thresholds.

`CURRENT_FRONTIER.md` in full, including skip-aware SHA-CTR / totient / Vigenere / PGP-body / MT19937 / payload49 / RC4 / ChaCha20 / HKDF / R12-C2 / CAS-book beams and the full Marsaglia file-aligned slide (plants recover; real pages do not).

## Highest-value next

0. **DONE — EXP-LP-WORD-SKIP-001, EXP-LP-WORD-LOCAL-TOTIENT-001, EXP-LP-WORD-CHAIN-AK-001, EXP-LP-WORD-END-KEYSKIP-001, EXP-LP-F-KEYSKIP-001, EXP-LP-SECTION-KEYSKIP-001.** Word-parse skip-aware beam, totient/reverse/columnar-then-totient at word boundaries, previous-word running key, rigid extra key consumes at known word ends/starts, after CT-F / CT-doublet, and at red-section / page-join boundaries (7632 tests, 0 keeps): all plant, all null on unsolved. Word lengths still do not pin a rune without an unpublished pad.

1. A seed **not** in the tested skip-aware lists. Subtract, add, and Beaufort skip-aware inverses are plant-validated on the short attested set **and** on the motivated CAS pads (KJV/Shakespeare/wiki/bits.01/plains). All null. Chaocipher-29 on attested alphabets is also null (plant 1.0). μ/ω/Ω/λ/σ and Solitaire/Pontifex skip-aware are null (plant 0.89). CT-autokey / previous-letter tableau is excluded by cond-prev IoC 0.0354. Marked-seed xorshift32 / xoroshiro64** / PCG / Galois LFSR is null (`EXP-LP-XORSHIFT-PCG-001`; 1496 tests). ISAAC and high-bit extracts of those PRNGs are also null (`EXP-LP-ISAAC-HIGHBIT-001`; 1430 tests). Marsaglia KISS99 / MWC / CMWC marked seeds are also null (`EXP-LP-KISS-MWC-001`; 28688 tests, 0 keeps). Geffe + shrinking LFSR marked seeds are also null (`EXP-LP-GEFFE-SHRINK-001`; 572 tests). Nihilist-29 is also null (`EXP-LP-NIHILIST-29-001`; 540 tests). Salsa20/20 + SHAKE256-XOF marked seeds are also null (`EXP-LP-SALSA20-SHAKE-001`; 14344 tests, 0 keeps). Java.util.Random / glibc TYPE_0 / SplitMix64 marked seeds are also null (`EXP-LP-JAVA-GLIBC-SPLITMIX-001`; 17952 tests, 0 keeps). Trifid-27 + Phillips-29 are also null (`EXP-LP-TRIFID-PHILLIPS-001`; 2268 tests). VIC packed-rune + ADFGX-25 are also null (`EXP-LP-VIC-ADFGVX-001`; 1561 tests; 162 salad keeps, 0 English). Rule 30 64-bit cyclic CA is also null (`EXP-LP-RULE30-001`; 7216 tests). Rule 30 + xoshiro256** marked seeds are also null (`EXP-LP-RULE30-XOSHIRO-001`; 4642 tests). Bazeries cylinder-29 + Fleissner grille are also null (`EXP-LP-BAZERIES-GRILLE-001`; 4319 tests). Fractionated Morse is also null (`EXP-LP-FRAC-MORSE-001`; 324 tests). HMAC-DRBG SHA-256 is also null (`EXP-LP-HMAC-DRBG-001`; 7216 tests). Hash_DRBG SHA-256 is also null (`EXP-LP-HASH-DRBG-001`; 3938 tests). CTR_DRBG AES-128/256 is also null (`EXP-LP-CTR-DRBG-001`; 7546 tests). SPECK/SIMON/xoroshiro128** are also null (`EXP-LP-SPECK-SIMON-001`; 11154 tests). Unused wiki pads (Sefer Yetzirah / Gematria / Agrippa / Soyga / Dee / …) are also null (`EXP-LP-SKIPAWARE-NEW-WIKI-001`; 32 tests). Kabbalah/Thelema/Enochian wiki pads are also null (`EXP-LP-SKIPAWARE-WIKI2-001`; 40 tests). The 2016 VALID “path lies empty” body is also null as pad/SHA/phrases (`EXP-LP-PGP-2016-PATH-001`; 1318 tests). Known-shift CT-crop depth does not majority-plant at page length (`EXP-LP-SKIPAWARE-DEPTH-PAGESHIFT-001`). Key-consumption T-crop also fails majority at n≤277 (`EXP-LP-SKIPAWARE-DEPTH-KEYSKIP-001`). Hill φ-entry book matrices are also null (`EXP-LP-HILL-PHI-BOOK-001`; 864 tests). ChaCha8/12 marked seeds are also null (`EXP-LP-CHACHA8-12-001`; 7876 tests). xorshift128+ / WELL512a / omitted titles are also null (`EXP-LP-XORSHIFT128-WELL-001`; 4328 tests). Same-start n=400 section/chunk depth is family-wise null (`EXP-LP-SKIPAWARE-DEPTH-SECTIONS-001`). A new signed body or unpublished pad is still the reopening artifact.
1b. Common Crawl + Wayback URL-index search for a new `7A35090F` body: no captures under fp/cicada/liber wildcards. Prefix pastebin CDX is either timestamp junk or 504. Not a full-text crawl.
1c. Today’s GitHub “solves” (27×27 10-word route; empty BOOK.MD; Leo exclusion ledger) are not executable 648-rune decrypts. Do not replay as if they were.
2. Skip-aware at arbitrary Marsaglia or book-pad offsets (infeasible here).
3. Dee *Hieroglyphic Monad*: **text now on allowlist** (`archive.org/download/monas-hieroglyphica` DjVuTXT, 38 642 runes). Skip-aware pad + SHA3/BLAKE2 CTR is null (`EXP-LP-SKIPAWARE-SHA3-DEE-001`).
4. A control-valid image–glyph overlay (projection, drop-cap, NCC, and rune-height line-class all failed p56/57). Line-class is closer (84/85 and 94/95) but first-red heading lengths do not lock to 5 and 7 under one filter.
5. A new 7A35090F-signed message or an unpublished pad.
5b. **DONE — EXP-LP-WORD-DEPTH-001.** The stronger model was not a higher-order n-gram: word boundaries are not encrypted (verified against the solved plaintexts), so a depth candidate must make both streams parse into real words at once. Cascade Markov-D -> exact bigram forward HMM -> joint word-LM beam. Real disjoint Cicada plaintext at n=242 scores z 5.93 against a measured family-wise threshold of 5.10, and an end-to-end cascade plant is found at rank 1 inside the real page set. Observed max over 894 452 alignments is 4.07. A single reused-pad pair with overlap >= 200 runes is excluded. Detection floor: z 5.50 at n=200, 4.21 at n=150, 2.60 at n=100 — overlaps below ~180 runes are still open, and so is depth behind the anti-repeat filter.
5c. **DONE at the n=400 same-start instrument — EXP-LP-SKIPAWARE-DEPTH-SECTIONS-001.** Match/gap forward plants on reject-filtered same-start pads at n=400 (6/6). Scan of 8 red-section 400-rune heads/tails (240 dirs) and 32 book chunks (992 dirs): observed max 2.23 / 2.59 **below** 4-surrogate max 5.04 / 3.47. Pair-local top-8 seps are look-elsewhere. Shifted reuse still fails at page length (PAGESHIFT / KEYSKIP). Latin recovery of 057/rev059 remains null. Remaining open: a stronger-than-forward statistic, or an unpublished pad.
6. Do not mark 5% complete without 648 verified newly decrypted unsolved runes.

Page 56 remains 85/85 under `totient_prime_skip_4th_ct_f` only.
