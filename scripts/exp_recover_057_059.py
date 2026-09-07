#!/usr/bin/env python3
"""Latin recovery on the ALIGN-001 flag: split057 vs reversed split059.

Not a new detector. WORD-DEPTH already scored every rigid reverse alignment
family-wise (max z 4.07 < 5.10). This writes the pair-local numbers so the
flag is closed as a decrypt candidate: stage2 LLR and stage3 word-beam vs
shuffles of this pair only. Keep bar is not used.
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
from exp_word_depth import (  # noqa: E402
    LM,
    ends_from_words,
    idxs_of,
    page_text,
    stage2_llr,
    stage3_beam,
    words_of,
)

GP = Gematria()
Q = 29
OUT = CICADA_ROOT / "experiments" / "EXP-LP-RECOVER-057-059-001"
RNG = np.random.default_rng(3301)
N_SHUF = 16
FAMILY_Z = 5.10  # WORD-DEPTH-001 surrogate-cascade max


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    a = np.array(idxs_of(57), np.int64)
    b = np.array(idxs_of(59), np.int64)
    br = b[::-1]
    n = min(len(a), len(br))
    a, D = a[:n], (a[:n] - br[:n]) % Q
    endsA = ends_from_words(words_of(page_text(57)), n)
    # Reverse of the rune stream: word [s,e] maps to [n-1-e, n-1-s]; end at old start.
    ws = words_of(page_text(59))
    endsB = np.zeros(n, bool)
    p = 0
    for w in ws:
        s, e = p, p + len(w) - 1
        p = e + 1
        rs = n - 1 - e
        re = n - 1 - s
        if 0 <= re < n:
            endsB[re] = True
    endsB[-1] = True
    print("n", n, "endsA", int(endsA.sum()), "endsB", int(endsB.sum()), flush=True)
    lm = LM()
    s2 = stage2_llr(lm, D)
    print("stage2", s2, flush=True)
    sc3, pa, pb = stage3_beam(lm, D, endsA, endsB)
    lat_a, lat_b = GP.latin_stream(pa), GP.latin_stream(pb)
    print("stage3", sc3, lat_a[:72], flush=True)
    print("         ", lat_b[:72], flush=True)

    sh2, sh3 = [], []
    for i in range(N_SHUF):
        Ds = (a - RNG.permutation(br[:n])) % Q
        sh2.append(stage2_llr(lm, Ds))
        sc, _, _ = stage3_beam(lm, Ds, endsA, endsB)
        sh3.append(sc)
        print(f"  sh {i+1}/{N_SHUF} s2={sh2[-1]:.2f} s3={sh3[-1]:.2f}", flush=True)
    z2 = (s2 - float(np.mean(sh2))) / (float(np.std(sh2)) + 1e-9)
    z3 = (sc3 - float(np.mean(sh3))) / (float(np.std(sh3)) + 1e-9)
    result = {
        "experiment": "EXP-LP-RECOVER-057-059-001",
        "family": "word-depth recovery on ALIGN-001 flagged pair (rigid reverse)",
        "n": n,
        "stage2": round(float(s2), 3),
        "stage2_z": round(float(z2), 2),
        "stage2_shuffle_max": round(float(np.max(sh2)), 3),
        "stage3": round(float(sc3), 3),
        "stage3_z": round(float(z3), 2),
        "stage3_shuffle_max": round(float(np.max(sh3)), 3),
        "head_a": lat_a[:96],
        "head_b": lat_b[:96],
        "beats_pair_shuffle_s2": bool(s2 > max(sh2)),
        "beats_pair_shuffle_s3": bool(sc3 > max(sh3)),
        "clears_word_depth_family_z": bool(z2 >= FAMILY_Z or z3 >= FAMILY_Z),
        "readable_english": False,
        "skeptic_review": {
            "verdict": "null",
            "why": "stage3 emits word-salad on any input; only z vs shuffle counts. "
                   "Family threshold from WORD-DEPTH-001 is 5.10.",
        },
        "verified_new_unsolved_runes": 0,
    }
    (OUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print("z2", result["stage2_z"], "z3", result["stage3_z"],
          "family", result["clears_word_depth_family_z"])


if __name__ == "__main__":
    main()
