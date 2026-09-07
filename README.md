# Cicada research laboratory

Local-first system for recovering, hashing, verifying, and experimenting on
publicly recoverable Cicada 3301 / Liber Primus material.

This repository is an **execution lab**, not a claim that Liber Primus is solved.

## What actually works now

Verified commands (run from the repository root, `PYTHONPATH=src`):

```bash
python3 -m cicada bootstrap
python3 -m cicada validate
python3 -m cicada ingest-core
python3 -m cicada verify-pgp
python3 -m cicada replay-known
python3 -m cicada run-frontier
python3 -m cicada reports
python3 -m pytest -q
```

## Layout

- `corpus/objects/sha256/` — content-addressed raw bytes
- `db/research.sqlite` — structured records
- `src/cicada/` — acquisition, PGP, Gematria, experiments, reports
- `tests/liber_primus/` — replay fixtures
- `experiments/` — frozen specs and attempt results
- `CURRENT_FRONTIER.md` — dated public-state assessment

## Limits

- No container sandbox. Isolation is allowlisted HTTPS plus temporary `GNUPGHOME`.
- Community transcriptions are not treated as original page bytes.
- A passing replay test is implementation fidelity, not a new decryption.
