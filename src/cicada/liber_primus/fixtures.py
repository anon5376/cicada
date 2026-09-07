from __future__ import annotations

import json
from pathlib import Path

from .ciphers import apply_named
from .gematria import Gematria

GP = Gematria()
DEFAULT_PATH = Path(__file__).resolve().parents[3] / "tests" / "liber_primus" / "replay_fixtures.json"


def _norm_plain(s: str) -> str:
    return "".join(ch for ch in s.upper() if ch.isalpha())


def load_fixtures(path: Path | None = None) -> list[dict]:
    p = path or DEFAULT_PATH
    if not p.exists():
        return []
    return json.loads(p.read_text(encoding="utf-8"))


def replay_fixture(fix: dict) -> dict:
    idxs = GP.rune_indices(fix["ciphertext"])
    key = GP.encode_latin_key(fix["key"]) if fix.get("key") else None
    out_idx = apply_named(fix["method"], idxs, key)
    latin = GP.latin_stream(out_idx)
    got = _norm_plain(latin)
    expected = _norm_plain(fix.get("expected_latin_normalized", ""))
    contains = [_norm_plain(x) for x in fix.get("expected_contains", [])]
    ok = True
    reasons = []
    if contains:
        for frag in contains:
            if frag not in got:
                ok = False
                reasons.append(f"missing fragment {frag}")
    elif expected:
        if got != expected:
            if expected and len(got) == len(expected):
                agree = sum(a == b for a, b in zip(got, expected)) / len(got)
                if agree < 0.95:
                    ok = False
                    reasons.append(f"normalized latin mismatch agree={agree:.3f}")
                else:
                    reasons.append(f"near-match agree={agree:.3f}")
            else:
                ok = False
                reasons.append("normalized latin mismatch")
    return {
        "stage_id": fix["stage_id"],
        "ok": ok,
        "reasons": reasons,
        "method": fix["method"],
        "input_rune_count": len(idxs),
        "got_normalized": got,
        "expected_normalized": expected or None,
        "mapping_version": GP.version,
        "reproduction_status": "REPRODUCED_FROM_RECONSTRUCTION" if ok else "CONTRADICTED",
        "limitation": "ciphertext is a community transcription, not independently re-derived from page image bytes in this replay",
    }


def replay_all(path: Path | None = None) -> list[dict]:
    return [replay_fixture(fix) for fix in load_fixtures(path)]
