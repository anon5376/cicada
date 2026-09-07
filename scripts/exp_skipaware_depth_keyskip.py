#!/usr/bin/env python3
"""Skip-aware depth that crops by *key* consumption, not a CT prefix of length S.

HANDOFF 5c: A starts at key index S, B at 0, both through encrypt_reject.
B's unmatched prefix length T is the number of B-CT symbols whose consumed
key index is < S — T ≤ S, usually T ∈ [S-5, S]. After dropping those T
runes the streams are same-start on the shared suffix.

Oracle-T must plant at page length if same-start does. The blind decoder
tries T in {S-5..S} for motivated S, each crop vs its own shuffles
(no max-over-crops in the plant gate).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from cicada.paths import ROOT as CICADA_ROOT  # noqa: E402
from exp_depth_kappa import UNI, idxs_of  # noqa: E402
from exp_skipaware_depth_align import N_SHUF, RNG, forward_score  # noqa: E402
from exp_skipaware_sha_ctr import encrypt_reject  # noqa: E402

OUT = CICADA_ROOT / "experiments" / "EXP-LP-SKIPAWARE-DEPTH-KEYSKIP-001"
Q = 29
SHIFTS = (15, 37)
MIN_N = 80
N_PLANT = 6
UNSOLVED = list(range(15, 71))


def synth_shifted(n: int, shift: int):
    p1 = [int(x) for x in RNG.choice(Q, n, p=UNI)]
    p2 = [int(x) for x in RNG.choice(Q, n, p=UNI)]
    ks = [int(x) for x in RNG.integers(0, Q, (n + shift) * 8 + 8)]
    ca, _ = encrypt_reject(p1, ks[shift:])
    cb, used_b = encrypt_reject(p2, ks)
    T = int(sum(1 for u in used_b if u < shift))
    return np.array(ca, np.int64), np.array(cb, np.int64), T


def suffix_score(a: np.ndarray, b: np.ndarray, T: int) -> float:
    if T < 0 or len(b) - T < MIN_N or len(a) < MIN_N:
        return -1e12
    L = min(len(a), len(b) - T)
    return forward_score(a[:L], b[T:T + L])


def plant_oracle(n: int, shift: int) -> dict:
    a, b, T = synth_shifted(n, shift)
    true = suffix_score(a, b, T)
    sh = [suffix_score(RNG.permutation(a), RNG.permutation(b), T) for _ in range(N_SHUF)]
    sep = (true - float(np.mean(sh))) / (float(np.std(sh)) + 1e-9)
    row = {
        "kind": "oracle_T", "n": n, "shift": shift, "T": T,
        "lens": [int(len(a)), int(len(b))],
        "true": round(float(true), 3),
        "shuffle_max": round(float(np.max(sh)), 3),
        "sep": round(float(sep), 2),
        "beats": bool(true > float(np.max(sh))),
    }
    print("plant", row, flush=True)
    return row


def plant_blind_window(n: int, shift: int) -> dict:
    """Each T in [S-5,S] vs its own shuffles. Success = oracle T is in the
    window and *that* crop beats (not the max over T)."""
    a, b, T = synth_shifted(n, shift)
    lo, hi = max(0, shift - 5), shift
    in_window = lo <= T <= hi
    true = suffix_score(a, b, T) if in_window else -1e12
    sh = [suffix_score(RNG.permutation(a), RNG.permutation(b), T) for _ in range(N_SHUF)]
    sep = (true - float(np.mean(sh))) / (float(np.std(sh)) + 1e-9)
    row = {
        "kind": "blind_window", "n": n, "shift": shift, "T": T,
        "window": [lo, hi], "T_in_window": in_window,
        "true": round(float(true), 3),
        "shuffle_max": round(float(np.max(sh)), 3),
        "sep": round(float(sep), 2),
        "beats": bool(in_window and true > float(np.max(sh))),
    }
    print("plant", row, flush=True)
    return row


def scan(pg: dict[int, np.ndarray]):
    keys = sorted(pg)
    hits, n = [], 0
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            va, vb = pg[a], pg[b]
            for S in SHIFTS:
                for T in range(max(0, S - 5), S + 1):
                    for which, x, y in (("B", va, vb), ("A", vb, va)):
                        n += 1
                        s = suffix_score(x, y, T)
                        hits.append((s, a, b, which, S, T))
    hits.sort(key=lambda r: -r[0])
    return hits, n


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    oracle, blind = [], []
    for n in (242, 277):
        for S in SHIFTS:
            for _ in range(N_PLANT):
                oracle.append(plant_oracle(n, S))
            for _ in range(N_PLANT):
                blind.append(plant_blind_window(n, S))

    def maj(rows, n, S):
        v = [r["beats"] for r in rows if r["n"] == n and r["shift"] == S]
        return {"wins": sum(v), "n": len(v), "ok": sum(v) >= 4}

    o_maj = {f"n{n}_s{S}": maj(oracle, n, S) for n in (242, 277) for S in SHIFTS}
    b_maj = {f"n{n}_s{S}": maj(blind, n, S) for n in (242, 277) for S in SHIFTS}
    plant = {
        "oracle_ok": all(v["ok"] for v in o_maj.values()),
        "blind_ok": all(v["ok"] for v in b_maj.values()),
        "oracle_majority": o_maj,
        "blind_majority": b_maj,
        "oracle_rows": oracle,
        "blind_rows": blind,
    }
    print("oracle_ok", plant["oracle_ok"], o_maj, flush=True)
    print("blind_ok", plant["blind_ok"], b_maj, flush=True)

    if not plant["oracle_ok"]:
        (OUT / "result.json").write_text(json.dumps({
            "experiment": "EXP-LP-SKIPAWARE-DEPTH-KEYSKIP-001",
            "family": "key-consumption suffix crop + same-start forward (HANDOFF 5c)",
            "plant": {k: plant[k] for k in ("oracle_ok", "blind_ok", "oracle_majority", "blind_majority")},
            "verified_new_unsolved_runes": 0,
            "aborted": "oracle-T same-start suffix does not majority-plant at page length",
        }, indent=2) + "\n")
        print("ORACLE PLANT FAILED — no page scan")
        return

    if not plant["blind_ok"]:
        (OUT / "result.json").write_text(json.dumps({
            "experiment": "EXP-LP-SKIPAWARE-DEPTH-KEYSKIP-001",
            "family": "key-consumption suffix crop + same-start forward (HANDOFF 5c)",
            "plant": {k: plant[k] for k in ("oracle_ok", "blind_ok", "oracle_majority", "blind_majority")},
            "verified_new_unsolved_runes": 0,
            "aborted": "oracle-T plants but T∈[S-5,S] blind window does not majority-plant",
            "note": "Key-step model is right; T is not recoverable from S alone at page length.",
        }, indent=2) + "\n")
        print("BLIND PLANT FAILED — no page scan")
        return

    uns = {s: np.array(idxs_of(s), np.int64) for s in UNSOLVED}
    uns = {s: v for s, v in uns.items() if len(v) >= MIN_N}
    hits, n_scored = scan(uns)
    print(f"observed max={hits[0][0]:.3f} scores={n_scored}", flush=True)
    top_local = []
    for z, a, b, which, S, T in hits[:8]:
        va, vb = uns[a], uns[b]
        x, y = (va, vb) if which == "B" else (vb, va)
        shufs = [suffix_score(RNG.permutation(x), RNG.permutation(y), T) for _ in range(N_SHUF)]
        sep = (z - float(np.mean(shufs))) / (float(np.std(shufs)) + 1e-9)
        row = {
            "a": f"split{a:03d}", "b": f"split{b:03d}", "late": which,
            "S": S, "T": T, "score": round(float(z), 3),
            "shuffle_max": round(float(np.max(shufs)), 3),
            "sep": round(float(sep), 2),
            "beats": bool(z > float(np.max(shufs))),
        }
        top_local.append(row)
        print("top", row, flush=True)
    flag = any(t["beats"] and t["sep"] >= 3.0 for t in top_local)
    result = {
        "experiment": "EXP-LP-SKIPAWARE-DEPTH-KEYSKIP-001",
        "family": "key-consumption suffix crop + same-start forward (HANDOFF 5c)",
        "keep_bar": "detection only; not a Latin decrypt",
        "plant": {k: plant[k] for k in ("oracle_ok", "blind_ok", "oracle_majority", "blind_majority")},
        "pairwise_unsolved": {
            "pages": len(uns), "scores": n_scored,
            "observed_max": round(float(hits[0][0]), 3),
            "top_local": top_local, "flag": flag,
        },
        "skeptic_review": {"verdict": "depth flag — not a decrypt" if flag else "null"},
        "verified_new_unsolved_runes": 0,
    }
    (OUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print("wrote", OUT / "result.json", "flag", flag)


if __name__ == "__main__":
    main()
