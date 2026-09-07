# Current frontier

Assessment time: `2026-09-07T21:00:00Z`
Scope phrase: **Latest located and verified within the documented search coverage.**

This document distinguishes checked evidence from inherited community claims.
It is not a proof that later messages, private stages, or unpublished solutions do not exist.

## Numbering conventions in play

These systems are **not** silently merged.

1. **rtkd master transcription splits** — file SHA-256
   `e21743ccd9a07f3845d52a329c61b9fa69e9ca6a44ee3ba0db8f28a0d7065004`,
   delimiter `%`. This run: **74** chunks, **72** with runes.
2. **LP2 onion filenames** — `liber-primus__images--unsolved/{0..57}.jpg`.
   All **58** JPEGs retrieved.
3. **scream314 `liber-primus-complete` names** — mixed early-2014 tree.
   `05.jpg` in that tree has 72 700 trailing bytes after JPEG EOI and is not
   treated as original page bytes.

**Alias hypothesis (STRONGLY SUPPORTED on three checkpoints):**
`rtkd split_index = 15 + onion_index`.

- split_015 begins with the wiki `0.jpg` prefix (U+16CB U+16BB U+16D6 U+16A9 U+16B7 U+16D7 U+16E1 U+16A0).
- split_071 contains the page-56 fixture prefix (85 runes).
- split_072 contains the page-57 fixture prefix (95 runes).
- 15+56=71 and 15+57=72.

Image-to-glyph overlay has **not** been completed, so the alias is not VERIFIED
for every intermediate page.

Gematria mapping: `mapping-v1-wiki-2026-09-07`, alphabet size **29**.
Index and prime value are distinct fields.

## Search coverage

Performed: web search (2026-09-07); GitHub API + raw GET; isolated GnuPG 2.5.22.

Not performed: full-text Common Crawl (URL-index only; 0 fp/cicada captures), full social archives, live onion services.

Failures: Fandom GET 403; iddqd `transcription--full` 404.
87 blobs stored.

## Latest communication actually verified

**AUTHENTICATED** (GnuPG `VALIDSIG`) under primary fingerprint computed from key bytes:

`6D854CD7933322A601C3286D181F01E57A35090F`

User ID on object: `Cicada 3301 (845145127)`.
Key packet timestamp: `1325734783` (2012-01-05T03:39:43Z).

| Message | SHA-256 | Result |
| --- | --- | --- |
| 2012-01-key-announcement.asc | `ce6c44a4c3daf6d5b3691f8894ddb59b10ab58514ce1a2e692caf9b86af7142a` | VALID |
| 2014-05-liber-primus-release.asc | `967990fd9415a13d18830e4159d8228b4c3ef443b712c293d56f04a28415cb18` | VALID |
| 2017-04-final-message.asc | `bb36c3c1c570ece6fb0db94c35a45d67f6a9b3a54675b6ced9aae2c8c5ee3990` | VALID |
| 2017-04-final-warning.asc | `c0e4adbd8aab8e85e9976d6a06c889d415e83cf1e76a0f8b56cad10406eea800` | VALID (same text, different stored bytes) |
| 2016-hello-the-path-lies-empty.asc | `64ecef22f91bea9fba0742cec8d28c1da8daa1c8565bfbf5d640b506f06cf5ce` | VALID (missing from krisyotam `pgp/messages/`; iBotPeaches + krisyotam solver copy) |

20 krisyotam messages VALID as stored. One stored-invalid:
`2013-01-opening-book-code.asc` — missing blank line after `Hash:`; VALID after that labeled repair.

Latest retrieved VALID body: “Beware false paths. Always verify PGP signature from 7A35090F.”
No newer signed bytes in the searched sources.

Short ID `7A35090F` is not the anchor. iBotPeaches filename `67F363C6…` is a different
blob that still imports as `6D854CD7…`.

## What “solved” means here

| Target | Method | This run |
| --- | --- | --- |
| lp1.warning (184 runes) | atbash | REPRODUCED_FROM_RECONSTRUCTION |
| lp1.wisdom (157) | direct | REPRODUCED_FROM_RECONSTRUCTION |
| lp2.page57 (95) | direct | REPRODUCED_FROM_RECONSTRUCTION |
| lp2.page56 | totient p−1, skip 4th ciphertext F | REPRODUCED_FROM_RECONSTRUCTION 85/85 |
| page 56 hash instruction | downstream | not attempted |
| onion 0–55 / splits 15–70 | decryption | unresolved |
| 2012/2013 stego | community-solved | DOCUMENTED_NOT_REPRODUCED (no OutGuess) |

## Structure of unresolved pages (measurement)

On rtkd splits hypothesized as onion 0–55 (splits 15–70; 12 956 runes, 12 901 adjacent pairs):

- mean IoC ≈ **0.0340** (chance for q=29 is ≈ 0.0345)
- observed doublets **86** vs ≈ **445** expected if iid uniform (ratio ≈ **0.19**)
- early solved-style splits 0–14: mean IoC ≈ 0.056, mean doublet ≈ 0.026

**VERIFIED as a measurement on this transcription.** This is not a decryption.
Novelty UNKNOWN (community writeups already discuss anti-repeat / doublet deficit).
It does not prove a one-time pad.

## Experiments executed

| ID | Domain | Result |
| --- | --- | --- |
| EXP-LP-TRANSFER-split015/016/017 | solved-page method transfer | 12 methods × 3 pages, 0 threshold hits |
| EXP-LP-TRANSFER-ALL-UNSOLVED | same 12 methods × splits 15–70 | 0 hits |
| EXP-LP-CAESAR-TOTIENT-OFFSET-001 | Caesar 0–28, atbash+Caesar 0–28, totient offsets 0–29 on split 15 | 88 candidates, 0 hits |
| EXP-LP-UNKNOWN-NEXT-001 | LP1 running-key; SHA-256-CTR semantic seeds; heading transfer; Hill 2×2 on p53 crib | 0 verified plains. Hill “THE/ING” hits are 51-rune scorer artifacts (IoC still ~0.034). |
| EXP-LP-PAGE15-CRIB-001 | 15.jpg C-grid reading orders as Vigenere; p53 word-shape dictionary fill | square C matches claimed Fibonacci recipe; page-order/spiral/infinity keys 0 English. Implied crib keystreams ~7% period agree (chance). |
| EXP-LP-ACROSTIC-UNSOLVED-001 | first/last rune and first-word streams of splits 15–70 | best tri=7.46 on 56-rune Caesar search; not readable English |
| EXP-LP-PAYLOAD49-AS-KEY-001 | rtkd 256-token grid → base-60 bytes 0–255 as repeating key | 12 configs on the concatenated unsolved stream, 0 hits |
| totient skip_pt_F / skip_ct_F | all unsolved pages, starts {0,1,onion,56−onion} | 660 tests, 0 hits |
| EXP-LP-ANEND-HASH-001 | 128-hex AN END block as repeating key and SHA-256-CTR seed | 151 configs, 0 hits. Page 56 itself now 85/85. |
| EXP-LP-TOTIENT-SKIP-FIB-001 | skip Nth CT-F totient on every unsolved page; Fibonacci–prime meshes | 416 tests, 0 hits |
| EXP-LP-RED-INK-001 | red-pixel map of all 58 onion JPEGs | section openings at 0,3,8,15,23,27,33,40,53,54 (+56,57). Speck-only red on several others. |
| EXP-LP-HEADING-SECTION-KEY-001 | decrypt red openings; use as Vigenere key for that section | 26 wordish heading guesses, 114 body tests, 0 hits |
| totient per red section | totient / skip-1 / skip-4 on each section concat | 27 tests, 0 hits |
| EXP-LP-GLYPH-OVERLAY-001 | line-projection red/black glyphs | **failed controls**: p56 counted hex as glyphs (203 vs 85); p57 first red run 4 ≠ 7. Not used as heading truth. |
| EXP-LP-HILL-WISDOM-001 | Hill 5×5 from LP1 wisdom square; Hill 4×4 from 15.jpg C; 3×3 corners | all invertible; 132 page/prefix tests, 0 keeps. pp49/51 rune headers 0 heading-vocab hits. |
| EXP-LP-IMAGE-SHA-SEED-001 | SHA-256 of each onion JPEG as page-local CTR; 15/56/0/xor/grid ascii as book seeds | 516 tests, 0 hits |
| EXP-LP-PGP-HASHBLOCK-001 | 2014 hash-block + other signed bodies as pad/CTR | 25 tests, 0 keeps |
| EXP-LP-GRID-ICC-HEADING-001 | artwaste 4-token grid fix; shared ICC/DQT as seeds; drop-cap heading CC | grid+ICC/DQT 0 keeps. Heading CC **failed** p56/57 controls |
| EXP-LP-PLAYFAIR-BIFID-HEADING-001 | Playfair 5×6 + Bifid {5,10,15,29} on attested keys | 269 tests, 0 keeps |
| EXP-LP-DELTA-SKELETON-LSB-001 | keyless delta; word-length skeleton vs solved plains + wiki/Alice; JPEG LSB | 0 decrypts. Alice 8-word run is chance. LSB channel collapsed |
| EXP-LP-SKELETON-KJV-001 | word-length slide vs full KJV + Paradise Lost | max exact run 9; 0 at ≥10. Not those texts |
| EXP-LP-NCC-HEADING-SKEL-001 | drop-cap 114px split; Moby/Enoch/Hermetica/AL skeleton | headings still fail p56/57; max skel run 8 |
| EXP-LP-SKELETON-LATIN-001 | letterwise Latin vs Caesar/Livy/Vergil/Ovid | max run 7 |
| EXP-LP-ANEND-SPLIT-AES-001 | 5×8 hex → two v2 hosts + 44 B leftover as AES/CTR | onion derivation reproduced; leftover 0 keeps |
| EXP-LP-NEVERUSED-HINTS-001 | 2012 P.S. / 2013 cookies / missing primes as CTR | 13 tests, 0 keeps |
| EXP-LP-NCC-TEMPLATE-001 | NCC of 16 isolated p57 rune templates | no threshold matches 56/57 glyph/red controls |
| EXP-LP-SHAKE-QURAN-WISDOM-001 | Shakespeare/Quran skeleton; OS wisdom/folly CTR | max skel run 8; wisdom is 3368 B noise, 0 keeps |
| EXP-LP-FOURSQUARE-WISDOM-AES-001 | Foursquare 5×6 attested pairs; AES wisdom blob | 240 foursquare 0 keeps; AES ASCII ~0.37 |
| EXP-LP-TWOSQUARE-INK-SKEL-001 | two-square + slidefair; ink-density keys; Ulysses/Quixote/Canterbury/Kafka skeleton | 180 pair tests 0 keeps; ink 0 keeps; Quixote 10-word run on split 56 is chance (ks IoC 0.033) |
| EXP-LP-AUTOKEY-PORTA-SKEL-001 | autokey/Beaufort/Porta-29/Nicodemus/word-reset/Trithemius; Faust/Tao/Nag Hammadi skeleton | 13 305 cipher tests, 0 keeps; skel max run 8 |
| EXP-LP-RUNKEY-PRIMER-CGRID-001 | Faust/Alice/Inferno running-key slide; page primers; C-grid autokey/Porta | ~20 M windows; 2 TH-salad scorer artifacts, 0 decrypts; primer 2115 / cgrid 1512, 0 keeps |
| EXP-LP-KJV-RUNNING-KEY-001 | first 220 k runes of KJV / Shakespeare / Paradise Lost as sliding Vigenere pads | 486 jobs; 5 keep-bar hits, all on short split066, unreadable; 0 decrypts |
| EXP-LP-GROMARK-QUAGMIRE-001 | Gromark running-adders (12 primers + mixed) and Quagmire I/III | 18 696 tests, 0 keeps |
| EXP-LP-TOTIENT-VIG-MESH-001 | totient then Vigenere/Beaufort/Porta; totient-after-Vigenere | 5 280 tests, 0 keeps |
| EXP-LP-QUIXOTE-MOBY-RUNKEY-001 | first 220 k runes of Quixote / Moby-Dick as sliding pads | 324 jobs; 2 split066 scorer artifacts; 0 decrypts |
| EXP-LP-AES-PW-SOLVED-PORTA-001 | AES-CTR under SHA-256(password); solved plains as Porta/Nicodemus; Kafka pad | 107 tests + Kafka slide, 0 keeps |
| EXP-LP-COMPOSE-ATBASH-TOTIENT-001 | atbash∘totient, totient∘atbash, skip-4 mixes, atbash∘Vigenere | 1 210 tests, 0 keeps |
| EXP-LP-ULYSSES-CANTERBURY-RUNKEY-001 | Ulysses / Canterbury 220 k-rune sliding pads | 324 jobs; 5 split066 artifacts; 0 decrypts |
| EXP-LP-ANTIREPEAT-SKIP-001 | totient/Vigenere skip-on-doublet and skip-every-F | 2 520 tests, 0 keeps |
| EXP-LP-SKIPAWARE-SHA-CTR-001 | filter-aware beam on SHA-256-CTR seeds (plant recovers 81/81) | 200 seed/page tests, 0 keeps |
| EXP-LP-SKIPAWARE-TOTIENT-001 | totient/prime/fib streams through the same beam (plant 97.8%) | 334 tests, 0 keeps |
| EXP-LP-SKIPAWARE-VIGENERE-001 | attested repeating keys through the same beam (plant DIVINITY 96.3%) | 990 tests, 0 keeps |
| EXP-LP-SKIPAWARE-CORPUS-SEEDS-001 | skip-aware SHA-CTR on AN END / ICC / DQT / plains / warning / page-local JPEG SHA | 77 tests, 0 keeps |
| EXP-LP-TRAILER-WORDSUM-001 | scream314 05.jpg trailer as beam pad/seed; word prime-sum self-key | 220 tests, 0 keeps |
| EXP-LP-SKIPAWARE-PGP-BODIES-001 | skip-aware SHA-CTR on every stored PGP body and blob SHA | 88 tests, 0 keeps |
| EXP-LP-SKIPAWARE-MARSAGLIA-001 | skip-aware beam on Marsaglia bits.01/15/33/56 + canada/calif (byte%29, 5-bit, file SHA, HMAC-fp) | plant 1.0; 288 tests, 0 keeps |
| EXP-LP-MARSAGLIA-RIGID-SLIDE-001 | rigid ±/Beaufort slide of those 6×10 MB files on prefix400 | 179 997 840 offsets; 86 153 THE-sieve cands; 0 keeps |
| EXP-LP-MARSAGLIA-REMAINDER-001 | remaining 54 bits.* + germany.bit: skip-aware @0/SHA; rigid all offsets | 57 files; beam 342 / 0; 1 709 979 480 offsets; 0 keeps |
| EXP-LP-SKIPAWARE-MT19937-001 | skip-aware MT19937 from 92 marked integer seeds | plant 1.0; 184 tests, 0 keeps |
| EXP-LP-SKIPAWARE-PAYLOAD49-001 | pp49–51 256-byte grid as skip-aware pad/CTR/HMAC/AES; MD5/SHA-1/SHA-512 seeds | plant 1.0; 68 tests, 0 keeps |
| EXP-LP-SKIPAWARE-STREAMCIPHERS-001 | skip-aware RC4 / ChaCha20 / HKDF / PBKDF2-3301 on attested seeds + pp49 | plant 0.95; 72 tests, 0 keeps |
| EXP-LP-SKIPAWARE-R12C2-001 | Dukotah R12-C2 esoteric corpus as skip-aware running key at offset 0 | 11 texts fetched; 22 tests, 0 keeps; 6 hosts 503/404 |
| EXP-LP-SKIPAWARE-CAS-RUNKEYS-001 | skip-aware beam on 11 CAS books (prior rigid slides only) at 6 marked offsets | 132 tests, 0 keeps |
| EXP-LP-SKIPAWARE-R12C2-RETRY-001 | Phaedo, Seneca, Iamblichus, Plotinus ethical, Eckhart Deutsche @0 | 10 tests, 0 keeps; Dee monad has no IA text file |
| EXP-LP-SKIPAWARE-SOLVED-MT-JPG-001 | solved plains as skip-aware pads; C/Py2 MT19937 init; raw JPEG %29 | plant 1.0; 54 tests, 0 keeps |
| EXP-LP-SKIPAWARE-WIKI-DOCS-001 | skip-aware pads/SHA from 13 CAS wiki + scream314 docs (Cicada, totient, Hermetica, …) | plant 1.0; 52 tests, 0 keeps |
| EXP-LP-SKIPAWARE-AUTOMATIC-FANDOM-001 | Thue–Morse / paperfold / Fibonacci word / period-doubling / Rudin–Shapiro; fandom CORE wiki | plant 1.0; 12 auto tests, 0 keeps; fandom 403 |
| EXP-LP-SKIPAWARE-WAYBACK-LAG-001 | self-key at DJUBEI lag 6395 and 1279/15/29/56/3301/1033; Wayback fandom | 14 lag tests, 0 keeps; Wayback 503 |
| EXP-LP-SKIPAWARE-WAYBACK-FANDOM-001 | 2019-11-07 Wayback snapshots of fandom Liber Primus + how-solved | fetched; 4 tests, 0 keeps |
| EXP-LP-SKIPAWARE-LATIN-CAS-001 | CLTK Latin (Caesar/Vergil/Livy/Ovid), Quran-JSON, 2013 onion HTML pads; Latin-word gate | 29 docs; 58 tests, 0 keeps |
| EXP-LP-SKIPAWARE-REL-INVERSES-001 | skip-aware add / Beaufort inverses (prior beams were subtract-only) | add/beau plant 1.0; 40 tests, 0 keeps |
| EXP-LP-SKIPAWARE-REL-PADS-001 | add/Beaufort skip-aware on KJV/Shakespeare/wiki/Wayback/bits.01/gall1 + solved plains @0 | plant 1.0; 40 tests, 0 keeps |
| EXP-LP-COMMONCRAWL-PGP-001 | CDX on 8 CC indexes for 7A35090F / pastebin cicada URL patterns | 127 indexes listed; wildcard queries 404/502; 0 URLs; 0 new PGP |
| EXP-LP-WAYBACK-PASTE-CDX-001 | Wayback CDX pastebin/GitHub wildcards + prefix `*3301*` | wildcards 0 rows; prefix filter hits timestamp junk; cicada filter 504 |
| EXP-LP-COND-PREV-IOC-001 | cond-prev / word-pos / delta IoC on splits 15–70 | cond-prev mean 0.0354; delta 0.0353; word-pos flat; CT-autokey Latin-square family excluded |
| EXP-LP-CHAOCIPHER-29-001 | Chaocipher-29 (classic zenith/nadir) on identity/reverse + 8 keyed alphabets | plant 1.0; 52 tests, 0 keeps |
| EXP-LP-SKIPAWARE-ARITH-001 | skip-aware μ/ω/Ω/λ/σ/sopfr streams @ 0/1/3301 | plant 0.89 (low-entropy beam bias); 42 tests, 0 keeps |
| EXP-LP-SKIPAWARE-SOLITAIRE-001 | skip-aware Solitaire/Pontifex on 9 attested passphrases | plant 0.89; 18 tests, 0 keeps |
| EXP-LP-TOTIENT-VIG-MESH-001 | totient then Vigenere/Beaufort/Porta, and Vigenere then totient | 5 280 tests, 0 keeps |
| EXP-LP-LCG-MOD29-001 | affine LCG (x->a*x+c) + lagged-Fibonacci mod 29 keystreams -- the named untested short-seed generator | exhaustive rigid Vigenere 366 270 tests (23 577 distinct LCG + 841 lagfib x sub/add/beau x 5 targets), 0 keeps; plant-validated skip-aware beam 520, 0 keeps; plants 0.99 / 0.95 |
| EXP-LP-DEPTH-KAPPA-001 | ciphertext depth: coincidence / optimal-LLR scan for pad reuse (pairwise all offsets fwd+rev, self-lag 1-6000, pooled page-aligned, known-plaintext drag) | plant 1.0 (163/163 exact recovery); control on splits 0-14 fires at z 10.8 > surrogate 7.3; unsolved 15-70 max z **4.55 < surrogate 5.47**, tail counts <= surrogate, longest shared run 5; pooled n=303 540 kappa z **0.35** vs 134 sigma if depth; 47 564 known-plaintext drags, 2 keeps, both artifacts; **0 decrypts** |
| EXP-LP-SKIPAWARE-DEPTH-001 | walking-offset HMM (and discarded banded NW) on the pair difference stream — HANDOFF 5c | clean shared-pad plant 7–10σ vs shuffle (redundant with rigid depth); **reject-filtered shared pad fails plant** (2/6 seeds at n=800; fail at 1500 and 3000). Banded NW discarded: shuffle path-z ~22. No page scan. **0 decrypts**. Does not close skip-aware depth. |
| EXP-LP-WORD-DEPTH-001 | word-constrained depth on the difference stream (HANDOFF 5b): Markov-D -> exact rune-bigram forward HMM -> joint word-LM beam using the transcribed word boundaries of both pages | plants clear: synthetic English n=277 **9.8 sigma separated**, real disjoint Cicada plaintext n=242 **z 5.93**, end-to-end cascade plant found at **rank 1** among the 53 real pages; family-wise surrogate max **5.10** (12 cascades). Observed 894 452 alignments, max **z 4.07 < 5.10** -> null. Detection floor n~180-200. Keep-bar is vacuous here: shuffled ciphertext yields **38-40/40** passes. **0 decrypts** |
| EXP-LP-WORD-SKIP-001 | word-parse skip-aware beam (HANDOFF 0): trigram skip tracker + vocab bonus at transcribed ends, attested SHA-CTR seeds + totient stream | SHA plant **1.0**; dictionary-only beam failed plant (prefix then desync). 48 tests, 10 beat 8-shuffle by <1pt (sep<3). Length-1 A/I/O cribs chance (z≤0.97 / 99). **0 decrypts** |
| EXP-LP-ENIGMA-29-001 | 3-rotor Enigma-29, atbash reflector, attested rotor words | plant 1.0; 120 tests, 0 keeps |
| EXP-LP-WORD-LOCAL-TOTIENT-001 | totient/caesar/reverse restarting at each transcribed word; columnar-then-totient | plant 1.0; **2385 tests, 0 keeps**; best tri 3.31 (below bar) |
| EXP-LP-WORD-CHAIN-AK-001 | previous-word running key (first word totient/atbash/direct) | plant 1.0; **159 tests, 0 keeps**; best tri 2.44 |
| EXP-LP-SKIPAWARE-SHA3-DEE-001 | skip-aware SHA3-256 / BLAKE2s CTR + Dee *Hieroglyphic Monad* DjVuTXT pad (IA monas-hieroglyphica) | plants 0.95 / 1.0 / 0.91; **34 tests, 0 keeps**; Dee 38 642 runes fetched |
| EXP-LP-WORD-END-KEYSKIP-001 | rigid extra key consumes at transcribed word ends/starts (known `-` positions; not a beam). SHA-CTR attested seeds + totient start 0/1; extra 1/2; sub/add/Beaufort | plant 1.0 all 12 configs; wrong extra breaks. **5088 tests, 0 keeps**. Best tri 4.49 / IoC 0.036 (TH-salad, below IoC bar). **0 decrypts** |
| EXP-LP-F-KEYSKIP-001 | rigid extra key consume after observed CT-F or CT-doublet (not skip-encrypt / not page-56 4th-F) | plant 1.0; **5088 tests, 0 keeps**. Best tri 3.55 / IoC 0.036. **0 decrypts** |
| EXP-LP-XORSHIFT-PCG-001 | marked-seed xorshift32 / xoroshiro64** / PCG-XSH-RR / Galois LFSR (rigid + skip-aware beam) | plants 0.90–1.0; **1320 rigid + 176 beam, 0 keeps**. Best tri 3.56 / IoC 0.035. Not exhaustive over 2³² seeds. **0 decrypts** |
| EXP-LP-ISAAC-HIGHBIT-001 | ISAAC CSPRNG + high-bit extracts of xorshift32/PCG/Galois (XORSHIFT-PCG `%29` boundary) | plant 1.0; **1320 rigid + 110 beam, 0 keeps**. Best tri 2.94. **0 decrypts** |
| EXP-LP-SKIPAWARE-DEPTH-ALIGN-001 | HANDOFF 5c retry: banded match/gap *forward* HMM (not walking-offset, not NW max-path) | filtered same-start plants beat 12 shuffles at n=400/800/1500 (sep 2.5–4.0). Shift-37 fails. Viterbi-z overfits shuffle (discarded). Page scan 2756 dirs: one pair (057 vs rev 059) fwd 2.479 > 8-surr max 1.682 and >80 pair-local shuffles (max 0.358, z 3.92). Alignment is nearly rigid reverse (rigid κ z 1.27), already inside DEPTH-KAPPA noise. **0 decrypts** |
| EXP-LP-KISS-MWC-001 | marked-seed Marsaglia KISS99 / 16-bit MWC / 32-bit MWC / CMWC-lag3 (`%29` + hi5); rigid + skip-aware beam | plants 0.90–1.0 (wrong seed fails); **28688 tests (28512 rigid + 176 beam), 0 keeps**. Best tri 3.57 / IoC 0.036 split066 salad. Not a 2³² grind. **0 decrypts** |
| EXP-LP-SKIPAWARE-DEPTH-OFFSET-001 | prefix-crop then same-start match/gap forward (nonzero pad offset) | max-over-crops fails at page scale: n=400 shift 0/15/37/56 do not beat shuffle (look-elsewhere). n=800 shift-37 plants (sep 2.67) but LP pages are ≤277. **0 decrypts** |
| EXP-LP-RECOVER-057-059-001 | word-depth stage2/3 on ALIGN-001 flag (split057 vs rigid reverse 059) | stage2 z **0.77**, stage3 z **−1.83** vs 16 pair shuffles; neither beats shuffle max nor WORD-DEPTH family 5.10. Heads are salad (`TVNTOTHOVTHERTE…`). **0 decrypts** |
| EXP-LP-GEFFE-SHRINK-001 | marked-seed Geffe combiner + shrinking LFSR (16-bit, 5-bit→mod29) | plants 1.0 / 0.89; **528 rigid + 44 beam, 0 keeps**. Best tri 2.71. **0 decrypts** |
| EXP-LP-SECTION-KEYSKIP-001 | extra key consume at red-section openings (onion 0,3,8,15,23,27,33,40,53,54) and at every page join; SHA-CTR + totient; extra 1–3; sub/add/Beaufort | plant 1.0; **7632 tests, 0 keeps**. Best tri 4.74 / IoC 0.034 tot1 salad. **0 decrypts** |
| EXP-LP-NIHILIST-29-001 | Nihilist 5×6 Polybius + repeating numeric keys (3301 / primes / DIVINITY / totient) | plant 1.0; **540 tests, 0 keeps**. Best tri 2.43. **0 decrypts** |
| EXP-LP-GLYPH-LINECLASS-001 | rune-height line class + drop-cap; hex/stipple bands excluded (x0=0.36 occupancy) | **failed controls**: best 56→84/85 red0=4–5; 57→93–101/95 red0=6–8. Dot-grids and glued post-hex lines still leak. Headings not used as keys. **0 decrypts** |
| EXP-LP-TRIFID-PHILLIPS-001 | Trifid-27 (periods 3/5/7/15; runes 27–28 pass through) + Phillips-29 (5×6, row-shift every 5/6) on 7 attested keys | plant 1.0 (wrong period/key fails); **2268 tests, 0 keeps**. Best tri 2.92. **0 decrypts** |
| EXP-LP-SALSA20-SHAKE-001 | Salsa20/20 + SHAKE256-XOF marked seeds (`%29` + hi5); rigid + skip-aware beam (ChaCha20 / SHA3-256-CTR siblings) | eSTREAM KAT + plants 0.95–1.0 (wrong seed fails); **14344 tests (14256 rigid + 88 beam), 0 keeps**. Best tri 3.99 / IoC 0.034 split038 salad. **0 decrypts** |

| EXP-LP-BOUNDARY-DOUBLET-001 | anti-doublet rule: boundary class, lag profile, enforcement rule, fixture control | deficit is **stream-level** (within-word 0.183 z -14.59; across `-` 0.238 z -7.32; across `/` 0.228 z -3.28) -> per-word/per-line resets **excluded**; **lag-1 only** (lag 2/3 pooled z -0.12/-0.08); output-nudge `c:=c+1` **excluded at -16.7 sigma**, key-advance fits at -0.09; residual flatness marginals (p 0.032 / 0.038) **fail split-half** (corr +0.06, argmax moves) = noise; page 56 carries 2 ct doublets vs lambda 0.56 (p 0.109). **0 decrypts** |
| EXP-LP-JAVA-GLIBC-SPLITMIX-001 | Java.util.Random 48-bit LCG / glibc TYPE_0 / SplitMix64 (`%29` + hi bits); rigid + skip-aware beam | OpenJDK seed-0 KAT; plants 0.90–1.0 (wrong seed fails); **17952 tests (17820 rigid + 132 beam), 0 keeps**. Best tri 4.35 / IoC 0.036 split066 salad. Not affine-LCG-mod-29. **0 decrypts** |
| EXP-LP-RULE30-001 | Wolfram Rule 30 64-bit cyclic CA (`%29` + hi5); rigid + skip-aware beam | plants 0.93–1.0 (wrong seed fails); **7216 tests (7128 rigid + 88 beam), 0 keeps**. Best tri 4.17 / IoC 0.038 split066 salad. Not Thue–Morse/paperfold. **0 decrypts** |
| EXP-LP-VIC-ADFGVX-001 | VIC straddling-checkerboard (8 uni + 21 bi; plant on digit stream) + textbook ADFGX-25 (no-pad columnar; 5×6 ADFGVX is not invertible) | plants 1.0 (wrong key fails). **1561 tests**. Packed-rune VIC: **162 keep-bar hits, all TH-salad** (ANEND/FIRFUM; best `NTHMNTHVOETHEOTVA…` tri 8.21 IoC 0.103). ADFGX-25: **0 keeps**. No English. **0 decrypts** |
| EXP-LP-RULE30-XOSHIRO-001 | marked-seed Wolfram Rule 30 (centre-pack5 / row-mod) + xoshiro256** (`%29` + hi5); rigid + skip-aware beam | plants 0.91–1.0 (wrong seed fails). **4642 tests (4554 rigid + 88 beam), 0 keeps**. Best tri 3.25 / IoC 0.038. Not a 2²⁵⁶ grind. **0 decrypts** |
| EXP-LP-BAZERIES-GRILLE-001 | Bazeries cylinder-29 (independently mixed disks, shifts 1–14) + Fleissner 4-turn grille (n=8..16, n²≤page) | plants 1.0 (wrong key fails). **4319 tests, 0 keeps**. Best tri 3.91 / grille salad. Quagmire already closed; disks are not one mixed alphabet. **0 decrypts** |
| EXP-LP-SKIPAWARE-DEPTH-PAGESHIFT-001 | known-shift CT-crop forward at n=242/277 (no max-over-crops; HANDOFF 5c) | first-seed 15/37 wins are luck. 6-trial majority: 242/15 3/6, 242/37 3/6, 277/15 4/6, 277/37 2/6. **Does not plant.** Key-index shift ≠ CT prefix. **0 decrypts** |
| EXP-LP-FRAC-MORSE-001 | fractionated Morse (variable Latin Morse + X, keyed 27-table; ≠ Trifid) | plant 1.0; **324 tests, 0 keeps**. Best `NNTYOEEEMRXVMRAE…` tri 6.38 IoC 0.13 but **n<80** (short Morse-salad). Not English. **0 decrypts** |
| EXP-LP-HMAC-DRBG-001 | NIST HMAC-DRBG SHA-256 (K,V); `%29` + hi5; rigid + skip-aware beam | plants 1.0 (wrong seed fails); **7216 tests (7128 rigid + 88 beam), 0 keeps**. Best tri 3.82 / IoC 0.035 split047 salad. HKDF-SHA256 already closed. **0 decrypts** |
| EXP-LP-SKIPAWARE-DEPTH-KEYSKIP-001 | crop B by # of CT runes whose consumed key index < S, then same-start forward (HANDOFF 5c) | T≈S. Oracle-T majority **fails** at n=242/277 (3/6, 2/6, 4/6, 1/6). Blind T∈[S-5,S] fails at n=277. Same-start forward still needs n≥400. **0 decrypts** |
| EXP-LP-HILL-PHI-BOOK-001 | Hill on φ(entry) / entry−1 / transpose of wisdom 5×5 and C15 4×4 (all 16 invertible) | plant 1.0; **864 tests, 0 keeps**. Best split066 `FBPYXJYTHREONGMO…` tri 6.78 IoC 0.042 (below IoC bar; TH/NG salad). **0 decrypts** |
| EXP-LP-CHACHA8-12-001 | marked-seed ChaCha8 / ChaCha12 (`%29` + hi5); rigid + skip-aware beam | plants 0.90–1.0 (8≠12; wrong seed fails). **7876 tests (7788 rigid + 88 beam), 0 keeps**. Best tri 4.70 / IoC 0.033. ChaCha20 already closed. **0 decrypts** |
| EXP-LP-XORSHIFT128-WELL-001 | xorshift128+ / WELL512a (`%29` + hi5) + skip-aware omitted titles (INTUS, ANINSTRUCTION, …) | plants 1.0; **4328 tests (4224 rigid + 104 beam), 0 keeps**. Best tri 3.62 / IoC 0.037. **0 decrypts** |
| EXP-LP-SKIPAWARE-DEPTH-SECTIONS-001 | same-start forward on n=400 section heads/tails (8 sections) + 32 non-overlap book chunks | plant 6/6 at n=400. Observed max **2.23 / 2.59 < surrogate 5.04 / 3.47**. Pair-local top-8 seps are look-elsewhere. **0 decrypts** |
| EXP-LP-SKIPAWARE-NEW-WIKI-001 | skip-aware unused Wikipedia raw pads (Sefer Yetzirah, Gematria, Agrippa, Liber AL wiki, Soyga, Atbash, Dee, Magic square) + file-SHA CTR | plant 0.98/1.0; Liber_Primus wiki only 14 runes. **32 tests, 0 keeps**. Best tri 2.47 salad. **0 decrypts** |
| EXP-LP-HASH-DRBG-001 | NIST Hash_DRBG SHA-256 (`%29` + hi5); rigid + skip-aware beam | plants 0.99–1.0 (wrong seed fails). **3938 tests (3894 rigid + 44 beam), 0 keeps**. Best tri 3.73 / IoC 0.037 split047 salad. HMAC-DRBG / HKDF already closed. **0 decrypts** |
| EXP-LP-CTR-DRBG-001 | NIST CTR_DRBG AES-128/256 (`%29` + hi5); rigid + skip-aware beam | plants 0.95–1.0 (wrong seed fails). **7546 tests (7458 rigid + 88 beam), 0 keeps**. Best tri 4.27 / IoC 0.035. AES-CTR passwords already closed. **0 decrypts** |
| EXP-LP-SPECK-SIMON-001 | SPECK-64/128 + SIMON-64/128 CTR + xoroshiro128** | plants 0.88–1.0. **11154 tests (11022 rigid + 132 beam), 0 keeps**. Best tri 3.85 / IoC 0.037. **0 decrypts** |
| EXP-LP-SKIPAWARE-WIKI2-001 | skip-aware Kabbalah / Thelema / Enochian / Zohar / Crowley / Tetragrammaton / Bahir / Golden ratio pads + file-SHA CTR | plant 1.0; Liber_AL / Qabalah stubs. **40 tests, 0 keeps**. Best tri 2.42. **0 decrypts** |
| EXP-LP-PGP-2016-PATH-001 | 2016 “path lies empty” clearsigned body (VALID 7A35090F; new to this tree) as pad/SHA + 8 new phrases | plant 0.99–1.0. **1318 tests, 0 keeps**. Best tri 2.68 salad. **0 decrypts** |
| EXP-LP-SKIPAWARE-DEPTH-KEYSHIFT-001 | key-prefix *accept-count* window S/(1+1/29)±3, equalize lengths, tight-band match/gap (not CT-crop=S) | n=400 S=37 shared **2/6** (need ≥5); indep **0/6**; n=277 S=37 **4/6**. Plant fails. No page scan. Distinct from KEYSKIP oracle-T. **0 decrypts** |

Does not exclude an unpublished pad, skip-aware search at arbitrary Marsaglia or book-pad offsets, a short-seed generator not in the tested lists (affine LCG and lagged-Fibonacci mod 29 closed -- EXP-LP-LCG-MOD29-001; Marsaglia KISS/MWC/CMWC marked seeds closed -- EXP-LP-KISS-MWC-001), or a family outside the tested additive / stream-cipher / autokey set. All 60 `bits.*` files plus canada/calif/germany are now rigid-slid. In-repo books are now also skip-aware at marked offsets. Key **reuse** is now measured rather than assumed: no stretch of pad is reused anywhere in splits 15-70 that this instrument can see - page-to-page at any offset, page-to-itself at any lag <= 6 000, or page-start/page-end aligned across all 1 378 pairs (EXP-LP-DEPTH-KAPPA-001). The pooled page-aligned test is decisive (n = 303 540; 134 sigma expected under depth, 0.35 observed). The pairwise test is **not**: at the 277-rune maximum page length English-on-English depth is only a 4.1 sigma effect against a 5.5 sigma family-wise threshold, so one isolated reused-pad page pair stays inside the noise, and a planted shared pad run through the anti-repeat reject filter falls from 8.6 to 3.3 sigma. EXP-LP-WORD-DEPTH-001 closes the first of those two gaps. The anti-repeat filter that every skip-aware beam assumes is now **measured rather than assumed**: it acts on the continuous rune stream (not per word or per line), it constrains lag 1 only, and it is enforced by advancing the key rather than nudging the output (EXP-LP-BOUNDARY-DOUBLET-001). That closes two encoder variants and leaves the `encrypt_reject` model in place. The same experiment raises a live question it cannot settle: page 56, the only verified polyalphabetic solved page, does **not** show the filter (P(X>=2) = 0.109 under it), which is weak evidence that pages 0-55 use a different mechanism from the one solved page whose mechanism is known. Word boundaries are **not encrypted** -- on the solved pages the transcribed ciphertext word lengths equal the plaintext word lengths exactly -- so a depth candidate must make both streams parse into real words at once. That model lifts real-Cicada depth detection at n=242 to z 5.93 against a measured family-wise threshold of 5.10, and an end-to-end cascade plant is recovered at rank 1 from inside the real page set. The observed maximum over all 894 452 alignments is 4.07. **A single reused-pad page pair with overlap >= 200 runes is now excluded**; below about 180 runes of overlap the instrument is still blind, and it remains blind behind the anti-repeat filter.

**5% unknown gate:** 12 956 unsolved runes; 5% = **648**. Verified newly decrypted unsolved runes this run: **0**. Known-page replays do not count.

**Instrument repair this run:** `tests/negative_controls/test_wrong_key.py` was passing vacuously -- its fixture `WELCOMEPILGRIM` contains none of the ten trigrams `latin_wordish_score` tracks, so the control compared 0.0 against 0.0 and asserted nothing. Refixtured on real `lp1.wisdom` plaintext, and the multigraph inflation that manufactures TH-salad keep-bar hits is now pinned by a regression test rather than only described in prose. `scoring.py` itself is unchanged, so every prior keep-bar number stays comparable.

## Public work located but not reproduced

- Dukotah/cicada3301 (2026-07-29 self-description): OTP-class claim. Not accepted.
- NoxxGames/LiberPrimus-GPU: not executed.
- Wulfic solved-page table: conflicts with wiki 0–55-unsolved; not merged.

## Missing artifacts (priority)

- 2012 contemporaneous key capture
- clean `05.jpg` without trailer
- original onion response bytes
- image–glyph overlays for splits 15–70 (projection, drop-cap split, and NCC templates all failed p56/57 controls)
- any post-2017 signed message outside this search

## Tool honesty

GnuPG installed then used. No OutGuess/steghide. No onion probing. No paid spend.
Working tree is not a container sandbox. No background worker is running.
