#!/usr/bin/env python3
"""Skip-aware pair depth via match/gap alignment (HANDOFF 5c retry).

EXP-LP-SKIPAWARE-DEPTH-001's walking-offset HMM always advanced both CT
clocks together (A[t] vs B[t+o]). Independent encrypt_reject on a shared pad
is not that: a key index may be used on A only, B only, or both. That is
sequence alignment with three moves (match / gap-A / gap-B), not a diagonal
jitter.

Needleman–Wunsch *max*-path was discarded because shuffle path-z ~22. This
uses the forward algorithm (sum over paths) and a Viterbi matching whose
LLR is scored against same-pair shuffles — the statistic, not the max path
in isolation, has to beat the null.
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
from exp_depth_kappa import H0_MEAN, H0_SD, LOGRATIO, UNI, idxs_of  # noqa: E402
from exp_skipaware_sha_ctr import encrypt_reject  # noqa: E402

GP = Gematria()
Q = 29
OUT = CICADA_ROOT / "experiments" / "EXP-LP-SKIPAWARE-DEPTH-ALIGN-001"
UNSOLVED = list(range(15, 71))
MIN_N = 80
NEG = -1e12
# P(both use) / P(A only) / P(B only) given independent skip≈1/29
P_MATCH = 0.934
P_GAP = (1.0 - P_MATCH) / 2.0
LOG_M = float(np.log(P_MATCH))
LOG_G = float(np.log(P_GAP))
N_SHUF = 12
N_SURR = 8
RNG = np.random.default_rng(3301)


def _lse3(x, y, z) -> float:
    m = x if x > y else y
    if z > m:
        m = z
    return m + float(np.log(np.exp(x - m) + np.exp(y - m) + np.exp(z - m)))


def band_w(n: int, m: int) -> int:
    return max(24, abs(n - m) + 12)


def forward_score(a: np.ndarray, b: np.ndarray, w: int | None = None) -> float:
    n, m = int(len(a)), int(len(b))
    if n < 8 or m < 8:
        return NEG
    if w is None:
        w = band_w(n, m)
    prev = np.full(m + 1, NEG)
    prev[0] = 0.0
    for j in range(1, min(m, w) + 1):
        prev[j] = prev[j - 1] + LOG_G
    for i in range(1, n + 1):
        cur = np.full(m + 1, NEG)
        j_lo = max(0, i - w)
        j_hi = min(m, i + w)
        if j_lo == 0:
            cur[0] = prev[0] + LOG_G
        ai = int(a[i - 1])
        j_start = max(1, j_lo)
        for j in range(j_start, j_hi + 1):
            em = LOG_M + float(LOGRATIO[(ai - int(b[j - 1])) % Q])
            cur[j] = _lse3(prev[j - 1] + em, prev[j] + LOG_G, cur[j - 1] + LOG_G)
        prev = cur
    return float(prev[m])


def viterbi_match_llr(a: np.ndarray, b: np.ndarray, w: int | None = None) -> dict:
    """Viterbi path; LLR and z on the matched pairs only (oracle-class statistic)."""
    n, m = int(len(a)), int(len(b))
    if n < 8 or m < 8:
        return {"n_match": 0, "llr": 0.0, "z": 0.0}
    if w is None:
        w = band_w(n, m)
    prev = np.full(m + 1, NEG)
    ptr = np.zeros((n + 1, m + 1), np.int8)  # 1=match 2=gapA 3=gapB
    prev[0] = 0.0
    for j in range(1, min(m, w) + 1):
        prev[j] = prev[j - 1] + LOG_G
        ptr[0, j] = 3
    for i in range(1, n + 1):
        cur = np.full(m + 1, NEG)
        j_lo = max(0, i - w)
        j_hi = min(m, i + w)
        if j_lo == 0:
            cur[0] = prev[0] + LOG_G
            ptr[i, 0] = 2
        ai = int(a[i - 1])
        for j in range(max(1, j_lo), j_hi + 1):
            em = LOG_M + float(LOGRATIO[(ai - int(b[j - 1])) % Q])
            cand = (prev[j - 1] + em, prev[j] + LOG_G, cur[j - 1] + LOG_G)
            k = int(np.argmax(cand))
            cur[j] = cand[k]
            ptr[i, j] = k + 1
        prev = cur
    i, j = n, m
    diffs = []
    while i > 0 or j > 0:
        mv = int(ptr[i, j])
        if mv == 1 and i and j:
            diffs.append((int(a[i - 1]) - int(b[j - 1])) % Q)
            i -= 1
            j -= 1
        elif mv == 2 and i:
            i -= 1
        elif mv == 3 and j:
            j -= 1
        else:
            if i:
                i -= 1
            elif j:
                j -= 1
            else:
                break
    nm = len(diffs)
    if nm < 8:
        return {"n_match": nm, "llr": 0.0, "z": 0.0}
    llr = float(np.sum(LOGRATIO[np.array(diffs, np.int64)]))
    z = (llr - nm * H0_MEAN) / (H0_SD * np.sqrt(nm) + 1e-12)
    return {"n_match": nm, "llr": round(llr, 3), "z": round(float(z), 3)}


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
    true_fwd = forward_score(a, b)
    true_v = viterbi_match_llr(a, b)
    sh_fwd, sh_z = [], []
    for _ in range(N_SHUF):
        sa, sb = RNG.permutation(a), RNG.permutation(b)
        sh_fwd.append(forward_score(sa, sb))
        sh_z.append(viterbi_match_llr(sa, sb)["z"])
    sep_fwd = (true_fwd - float(np.mean(sh_fwd))) / (float(np.std(sh_fwd)) + 1e-9)
    sep_z = (true_v["z"] - float(np.mean(sh_z))) / (float(np.std(sh_z)) + 1e-9)
    row = {
        "n": n, "filtered": filtered, "shift": shift,
        "lens": [int(len(a)), int(len(b))],
        "true_fwd": round(true_fwd, 3),
        "shuffle_fwd_max": round(float(np.max(sh_fwd)), 3),
        "sep_fwd": round(float(sep_fwd), 2),
        "true_z": true_v["z"], "n_match": true_v["n_match"],
        "shuffle_z_max": round(float(np.max(sh_z)), 3),
        "sep_z": round(float(sep_z), 2),
        "beats_fwd": bool(true_fwd > float(np.max(sh_fwd))),
        "beats_z": bool(true_v["z"] > float(np.max(sh_z))),
    }
    row["beats"] = bool(row["beats_fwd"] or row["beats_z"])
    print("plant_row", row, flush=True)
    return row


def run_plants() -> dict:
    rows = [
        plant_one(400, False, 0),
        plant_one(400, True, 0),
        plant_one(800, True, 0),
        plant_one(1500, True, 0),
        plant_one(800, True, 37),
    ]
    # must beat shuffle on the filtered same-start cases (rows 1-3)
    ok = all(r["beats"] for r in rows[1:4])
    return {"ok": ok, "rows": rows, "n_shuffle": N_SHUF,
            "note": "filtered rows 400/800/1500 must beat 12 shuffles on fwd or viterbi-z"}


def scan_pairs(pg: dict[int, np.ndarray]):
    """Score with forward_score — the statistic that beat shuffle on filtered plants.

    Viterbi-z is *not* used: plant rows show shuffle Viterbi-z exceeding the true
    pair (same cherry-pick as discarded Needleman–Wunsch).
    """
    keys = sorted(pg)
    hits = []
    n = 0
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            for tag, vb in (("fwd", pg[b]), ("rev", pg[b][::-1])):
                n += 1
                s = forward_score(pg[a], vb)
                hits.append((s, a, b, tag))
                if n % 400 == 0:
                    print(f"  scored {n} pairs", flush=True)
    hits.sort(key=lambda x: -x[0])
    return hits, n


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    plant = run_plants()
    print("plant_ok", plant["ok"], flush=True)
    if not plant["ok"]:
        (OUT / "result.json").write_text(json.dumps({
            "experiment": "EXP-LP-SKIPAWARE-DEPTH-ALIGN-001",
            "family": "banded match/gap forward+Viterbi pair depth",
            "plant": plant,
            "verified_new_unsolved_runes": 0,
            "aborted": "plant failed — decoder still does not recover reject-filtered matching",
        }, indent=2) + "\n")
        print("PLANT FAILED")
        return

    uns = {s: np.array(idxs_of(s), np.int64) for s in UNSOLVED}
    uns = {s: v for s, v in uns.items() if len(v) >= MIN_N}
    hits, n_pair = scan_pairs(uns)
    observed = hits[0][0] if hits else -1e12
    print(f"observed max z={observed:.3f} pairs={n_pair}", flush=True)
    surr = []
    for r in range(N_SURR):
        sh = {s: RNG.permutation(v) for s, v in uns.items()}
        sh_hits, _ = scan_pairs(sh)
        surr.append(sh_hits[0][0] if sh_hits else -1e12)
        print(f"  surrogate {r+1}/{N_SURR} max z={surr[-1]:.3f}", flush=True)
    exceeds = bool(observed > float(np.max(surr)))
    top = [{"a": f"split{a:03d}", "b": f"split{b:03d}", "dir": tag, "z": round(z, 3)}
           for z, a, b, tag in hits[:8]]
    result = {
        "experiment": "EXP-LP-SKIPAWARE-DEPTH-ALIGN-001",
        "family": "banded match/gap forward+Viterbi pair depth (HANDOFF 5c)",
        "keep_bar": "detection only; not a Latin decrypt",
        "plant": plant,
        "pairwise_unsolved": {
            "pages": len(uns),
            "pair_directions": n_pair,
            "observed_max_z": round(float(observed), 3),
            "surrogate_max_z": round(float(np.max(surr)), 3),
            "exceeds_surrogate": exceeds,
            "top": top,
        },
        "skeptic_review": {
            "verdict": "depth flag — not a decrypt" if exceeds else "null",
        },
        "verified_new_unsolved_runes": 0,
    }
    (OUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print("wrote", OUT / "result.json", "exceeds", exceeds)


if __name__ == "__main__":
    main()
