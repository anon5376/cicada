#!/usr/bin/env python3
"""Skip-aware depth at a nonzero pad offset (HANDOFF 5c remainder).

Same-start match/gap forward plants. A pad that starts 37 keys later does not,
even with a wide band: the model’s gap cost is calibrated for 1/29 skips, not
a long unmatched prefix, so it prefers a noisy diagonal.

This decoder *crops* a short prefix of either page (blind max over a small
offset set) and then runs the same-start forward score. Shuffle takes the
same max, so the extra looks are priced in.
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
from exp_depth_kappa import idxs_of  # noqa: E402
from exp_skipaware_depth_align import (  # noqa: E402
    N_SHUF,
    RNG,
    forward_score,
    synth_pair,
)

OUT = CICADA_ROOT / "experiments" / "EXP-LP-SKIPAWARE-DEPTH-OFFSET-001"
# motivated + a short grid; shuffle maximises over the same set
OFFSETS = (0, 8, 15, 29, 37, 42, 56)
MIN_N = 80
N_SURR = 4
UNSOLVED = list(range(15, 71))


def max_crop_score(a: np.ndarray, b: np.ndarray) -> tuple[float, str]:
    best = (-1e12, "none")
    for k in OFFSETS:
        if len(b) - k >= MIN_N:
            L = min(len(a), len(b) - k)
            s = forward_score(a[:L], b[k:k + L])
            if s > best[0]:
                best = (s, f"B+{k}")
        if k and len(a) - k >= MIN_N:
            L = min(len(a) - k, len(b))
            s = forward_score(a[k:k + L], b[:L])
            if s > best[0]:
                best = (s, f"A+{k}")
    return best


def plant_one(n: int, shift: int) -> dict:
    a, b = synth_pair(n, True, shift)
    true, where = max_crop_score(a, b)
    sh = []
    for _ in range(N_SHUF):
        sh.append(max_crop_score(RNG.permutation(a), RNG.permutation(b))[0])
    sep = (true - float(np.mean(sh))) / (float(np.std(sh)) + 1e-9)
    row = {
        "n": n, "shift": shift, "lens": [int(len(a)), int(len(b))],
        "true": round(float(true), 3), "where": where,
        "shuffle_max": round(float(np.max(sh)), 3),
        "sep": round(float(sep), 2),
        "beats": bool(true > float(np.max(sh))),
    }
    print("plant_row", row, flush=True)
    return row


def scan(pg: dict[int, np.ndarray]):
    keys = sorted(pg)
    hits, n = [], 0
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            for tag, vb in (("fwd", pg[b]), ("rev", pg[b][::-1])):
                n += 1
                s, where = max_crop_score(pg[a], vb)
                hits.append((s, a, b, tag, where))
                if n % 200 == 0:
                    print(f"  scored {n}", flush=True)
    hits.sort(key=lambda x: -x[0])
    return hits, n


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = [
        plant_one(400, 0),
        plant_one(400, 15),
        plant_one(400, 37),
        plant_one(800, 37),
        plant_one(400, 56),
    ]
    # shift 0 and 15/37/56 at n=400; 37 also at 800
    ok = rows[0]["beats"] and rows[2]["beats"] and rows[3]["beats"]
    plant = {"ok": ok, "rows": rows, "offsets": list(OFFSETS)}
    print("plant_ok", ok, flush=True)
    if not ok:
        (OUT / "result.json").write_text(json.dumps({
            "experiment": "EXP-LP-SKIPAWARE-DEPTH-OFFSET-001",
            "family": "prefix-crop then same-start match/gap forward",
            "plant": plant,
            "verified_new_unsolved_runes": 0,
            "aborted": "offset plant failed",
        }, indent=2) + "\n")
        print("PLANT FAILED")
        return

    uns = {s: np.array(idxs_of(s), np.int64) for s in UNSOLVED}
    uns = {s: v for s, v in uns.items() if len(v) >= MIN_N}
    hits, n_pair = scan(uns)
    observed = hits[0][0]
    print(f"observed max={observed:.3f} pairs={n_pair} top={hits[0][1:]}")
    surr = []
    for r in range(N_SURR):
        sh = {s: RNG.permutation(v) for s, v in uns.items()}
        sh_hits, _ = scan(sh)
        surr.append(sh_hits[0][0])
        print(f"  surrogate {r+1}/{N_SURR} max={surr[-1]:.3f}", flush=True)
    exceeds = bool(observed > float(np.max(surr)))
    top = [{"a": f"split{a:03d}", "b": f"split{b:03d}", "dir": tag, "where": w, "fwd": round(s, 3)}
           for s, a, b, tag, w in hits[:8]]
    (OUT / "result.json").write_text(json.dumps({
        "experiment": "EXP-LP-SKIPAWARE-DEPTH-OFFSET-001",
        "family": "prefix-crop then same-start match/gap forward (nonzero pad offset)",
        "plant": plant,
        "pairwise_unsolved": {
            "pages": len(uns), "pair_directions": n_pair,
            "observed_max": round(float(observed), 3),
            "surrogate_max": round(float(np.max(surr)), 3),
            "exceeds_surrogate": exceeds, "top": top,
        },
        "skeptic_review": {"verdict": "depth flag — not a decrypt" if exceeds else "null"},
        "verified_new_unsolved_runes": 0,
    }, indent=2) + "\n")
    print("wrote exceeds", exceeds)


if __name__ == "__main__":
    main()
