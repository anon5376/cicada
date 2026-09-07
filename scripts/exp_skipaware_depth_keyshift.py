#!/usr/bin/env python3
"""Skip-aware depth that models skipped KEY steps, not CT crops.

HANDOFF 5c remainder. PAGESHIFT cropped exactly S ciphertext runes
(key-index shift ≠ CT prefix). This searches the accept-count nB in a
±3 window around S/(1+1/29), equalizes lengths, then tight-band match/gap.

Plant must beat shuffle on reject-filtered shift-37 at prefix400 scale
(n=400) and fail on independent pads. Page-length n=277 is recorded.
Abort the unsolved scan if plant fails. Detection is not Latin; keep-bar
does not count toward 300.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from cicada.liber_primus.skipaware_depth import (  # noqa: E402
    accept_window,
    score_keyshift,
)
from cicada.paths import ROOT as CICADA_ROOT  # noqa: E402
from exp_depth_kappa import LOGRATIO, UNI, Q, idxs_of  # noqa: E402
from exp_skipaware_sha_ctr import encrypt_reject, prefix  # noqa: E402

OUT = CICADA_ROOT / "experiments" / "EXP-LP-SKIPAWARE-DEPTH-KEYSHIFT-001"
EXPERIMENT = "EXP-LP-SKIPAWARE-DEPTH-KEYSHIFT-001"
N_SHUF = 8
N_TRIAL = 6
MARKED_S = (0, 15, 37, 56)
MIN_N = 80


def synth_pair(n: int, shift: int, seed: int, shared: bool = True):
    rng = np.random.default_rng(seed)
    p1 = [int(x) for x in rng.choice(Q, n, p=UNI)]
    p2 = [int(x) for x in rng.choice(Q, n, p=UNI)]
    ks = [int(x) for x in rng.integers(0, Q, (n + shift) * 8 + 16)]
    if not shared:
        ks2 = [int(x) for x in rng.integers(0, Q, (n + shift) * 8 + 16)]
        ca, _ = encrypt_reject(p1, ks[shift:] if shift else ks)
        cb, _ = encrypt_reject(p2, ks2)
        return np.array(ca, np.int64), np.array(cb, np.int64)
    ca, _ = encrypt_reject(p1, ks[shift:] if shift else ks)
    cb, _ = encrypt_reject(p2, ks)
    return np.array(ca, np.int64), np.array(cb, np.int64)


def one_trial(n: int, shift: int, seed: int, shared: bool = True) -> dict:
    a, b = synth_pair(n, shift, seed, shared)
    true = score_keyshift(a, b, shift, LOGRATIO)
    rng = np.random.default_rng(seed + 99991)
    sh = [
        score_keyshift(rng.permutation(a), rng.permutation(b), shift, LOGRATIO)["score"]
        for _ in range(N_SHUF)
    ]
    mx = float(np.max(sh))
    sep = (true["score"] - float(np.mean(sh))) / (float(np.std(sh)) + 1e-9)
    return {
        "n": n, "shift": shift, "shared": shared, "seed": seed,
        "nB": true["nB"], "score": round(float(true["score"]), 3),
        "shuffle_max": round(mx, 3),
        "beats": bool(true["score"] > mx),
        "sep": round(float(sep), 2),
    }


def plant_block(n: int, shift: int, shared: bool, base: int) -> dict:
    rows = [one_trial(n, shift, base + i, shared) for i in range(N_TRIAL)]
    wins = sum(r["beats"] for r in rows)
    return {
        "n": n, "shift": shift, "shared": shared,
        "wins": wins, "n_trial": N_TRIAL,
        "ok": (wins >= 5) if shared else (wins <= 1),
        "rows": rows,
    }


def run_plants() -> dict:
    print("plant n=400 S=37 shared ...", flush=True)
    p400_37 = plant_block(400, 37, True, 3301)
    print("  wins", p400_37["wins"], "/", N_TRIAL, flush=True)
    print("plant n=400 S=37 indep ...", flush=True)
    p400_ind = plant_block(400, 37, False, 4301)
    print("  wins", p400_ind["wins"], "/", N_TRIAL, flush=True)
    print("plant n=277 S=37 shared ...", flush=True)
    p277_37 = plant_block(277, 37, True, 5301)
    print("  wins", p277_37["wins"], "/", N_TRIAL, flush=True)
    print("plant n=400 S=0 shared ...", flush=True)
    p400_0 = plant_block(400, 0, True, 6301)
    print("  wins", p400_0["wins"], "/", N_TRIAL, flush=True)
    ok = bool(p400_37["ok"] and p400_ind["ok"])
    return {
        "ok": ok,
        "threshold": "n=400 shift=37 shared wins>=5/6 AND indep wins<=1/6",
        "accept_window_37": list(accept_window(37)),
        "n400_s37_shared": p400_37,
        "n400_s37_indep": p400_ind,
        "n277_s37_shared": p277_37,
        "n400_s0_shared": p400_0,
        "note": "n=277 is LP page max; not required for plant_ok (prefix400 scale is n=400)",
    }


def n80_pages():
    out = {}
    for s in range(15, 71):
        v = np.array(idxs_of(s), np.int64)
        if len(v) >= MIN_N:
            out[s] = v
    return out


def scan(pages: dict, p400: np.ndarray):
    """prefix400 vs each n>=80 page, marked key-shifts, both who-shifted."""
    hits = []
    tested = 0
    keys = sorted(pages)
    # prefix400 vs pages
    for s in keys:
        for shift in MARKED_S:
            for who, a, b in (("p400_vs_page", p400, pages[s]),
                              ("page_vs_p400", pages[s], p400)):
                tested += 1
                sc = score_keyshift(a, b, shift, LOGRATIO)
                hits.append((sc["score"], who, s, shift, sc["nB"]))
    hits.sort(key=lambda x: -x[0])
    return hits, tested


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    plant = run_plants()
    print("plant_ok", plant["ok"], flush=True)
    if not plant["ok"]:
        result = {
            "experiment": EXPERIMENT,
            "family": "skip-aware depth: key-prefix accept-count (not CT-crop=S), tight-band match/gap",
            "plant": plant,
            "tested": 0,
            "keep_bar_hits": 0,
            "verified_new_unsolved_runes": 0,
            "aborted": "plant failed — decoder does not majority-beat shuffle on reject-filtered shift-37 at n=400, or independent pads fire",
            "unsolved_runes_total": 12956,
        }
        (OUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")
        print("PLANT FAILED")
        return

    p400 = np.array(prefix(400), np.int64)
    pages = n80_pages()
    hits, tested = scan(pages, p400)
    observed = hits[0][0] if hits else -1e12
    print(f"observed max={observed:.3f} tested={tested}", flush=True)
    rng = np.random.default_rng(3301)
    surr = []
    # 4 surrogate maxes: permute prefix400 and a sample of pages
    sample = [pages[k] for k in sorted(pages)[:8]]
    for r in range(4):
        mx = -1e12
        pa = rng.permutation(p400)
        for pg in sample:
            pb = rng.permutation(pg)
            for shift in MARKED_S:
                sc = score_keyshift(pa, pb, shift, LOGRATIO)["score"]
                if sc > mx:
                    mx = sc
        surr.append(mx)
        print(f"  surrogate {r+1}/4 max={mx:.3f}", flush=True)
    exceeds = bool(observed > float(np.max(surr))) if surr else False
    top = [
        {"who": who, "split": f"split{s:03d}", "shift": sh, "nB": nB, "score": round(float(sc), 3)}
        for sc, who, s, sh, nB in hits[:8]
    ]
    result = {
        "experiment": EXPERIMENT,
        "family": "skip-aware depth: key-prefix accept-count (not CT-crop=S), tight-band match/gap",
        "keep_bar": "detection only; not a Latin decrypt",
        "plant": plant,
        "scan": {
            "prefix400": True,
            "n80_count": len(pages),
            "n80_pages": [f"split{s:03d}" for s in sorted(pages)],
            "tested": tested,
            "marked_S": list(MARKED_S),
            "observed_max": round(float(observed), 3),
            "surrogate_max": round(float(np.max(surr)), 3) if surr else None,
            "exceeds_surrogate": exceeds,
            "top": top,
        },
        "tested": tested,
        "keep_bar_hits": 0,
        "skeptic_review": {
            "verdict": "depth flag — not English" if exceeds else "null",
            "why": "score vs shuffle of the same keyshift statistic; no unique Latin",
        },
        "verified_new_unsolved_runes": 0,
        "unsolved_runes_total": 12956,
    }
    (OUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print("wrote", OUT / "result.json", "exceeds", exceeds, "new_runes", 0)


if __name__ == "__main__":
    main()
