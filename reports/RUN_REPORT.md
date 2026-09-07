# Run report — 2026-09-07T04:27Z

## 1. What was actually built and run

A local Python 3.9 research lab at `/Users/anon5376/Projects/cicada`:

- content-addressed blob store, SQLite registry, allowlisted HTTPS fetcher
- isolated GnuPG 2.5.22 verification (`--status-fd`)
- Gematria Primus mapping (29 runes; index ≠ prime)
- atbash / Vigenere / totient-prime transforms with tests
- replay fixtures extracted from a captured wiki how-solved page
- experiment runner with frozen spec/result JSON
- report generator

Commands actually executed: `bootstrap`, `validate`, `ingest-core`, follow-up ingest of 17 more PGP messages and LP2 images 1–55, `verify-pgp`, fixture replays, three transfer experiments, one Caesar/totient-offset experiment, image EOI triage, report generation.

## 2. Current frontier as of the recorded check time

See `CURRENT_FRONTIER.md`. Latest VALID signed body in coverage: 2017-04 warning under fingerprint `6D854CD7933322A601C3286D181F01E57A35090F`. Liber Primus onion pages corresponding to rtkd splits 15+ remain unresolved decryption problems.

## 3. Historical stages independently reproduced

- LP1 warning: atbash — REPRODUCED_FROM_RECONSTRUCTION
- LP1 wisdom: direct — REPRODUCED_FROM_RECONSTRUCTION
- LP2 57 parable: direct — REPRODUCED_FROM_RECONSTRUCTION
- LP2 56 “An end”: totient-prime — PARTIALLY_REPRODUCED (paragraph 1 only)

2012/2013 stego/book-code stages: not replayed (tools missing).

## 4. New findings (discovery status)

- **REPRODUCED / AUTHENTICATED:** full fingerprint of the candidate signing key from imported bytes; 20 krisyotam messages VALID as stored; 2017 body verified.
- **DISCOVERY CANDIDATE:** krisyotam `2013-01-opening-book-code.asc` is damaged (missing Hash-header blank line); VALID after that documented repair.
- **DISCOVERY CANDIDATE:** scream314 `05.jpg` has 72 700 trailing post-EOI bytes, high entropy, no valid gzip. Treat as contaminated community file, not an original payload.
- **No verified new Liber Primus decryption.**

## 5. Important rejected hypotheses and exact bounds

- `LP-HYP-000001` on splits 15–17: 12 transferred solved-page methods each, 0 hits.
- `EXP-LP-CAESAR-TOTIENT-OFFSET-001` on split 15: 88 candidates (Caesar, atbash+Caesar, totient offsets 0–29), 0 hits.
- Does not exclude other keys, other families, or other page segmentations.

## 6. Unresolved gaps and deferred branches

- Page 56 paragraph 2 mismatch; hash-preimage instruction.
- Alias map across numbering systems.
- Clean vs contaminated image variants.
- 2012 OutGuess replay (tool unavailable).
- Dukotah/Wulfic competing claims.

## 7. Resource use and why execution stopped

- Host: Darwin arm64, 15 CPUs, ~24 GiB RAM, plenty of disk.
- Network used for GitHub raw/API only. No paid spend.
- Stopping condition: first full vertical slice + frontier experiments + dated frontier document are in place; remaining high-value work is continued per `state/HANDOFF.md` within the same session if time remains, otherwise this is the checkpoint. No background process is running.

## 8. Reproduction commands

```bash
cd /Users/anon5376/Projects/cicada
export PYTHONPATH=src
python3 -m cicada validate
python3 -m cicada replay-known
python3 -m cicada reports
```

## 9. Checkpoint / resume

See `state/HANDOFF.md`. Queue files are records, not running workers.
