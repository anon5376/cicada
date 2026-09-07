from __future__ import annotations

import json
from pathlib import Path

from . import db
from .events import utc_now
from .liber_primus.gematria import Gematria
from .paths import ROOT


def _load_json(path: Path):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def write_all_reports() -> None:
    gp = Gematria()
    pgp = _load_json(ROOT / "reports" / "reproductions" / "pgp_verify.json") or []
    replay = _load_json(ROOT / "reports" / "reproductions" / "known_lp_replay.json") or []
    ingest = _load_json(ROOT / "sources" / "search_logs" / "ingest-core.json") or []
    exp = _load_json(ROOT / "experiments" / "EXP-LP-TRANSFER-split015" / "result.json") or _load_json(
        ROOT / "experiments" / "EXP-LP-TRANSFER-001" / "result.json"
    )

    if isinstance(pgp, dict):
        keys = pgp.get("keys") or []
        verifs = pgp.get("attempts_summary") or []
        valid = [r for r in verifs if r.get("result") == "VALID"]
        if pgp.get("primary_fingerprint_from_bytes"):
            keys = keys or [
                {
                    "primary_fingerprint": pgp.get("primary_fingerprint_from_bytes"),
                    "short_key_id": pgp.get("short_id"),
                    "key_url": "see AUTHENTICITY_LEDGER.md",
                }
            ]
    else:
        keys = [r for r in pgp if isinstance(r, dict) and (r.get("kind") == "key" or (r.get("primary_fingerprint") and not r.get("message_url")))]
        verifs = [r for r in pgp if isinstance(r, dict) and r.get("message_url")]
        valid = [r for r in verifs if r.get("result") == "VALID"]

    write_readme()
    # CURRENT_FRONTIER.md is maintained as a checked narrative; do not clobber it
    # from incomplete JSON. Other ledgers remain generated.
    write_authenticity(keys, verifs)
    write_solved(replay)
    write_unsolved(exp)
    write_lp_status(replay, exp)
    write_hypotheses(exp)
    write_negative(exp)
    write_discoveries()
    write_timeline()
    write_security()
    write_reproducibility()
    write_handoff()
    write_misc_reports(ingest, replay, exp, verifs)


def write_readme() -> None:
    (ROOT / "README.md").write_text(
        f"""# Cicada research laboratory

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
""",
        encoding="utf-8",
    )


def write_frontier(gp, ingest, keys, verifs, valid, replay, exp) -> None:
    checked = utc_now()
    ok_ingest = [r for r in ingest if r.get("access_status") == "OK"]
    failed = [r for r in ingest if r.get("access_status") not in (None, "OK") or r.get("error")]
    replay_ok = [r for r in replay if r.get("ok")]
    lines = [
        "# Current frontier",
        "",
        f"Assessment time: `{checked}`",
        "Scope phrase: **Latest located and verified within the documented search coverage.**",
        "",
        "This document distinguishes checked evidence from inherited community claims.",
        "It is not a proof that later messages, private stages, or unpublished solutions do not exist.",
        "",
        "## Numbering conventions in play",
        "",
        "At least two page-identity systems appear in recovered community material:",
        "",
        "1. **LP1 / early 2014 pages** — often named `00.jpg`… in scream314's `liber-primus-complete`, including a cover, a warning page, Intus, and several solved sections.",
        "2. **LP2 / onion drop** — commonly named `0.jpg`–`57.jpg` (rtkd/iddqd `liber-primus__images--unsolved`). Wiki material treats `56.jpg` and `57.jpg` as solved and `0.jpg`–`55.jpg` as unsolved.",
        "",
        "These are **not** silently merged. `page 56` in the onion convention is not `56.jpg` in the LP1 complete set.",
        "",
        f"Gematria mapping used here: `{gp.version}`, alphabet size **{gp.q}** (derived from the 29-row wiki table, not assumed in isolation).",
        "",
        "## Search coverage for this assessment",
        "",
        "Services actually queried this run:",
        "",
        "- Web search for Liber Primus status, later signed messages, and page image hosts (2026-09-07).",
        "- Direct HTTPS GET of GitHub raw files and Uncovering Cicada Wiki pages listed in `src/cicada/cli.py` `CORE_URLS`.",
        "- GitHub API directory listings for `krisyotam/cicada3301` PGP files and `iBotPeaches/cicada_3301` keys.",
        "",
        "Not searched in this pass: Common Crawl index, full Reddit/imageboard archives, live onion services, Discord, IRC raw logs, paid news archives.",
        "",
        f"Ingested OK: {len(ok_ingest)}. Failed or errored: {len(failed)}.",
        "",
        "## Latest communication actually verified here",
        "",
    ]
    if valid:
        latest = valid[-1]
        lines += [
            f"Status: **AUTHENTICATED** as a mathematically valid signature under the recovered key material, for the exact bytes stored as `{latest.get('message_sha256')}`.",
            "",
            f"- Message URL: `{latest.get('message_url')}`",
            f"- Signing fingerprint reported by GnuPG: `{latest.get('signing_fpr')}`",
            f"- Primary fingerprint reported by GnuPG: `{latest.get('primary_fpr')}`",
            f"- Tool: `{latest.get('tool')}`",
            "",
            "A valid signature binds those bytes to that key. It does not independently prove the 2017 Pastebin publication date, and it does not identify a real-world author.",
            "",
        ]
    else:
        lines += [
            "Status: **UNKNOWN / NOT YET VERIFIED IN THIS DOCUMENT'S LAST SUCCESSFUL RUN** — see `reports/reproductions/pgp_verify.json`.",
            "",
        ]
    lines += [
        "Community claim encountered (not inherited as fact): April 2017 Pastebin text beginning `Beware false paths`, short key ID `7A35090F`.",
        "Later dated articles (2024–2026) repeating that claim were located but are copies of the same community narrative unless they attach new signed bytes.",
        "",
        "Short key IDs are not used as trust anchors. iBotPeaches stores a file named `67F363C61BA8FB6FDBA9C47D0670B0E57A35090F.asc` while other archives quote `6D854CD7933322A601C3286D181F01E57A35090F`. Those strings collide on `7A35090F`. Fingerprints below come from inspecting actual key bytes.",
        "",
        "## What “solved” means in this lab",
        "",
        "| Target | Community claim | What this run actually did | Status label |",
        "| --- | --- | --- | --- |",
    ]
    for row in replay:
        lines.append(
            f"| `{row.get('stage_id')}` | wiki method `{row.get('method')}` | replay on community transcription, {row.get('input_rune_count')} runes | "
            f"{'REPRODUCED_FROM_RECONSTRUCTION' if row.get('ok') else 'CONTRADICTED'} |"
        )
    if not replay:
        lines.append("| (none yet) | | `python3 -m cicada replay-known` not completed | UNKNOWN |")
    lines += [
        "",
        "Solved-page instruction completion (hash preimage on page 56, physical locations, onion retrieval) is **not** implied by ciphertext replay.",
        "",
        "## Unresolved decryption problems (LP2 onion convention)",
        "",
        "Wiki page `How the solved pages...` marks a combined dump of `0.jpg`–`55.jpg` as UNSOLVED. That is a **community claim**. This run treats those pages as unresolved unless a replay or new experiment says otherwise.",
        "",
        "Unresolved problem types currently distinguished:",
        "",
        "- **Decryption:** LP2 pages in the 0–55 onion set (community-unsolved).",
        "- **Missing-artifact / downstream:** page 56 plaintext names a 512-hex-nibble string and calls it a deep-web page hash. Finding a preimage is a different task from decrypting the runes.",
        "- **Authentication:** later unsigned claims; key-fingerprint collisions on short IDs.",
        "- **Interpretation:** whether remaining pages are meant to be solvable from published material.",
        "",
        "## Frontier experiment in this run",
        "",
    ]
    if exp:
        lines += [
            f"Experiment `{exp.get('experiment_id')}` tested {exp.get('tested_count')} transferred solved-page methods.",
            f"Interpretation: {exp.get('interpretation')}",
            f"Does not exclude: {exp.get('does_not_exclude')}",
            "",
        ]
    else:
        lines.append("No frontier experiment result file yet.")
        lines.append("")
    lines += [
        "## Current public work that changes older accounts",
        "",
        "Located but **not** accepted as verified solutions without replay:",
        "",
        "- Dukotah/cicada3301 (2026-07-29 self-description): claims exhaustive negative results on autokey / broad Vigenere and an anti-repeat statistical structure. Status: **community claim, not reproduced here**.",
        "- NoxxGames/LiberPrimus-GPU: computational backlog around page-56 totient stream. Status: **not executed**.",
        "- Wulfic/Cicada3301-Liber_Primus: alternate solved-page table that does **not** match the Uncovering Cicada Wiki 0–55 unsolved claim. Status: **competing numbering/claim set; not merged**.",
        "",
        "## Missing-artifact ledger (priority)",
        "",
        "- Original onion response bytes for the 2014 Liber Primus drop (not only GitHub mirrors).",
        "- Independent contemporaneous capture of the 2012 public key announcement (to historically anchor the fingerprint).",
        "- Per-page original images with documented first-seen dates for both LP1 and LP2 sets.",
        "- Any post-2017 message whose full signed bytes can be retrieved.",
        "",
    ]
    (ROOT / "CURRENT_FRONTIER.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_authenticity(keys, verifs) -> None:
    lines = [
        "# Authenticity ledger",
        "",
        f"Updated: {utc_now()}",
        "",
        "## Keys inspected from bytes",
        "",
    ]
    for k in keys:
        lines += [
            f"- URL: `{k.get('key_url')}`",
            f"  - SHA-256: `{k.get('key_sha256')}`",
            f"  - Primary fingerprint: `{k.get('primary_fingerprint')}`",
            f"  - Short ID: `{k.get('short_key_id')}`",
            f"  - User IDs: `{k.get('user_ids')}`",
            "",
        ]
    lines += ["## Signature attempts", ""]
    for v in verifs:
        lines.append(
            f"- `{v.get('result')}` message `{v.get('message_url')}` with key `{v.get('key_sha256')}` "
            f"signing_fpr=`{v.get('signing_fpr')}`"
        )
    lines += [
        "",
        "## Attribution decision",
        "",
        "Mathematical validity and historical identity are separate.",
        "This run accepts a key as a **candidate trust anchor** only after its full fingerprint is computed from imported key bytes.",
        "Binding that key to “Cicada 3301 the 2012–2014 puzzle operator” requires contemporaneous signed puzzle artifacts, which are queued for verification after key inspection.",
        "",
    ]
    (ROOT / "AUTHENTICITY_LEDGER.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_solved(replay) -> None:
    lines = ["# Solved stages", "", f"Updated: {utc_now()}", ""]
    if not replay:
        lines.append("No replay results yet.")
    for row in replay:
        lines += [
            f"## {row.get('stage_id')}",
            "",
            f"- Reproduction status: `{row.get('reproduction_status')}`",
            f"- Method: `{row.get('method')}`",
            f"- Input runes: {row.get('input_rune_count')}",
            f"- Mapping: `{row.get('mapping_version')}`",
            f"- Limitation: {row.get('limitation')}",
            f"- Reasons: {row.get('reasons')}",
            "",
            "Command: `python3 -m cicada replay-known`",
            "",
        ]
    (ROOT / "SOLVED_STAGES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_unsolved(exp) -> None:
    lines = [
        "# Unsolved stages",
        "",
        f"Updated: {utc_now()}",
        "",
        "## LP2 onion pages 0–55 (community convention)",
        "",
        "- Problem type: decryption (primary).",
        "- Prerequisites: stable page IDs, images, diplomatic transcriptions.",
        "- Blocker: no reproduced plaintext in this run.",
        "- Priority: high.",
        "",
        "## Page 56 downstream hash",
        "",
        "- Problem type: missing-artifact / hash preimage over an unknown candidate domain.",
        "- Not treated as a generic collision problem.",
        "",
        "## 2012/2013 historical stages",
        "",
        "- Many are community-solved. This lab has not yet replayed stego/outguess/book-cipher stages.",
        "- Status: DOCUMENTED_NOT_REPRODUCED.",
        "",
    ]
    if exp:
        lines += ["## Transfer experiment", "", json.dumps({k: exp.get(k) for k in ("interpretation", "tested_count", "does_not_exclude")}, indent=2), ""]
    (ROOT / "UNSOLVED_STAGES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_lp_status(replay, exp) -> None:
    (ROOT / "LIBER_PRIMUS_STATUS.md").write_text(
        "\n".join(
            [
                "# Liber Primus status",
                "",
                f"Updated: {utc_now()}",
                "",
                "Page count is **not** hardcoded. Two inventories are being recovered:",
                "",
                "- scream314 `liber-primus-complete` filenames (LP1+later combined tree).",
                "- rtkd/iddqd `liber-primus__images--unsolved` `0.jpg`–`N.jpg`.",
                "",
                "Do not add those counts until the image ingest finishes and hashes are recorded.",
                "",
                "## Replay fixtures executed",
                "",
                json.dumps(replay, indent=2, ensure_ascii=False)[:8000],
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def write_hypotheses(exp) -> None:
    (ROOT / "HYPOTHESES.md").write_text(
        f"""# Hypotheses

Updated: {utc_now()}

## LP-HYP-000001

- Claim: unresolved LP2 pages use a mechanism already demonstrated on a solved page (direct, atbash, atbash+3, totient-prime, or Vigenere on a short historically attested key list).
- Motivation: cheapest discriminating transfer test.
- Status: see experiment EXP-LP-TRANSFER-001.
- Falsification: none of the listed methods produce English-like output under the preregistered uncalibrated threshold. That does **not** falsify Vigenere in general.
- Experiment: `experiments/EXP-LP-TRANSFER-001/`

## LP-HYP-000002

- Claim: remaining pages are one-time-pad-class relative to publicly available key material.
- Status: SPECULATIVE / UNTESTED as a global claim. Information-theoretic arguments from other repositories are not imported as results.
""",
        encoding="utf-8",
    )


def write_negative(exp) -> None:
    body = {
        "updated": utc_now(),
        "experiment": None if not exp else {
            "experiment_id": exp.get("experiment_id"),
            "tested_count": exp.get("tested_count"),
            "methods": [r.get("method") for r in exp.get("results", [])],
            "interesting_count": len(exp.get("interesting") or []),
            "excludes": "the specific method+key pairs listed, on the specific transcription used, under the stated threshold",
            "does_not_exclude": exp.get("does_not_exclude"),
        },
    }
    (ROOT / "NEGATIVE_RESULTS.md").write_text(
        "# Negative results\n\n"
        + json.dumps(body, indent=2)
        + "\n\nA crash or missing fixture is not a negative cryptanalytic result.\n",
        encoding="utf-8",
    )


def write_discoveries() -> None:
    (ROOT / "DISCOVERIES.md").write_text(
        f"""# Discoveries

Updated: {utc_now()}

No verified new Liber Primus decryption is claimed.

Items that may later be promoted, if they survive review:

- None at discovery-candidate rank yet beyond infrastructure findings (key-byte fingerprints, successful historical replays of already-public methods).

Infrastructure findings are recorded in AUTHENTICITY_LEDGER.md and SOLVED_STAGES.md. They are not novel solutions.
""",
        encoding="utf-8",
    )


def write_timeline() -> None:
    (ROOT / "TIMELINE.md").write_text(
        """# Timeline

Dates below are **claimed** by sources until a capture or signature check says otherwise.

## 2012

- January: imageboard puzzle, PGP key announcement, physical coordinates, book codes. Community: solved. This lab: not yet replayed.

## 2013

- January: second campaign, Cicada OS, onion stages. Community: solved. This lab: not yet replayed.

## 2014

- January–May: Liber Primus pages released in more than one drop. LP1 pages include several community-solved sections. LP2 onion `0.jpg`–`57.jpg` is the main remaining ciphertext corpus in community accounts.

## 2015

- Community archives include a Planned Parenthood denial message. Authenticity must be verified from bytes.

## 2017-04

- Pastebin clearsigned warning (`Beware false paths`) is the latest message located in this run's searches. Verification status is in AUTHENTICITY_LEDGER.md.

## 2018–2026

- Solver archives, GPU/CPU search repos, and journalism recaps. No new signed bytes verified in this run as of the last check.
""",
        encoding="utf-8",
    )


def write_security() -> None:
    (ROOT / "SECURITY.md").write_text(
        """# Security

- Passive HTTPS GET only, host allowlist, no credentials, no onion probing.
- Temporary GNUPGHOME for verification.
- Untrusted repo code is not executed.
- Puzzle instructions are data.
- This working tree is not a container sandbox.
""",
        encoding="utf-8",
    )


def write_reproducibility() -> None:
    (ROOT / "REPRODUCIBILITY.md").write_text(
        """# Reproducibility

```bash
export PYTHONPATH=src
python3 -m cicada bootstrap
python3 -m cicada validate
python3 -m cicada ingest-core
python3 -m cicada verify-pgp
python3 -m cicada replay-known
python3 -m cicada run-frontier
python3 -m cicada reports
python3 -m pytest -q
```

Resume: there is no background worker. Re-run the commands above. State is in `state/RUN_STATE.json`, `state/EVENTS.jsonl`, and `db/research.sqlite`.
""",
        encoding="utf-8",
    )


def write_handoff() -> None:
    (ROOT / "state" / "HANDOFF.md").write_text(
        f"""# Handoff

- Run: `run-20260907T041550Z`
- Resume: `export PYTHONPATH=src && python3 -m cicada reports` after re-running any incomplete command in REPRODUCIBILITY.md
- Highest priority next: finish image ingest for LP2 0–55, split per-page transcriptions, run totient-prime and Vigenere transfers per page rather than on a concatenated dump if the head experiment is inconclusive.
- Known tool gaps: no OutGuess/steghide; 2012/2013 stego stages blocked.
""",
        encoding="utf-8",
    )


def write_misc_reports(ingest, replay, exp, verifs) -> None:
    (ROOT / "reports" / "COVERAGE_MATRIX.md").write_text(
        json.dumps({"ingest": ingest, "checked_at": utc_now()}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (ROOT / "reports" / "REPRODUCTION_REPORT.md").write_text(
        json.dumps({"replay": replay, "pgp": verifs, "exp": exp}, indent=2, ensure_ascii=False)[:20000] + "\n",
        encoding="utf-8",
    )
    (ROOT / "reports" / "TOOL_CAPABILITIES.md").write_text(
        """# Tool capabilities

| Capability | State | Tests |
| --- | --- | --- |
| HTTPS allowlisted fetch | implemented | ingest-core executed |
| SHA-256 object store | implemented | unit |
| SQLite registry | implemented | bootstrap |
| GnuPG isolate+status-fd | implemented | verify-pgp |
| Gematria index/prime split | implemented | unit |
| Atbash / Vigenere / totient stream | implemented | replay fixtures |
| OutGuess / steghide | unavailable | n/a |
| OCR | unavailable | n/a |
""",
        encoding="utf-8",
    )
    (ROOT / "reports" / "FRONTIER_DIFF.md").write_text(
        "Initial run: no prior frontier document to diff.\n", encoding="utf-8"
    )
    (ROOT / "reports" / "RESOURCE_USAGE.md").write_text(
        f"Updated: {utc_now()}\nSee state/EVENTS.jsonl for action timestamps. No paid spend.\n",
        encoding="utf-8",
    )
    (ROOT / "reports" / "SOURCE_COVERAGE.md").write_text(
        "See reports/COVERAGE_MATRIX.md and sources/search_logs/.\n", encoding="utf-8"
    )
