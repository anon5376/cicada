#!/usr/bin/env python3
"""Known-shift CT-crop depth at Liber Primus page length (HANDOFF 5c remainder).

Max-over-crops failed at n=400 (look-elsewhere). This scores each motivated
CT prefix-crop against shuffles of *that same crop* — no extra looks.
If a reject-filtered pad offset plants at n<=277 under that rule, scan
unsolved pairs at those shifts only.
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

OUT = CICADA_ROOT / "experiments" / "EXP-LP-SKIPAWARE-DEPTH-PAGESHIFT-001"
SHIFTS = (15, 37)  # 56 failed plant at n=242/277 (crop too large vs page)
MIN_N = 80
N_PLANT = 6
UNSOLVED = list(range(15, 71))


def crop_score(a: np.ndarray, b: np.ndarray, shift: int) -> float:
    if shift < 0:
        return crop_score(b, a, -shift)
    if len(b) - shift < MIN_N or len(a) < MIN_N:
        return -1e12
    L = min(len(a), len(b) - shift)
    return forward_score(a[:L], b[shift:shift + L])


def plant_one(n: int, shift: int) -> dict:
    a, b = synth_pair(n, True, shift)
    true = crop_score(a, b, shift)
    sh = [crop_score(RNG.permutation(a), RNG.permutation(b), shift) for _ in range(N_SHUF)]
    sep = (true - float(np.mean(sh))) / (float(np.std(sh)) + 1e-9)
    row = {
        "n": n, "shift": shift, "lens": [int(len(a)), int(len(b))],
        "true": round(float(true), 3),
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
                for sh in SHIFTS:
                    n += 1
                    s_ab = crop_score(pg[a], vb, sh)
                    s_ba = crop_score(vb, pg[a], sh)
                    s, which = (s_ab, f"B+{sh}") if s_ab >= s_ba else (s_ba, f"A+{sh}")
                    hits.append((s, a, b, tag, which))
    hits.sort(key=lambda x: -x[0])
    return hits, n


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for n in (242, 277):
        for sh in SHIFTS:
            for _ in range(N_PLANT):
                rows.append(plant_one(n, sh))
    # majority per (n, shift)
    groups = {}
    for r in rows:
        groups.setdefault((r["n"], r["shift"]), []).append(r["beats"])
    maj = {f"n{n}_s{sh}": {"wins": sum(v), "n": len(v), "ok": sum(v) >= 4}
           for (n, sh), v in groups.items()}
    shifted_ok = all(v["ok"] for v in maj.values())
    plant = {"ok": bool(shifted_ok), "majority": maj, "rows": rows, "n_plant": N_PLANT}
    print("plant_ok", plant["ok"], "majority", maj, flush=True)
    if not plant["ok"]:
        (OUT / "result.json").write_text(json.dumps({
            "experiment": "EXP-LP-SKIPAWARE-DEPTH-PAGESHIFT-001",
            "family": "known-shift CT-crop forward at n<=277 (no max-over-crops)",
            "plant": plant,
            "verified_new_unsolved_runes": 0,
            "aborted": "shifted CT-crop does not majority-plant at page length",
            "note": "First-seed 15/37 wins were not stable across 6 trials.",
        }, indent=2) + "\n")
        print("PLANT FAILED — no page scan")
        return

    uns = {s: np.array(idxs_of(s), np.int64) for s in UNSOLVED}
    uns = {s: v for s, v in uns.items() if len(v) >= MIN_N}
    hits, n_pair = scan(uns)
    print(f"observed max={hits[0][0]:.3f} scores={n_pair}", flush=True)
    # pair-local shuffles on top 8 only (full-scan surrogates are look-elsewhere again)
    top_local = []
    for z, a, b, tag, which in hits[:8]:
        va, vb = uns[a], (uns[b] if tag == "fwd" else uns[b][::-1])
        sh_amt = int(which.split("+")[1])
        first = which[0]
        shufs = []
        for _ in range(N_SHUF):
            sa, sb = RNG.permutation(va), RNG.permutation(vb)
            if first == "B":
                shufs.append(crop_score(sa, sb, sh_amt))
            else:
                shufs.append(crop_score(sb, sa, sh_amt))
        sep = (z - float(np.mean(shufs))) / (float(np.std(shufs)) + 1e-9)
        top_local.append({
            "a": f"split{a:03d}", "b": f"split{b:03d}", "dir": tag, "crop": which,
            "score": round(float(z), 3),
            "shuffle_max": round(float(np.max(shufs)), 3),
            "sep": round(float(sep), 2),
            "beats": bool(z > float(np.max(shufs))),
        })
        print("top", top_local[-1], flush=True)
    exceeds = any(t["beats"] and t["sep"] >= 3.0 for t in top_local)
    result = {
        "experiment": "EXP-LP-SKIPAWARE-DEPTH-PAGESHIFT-001",
        "family": "known-shift CT-crop forward at n<=277 (HANDOFF 5c)",
        "keep_bar": "detection only; not a Latin decrypt",
        "plant": {k: plant[k] for k in ("ok", "majority", "n_plant")},
        "pairwise_unsolved": {
            "pages": len(uns),
            "scores": n_pair,
            "observed_max": round(float(hits[0][0]), 3),
            "top_local": top_local,
            "flag": exceeds,
        },
        "skeptic_review": {"verdict": "depth flag — not a decrypt" if exceeds else "null"},
        "verified_new_unsolved_runes": 0,
    }
    (OUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print("wrote", OUT / "result.json", "flag", exceeds)


if __name__ == "__main__":
    main()
