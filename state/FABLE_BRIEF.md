# Fable 5.1 brief (Agent Bus / Claude Code subscription)

Workdir: `/Users/anon5376/Projects/cicada`
Date: 2026-09-07

## Goal

Decrypt ≥5% of still-unresolved Liber Primus ciphertext. rtkd splits 15–70 / onion 0–55 = 12,956 runes. 5% = **648**. Known-page replays do not count. Current verified new decrypt: **0**.

## Hard rules

- Inspect the tree as authority: `CURRENT_FRONTIER.md`, `NEGATIVE_RESULTS.md`, `state/HANDOFF.md`, `experiments/EXP-LP-*/result.json`.
- Passive public HTTPS only. Allowlist in `src/cicada/acquisition.py`. No onion probing, no contacting people, no exploits, no OutGuess.
- Do not invent English. Do not promote split066 TH-salad. Shared heads like `PMCEAO` / `NGCPTN` are beam bias.
- Plant-and-recover before trusting a null. Reuse `scripts/exp_skipaware_sha_ctr.py` and `scripts/exp_skipaware_rel_inverses.py`.
- Keep bar: n≥80, trigram_per_100≥3.5, IoC≥0.045, vowelish 0.28–0.55, then human-readable English.
- `export PYTHONPATH=src`. Do **not** run `python3 -m cicada reports` (clobbers CURRENT_FRONTIER).
- Do not mark the 5% goal complete.

## Already tested — do not rerun

See CURRENT_FRONTIER experiment table. In particular: skip-aware SHA-CTR / totient / Vigenere / PGP / Marsaglia file-aligned / MT19937 / pp49 / stream ciphers / R12-C2 / CAS books / solved plains / JPEG %29 / wiki / automatic sequences / Latin / Wayback fandom / add+Beaufort inverses and pads / CC+Wayback URL-index (0 new 7A35090F); word-local totient, word-chain autokey, word-parse skip beam, and rigid extra key-skip at word ends/starts (`EXP-LP-WORD-END-KEYSKIP-001`, 5088 tests, 0 keeps). GitHub 2026-09-07 “solves” are not executable 648-rune decrypts.

Fresh measurement 2026-09-07: cond-prev IoC mean 0.0354 (chance). Word-position IoC flat. Delta IoC 0.0353. Previous-CT-selects-alphabet family is dead.

## Your job

1. Find ONE unused executable family (new KDF, relation, allowlisted artifact, or control-valid image method). Not a KJV reslide. Not skip-aware at every Marsaglia offset.
2. Script under `scripts/exp_*.py`, plant-and-recover, run prefix400 + split015.
3. Write `experiments/EXP-LP-.../result.json`.
4. Append one CURRENT_FRONTIER row and a NEGATIVE_RESULTS bullet (or a decrypt record only if ≥80 readable runes survive skeptic review).

Reply on Agent Bus to **operator** with: method run, plant agree, tested/keeps, verified new unsolved runes (integer), next unused angle or evidence boundary, file paths.
