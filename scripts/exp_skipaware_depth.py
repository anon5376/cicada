#!/usr/bin/env python3
"""Skip-aware pair depth: walking-offset HMM on the difference stream.

WHY THIS FAMILY IS NEW
----------------------
DEPTH-KAPPA is rigid. Its plant: shared pad + encrypt_reject on both pages
falls 8.6σ → 3.3σ. Independent rejections make the same-key map a slow
random walk in (i, j), not a free gap soup (Needleman-Wunsch max-path
z-scores ~22σ on shuffled pages — discarded).

Oracle on a synthetic n=800 filtered pair: 773 shared key indices, drift
in [-8, +2], matched LLR 7.6σ. This script scores that walk with a
forward HMM (sum over paths, not Viterbi): A[t] vs B[t+o], o in -W..W,
transitions stay / ±1. Thresholds are shuffle-surrogates of the same
statistic. Theoretical N(0,1) z is not used.

A hit is a depth *flag*, not Latin. English keep-bar does not apply to
P_a − P_b.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from cicada.liber_primus.gematria import Gematria  # noqa: E402
from cicada.paths import ROOT as CICADA_ROOT  # noqa: E402
from exp_depth_kappa import (  # noqa: E402
    H0_MEAN,
    H0_SD,
    H1_MEAN,
    LOGRATIO,
    UNI,
    best_alignment,
    idxs_of,
)
from exp_skipaware_sha_ctr import encrypt_reject  # noqa: E402

GP = Gematria()
Q = 29
OUT = CICADA_ROOT / "experiments" / "EXP-LP-SKIPAWARE-DEPTH-001"
UNSOLVED = list(range(15, 71))
MIN_N = 80
W = 8
P_STAY = 0.90
N_SURROGATE = 8
N_PLANT_SHUF = 20
RNG = np.random.default_rng(3301)

# log-sum-exp over last axis
def _lse(x: np.ndarray) -> np.ndarray:
    m = np.max(x, axis=-1, keepdims=True)
    return np.squeeze(m, axis=-1) + np.log(np.sum(np.exp(x - m), axis=-1))


def hmm_forward(a: np.ndarray, b: np.ndarray, w: int = W, p_stay: float = P_STAY) -> float:
    """Log P(observations) under walking-offset depth. Higher = more depth-like."""
    n = min(int(len(a)), int(len(b)))
    if n < MIN_N:
        return -1e12
    a = np.asarray(a[:n], np.int64)
    b = np.asarray(b[:n], np.int64)
    offs = np.arange(-w, w + 1, dtype=np.int64)
    nS = len(offs)
    log_stay = np.log(p_stay)
    log_step = np.log((1.0 - p_stay) / 2.0)
    trans = np.full((nS, nS), -1e12)
    for i in range(nS):
        trans[i, i] = log_stay
        if i:
            trans[i, i - 1] = log_step
        if i + 1 < nS:
            trans[i, i + 1] = log_step
    # emit[t, k] = LOGRATIO[(a[t] - b[t+o]) % Q], -100 if o out of range
    idx = np.arange(n)[:, None] + offs[None, :]
    valid = (idx >= 0) & (idx < n)
    safe = np.where(valid, idx, 0)
    emit = np.where(valid, LOGRATIO[(a[:, None] - b[safe]) % Q], -100.0)
    logp = np.full(nS, -np.log(nS))
    for t in range(n):
        logp = _lse(logp[:, None] + trans) + emit[t]
    return float(_lse(logp[None, :]))


def pair_score(a: np.ndarray, b: np.ndarray) -> dict:
    """HMM at page-aligned start, plus HMM on the rigid DFT-peak overlap."""
    s0 = hmm_forward(a, b)
    out = {"hmm0": round(s0, 3), "score": round(s0, 3), "where": "align0"}
    h = best_alignment(a, b)
    if h:
        d = int(h["offset"])
        lo, hi = max(0, -d), min(len(b), len(a) - d)
        if hi - lo >= MIN_N:
            sw = hmm_forward(a[lo + d:hi + d], b[lo:hi])
            out["hmm_rigid"] = round(sw, 3)
            out["rigid_offset"] = d
            out["rigid_llr_z"] = h["llr_z"]
            if sw > s0:
                out["score"] = round(sw, 3)
                out["where"] = "rigid_slice"
    return out


def scan(pg: dict[int, np.ndarray]):
    keys = sorted(pg)
    hits = []
    n = 0
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            for tag, vb in (("fwd", pg[b]), ("rev", pg[b][::-1])):
                n += 1
                h = pair_score(pg[a], vb)
                hits.append((h["score"], a, b, tag, h))
    hits.sort(key=lambda x: -x[0])
    return hits, n


def fmt(hits, k=8):
    return [{"a": f"split{a:03d}", "b": f"split{b:03d}", "dir": tag, **h}
            for _, a, b, tag, h in hits[:k]]


def synth_pair(n: int, filtered: bool, shift: int = 0):
    p1 = [int(x) for x in RNG.choice(Q, n, p=UNI)]
    p2 = [int(x) for x in RNG.choice(Q, n, p=UNI)]
    ks = [int(x) for x in RNG.integers(0, Q, (n + shift) * 8 + 8)]
    if filtered:
        ca, _ = encrypt_reject(p1, ks[shift:])
        cb, _ = encrypt_reject(p2, ks)
        return np.array(ca, np.int64), np.array(cb, np.int64)
    ca = np.array([(p1[i] + ks[shift + i]) % Q for i in range(n)], np.int64)
    cb = np.array([(p2[i] + ks[i]) % Q for i in range(n)], np.int64)
    return ca, cb


def plant_one(n: int, filtered: bool, shift: int = 0) -> dict:
    a, b = synth_pair(n, filtered, shift)
    true = pair_score(a, b)["score"]
    sh = [pair_score(RNG.permutation(a), RNG.permutation(b))["score"] for _ in range(N_PLANT_SHUF)]
    rigid = best_alignment(a, b)
    return {
        "n": n, "filtered": filtered, "shift": shift,
        "true_score": true,
        "shuffle_max": round(float(np.max(sh)), 3),
        "shuffle_mean": round(float(np.mean(sh)), 3),
        "shuffle_sd": round(float(np.std(sh)), 3),
        "beats_all_shuffles": bool(true > float(np.max(sh))),
        "sep_sigma": round((true - float(np.mean(sh))) / (float(np.std(sh)) + 1e-9), 2),
        "rigid_llr_z": None if rigid is None else rigid["llr_z"],
        "lens": [int(len(a)), int(len(b))],
    }


def run_plants() -> dict:
    rows = [
        plant_one(800, False, 0),
        plant_one(800, True, 0),
        plant_one(1500, True, 0),
        plant_one(800, True, 37),
    ]
    ok = all(r["beats_all_shuffles"] for r in rows[:3])  # shift-37 is extra
    return {"ok": ok, "rows": rows, "w": W, "p_stay": P_STAY,
            "note": "same-pair shuffle calibration; rows 0-2 must all beat 20 shuffles"}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    plant = run_plants()
    print("plant", json.dumps(plant, indent=2))
    if not plant["ok"]:
        (OUT / "result.json").write_text(json.dumps({
            "experiment": "EXP-LP-SKIPAWARE-DEPTH-001",
            "plant": plant,
            "verified_new_unsolved_runes": 0,
            "aborted": "plant failed",
        }, indent=2) + "\n")
        print("PLANT FAILED")
        return

    uns = {s: np.array(idxs_of(s), np.int64) for s in UNSOLVED}
    uns = {s: v for s, v in uns.items() if len(v) >= MIN_N}
    hits, n_pair = scan(uns)
    observed = hits[0][0] if hits else -1e12
    print(f"observed max={observed:.3f} pairs={n_pair}")

    surr = []
    for r in range(N_SURROGATE):
        sh = {s: RNG.permutation(v) for s, v in uns.items()}
        sh_hits, _ = scan(sh)
        surr.append(sh_hits[0][0] if sh_hits else -1e12)
        print(f"  surrogate {r+1}/{N_SURROGATE} max={surr[-1]:.3f}")

    exceeds = bool(observed > float(np.max(surr)))
    result = {
        "experiment": "EXP-LP-SKIPAWARE-DEPTH-001",
        "family": "skip-aware pair depth: walking-offset forward HMM on C_a-C_b",
        "keep_bar": "detection only; English keep-bar does not apply to P_a-P_b",
        "plant": plant,
        "pairwise_unsolved": {
            "pages": len(uns),
            "pair_directions": n_pair,
            "w": W,
            "observed_max_score": round(float(observed), 3),
            "surrogate_max_score": round(float(np.max(surr)), 3),
            "surrogate_mean_max": round(float(np.mean(surr)), 3),
            "exceeds_surrogate": exceeds,
            "top": fmt(hits, 8),
        },
        "power": {
            "h1_minus_h0_per_rune": round(H1_MEAN - H0_MEAN, 5),
            "rigid_expected_z_at_277": round(
                (H1_MEAN - H0_MEAN) * 277 / (H0_SD * np.sqrt(277)), 2),
            "note": "HMM is calibrated by shuffle, not this unigram z. "
                    "A single filtered page-pair at n<=277 is expected near the family-wise noise floor.",
        },
        "skeptic_review": {
            "verdict": "needs pair read — not a decrypt" if exceeds else "null",
            "why": ("HMM score beat page-shuffle max; that is a depth flag, not Latin"
                    if exceeds else
                    "max HMM score at or below shuffle-surrogate max of the same statistic"),
        },
        "unsolved_runes_total": 12956,
        "verified_new_unsolved_runes": 0,
    }
    (OUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print("wrote", OUT / "result.json", "exceeds", exceeds, "new_runes", 0)


if __name__ == "__main__":
    main()
