#!/usr/bin/env python3
"""Same-start skip-aware depth on n≥400 concatenations (HANDOFF 5c remainder).

Page-scale (n≤277) same-start and shifted crops do not majority-plant.
ALIGN plants filtered same-start at n=400. This scores:
  1) red-ink section concatenations
  2) non-overlapping 400-rune blocks of the unsolved book
against the same-start forward HMM, with shuffle surrogates.
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

OUT = CICADA_ROOT / "experiments" / "EXP-LP-SKIPAWARE-DEPTH-SECTIONS-001"
# onion inclusive-start, exclusive-end (heading script); skip solved 56–57
SECTIONS = [
    (0, 3, "s0"),
    (3, 8, "s3"),
    (8, 15, "s8"),
    (15, 23, "s15"),
    (23, 27, "s23"),
    (27, 33, "s27"),
    (33, 40, "s33"),
    (40, 54, "s40"),
    (54, 56, "s54"),
]
CHUNK = 400
N_SURR = 4
MIN_N = 400


def section_stream(o0: int, o1: int) -> np.ndarray:
    out: list[int] = []
    for o in range(o0, o1):
        if o > 55:
            break
        out.extend(idxs_of(15 + o))
    return np.array(out, np.int64)


def plant_same_start(n: int) -> dict:
    a, b = synth_pair(n, True, 0)
    true = forward_score(a, b)
    sh = [forward_score(RNG.permutation(a), RNG.permutation(b)) for _ in range(N_SHUF)]
    sep = (true - float(np.mean(sh))) / (float(np.std(sh)) + 1e-9)
    row = {
        "n": n, "true": round(float(true), 3),
        "shuffle_max": round(float(np.max(sh)), 3),
        "sep": round(float(sep), 2),
        "beats": bool(true > float(np.max(sh))),
    }
    print("plant", row, flush=True)
    return row


def score_catalog(cat: dict[str, np.ndarray]):
    keys = sorted(cat)
    hits, n = [], 0
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            for tag, vb in (("fwd", cat[b]), ("rev", cat[b][::-1])):
                n += 1
                s = forward_score(cat[a], vb)
                hits.append((s, a, b, tag))
    hits.sort(key=lambda x: -x[0])
    return hits, n


def local_null(hits, cat, k: int = 8):
    rows = []
    for z, a, b, tag in hits[:k]:
        va, vb = cat[a], (cat[b] if tag == "fwd" else cat[b][::-1])
        sh = [forward_score(RNG.permutation(va), RNG.permutation(vb)) for _ in range(N_SHUF)]
        sep = (z - float(np.mean(sh))) / (float(np.std(sh)) + 1e-9)
        row = {
            "a": a, "b": b, "dir": tag, "score": round(float(z), 3),
            "shuffle_max": round(float(np.max(sh)), 3),
            "sep": round(float(sep), 2),
            "beats": bool(z > float(np.max(sh))),
        }
        rows.append(row)
        print("top", row, flush=True)
    return rows


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    plants = [plant_same_start(400) for _ in range(6)]
    wins = sum(1 for p in plants if p["beats"])
    plant_ok = wins >= 4
    print("plant_majority", wins, "/6", plant_ok, flush=True)
    if not plant_ok:
        (OUT / "result.json").write_text(json.dumps({
            "experiment": "EXP-LP-SKIPAWARE-DEPTH-SECTIONS-001",
            "plant": plants,
            "plant_wins": wins,
            "verified_new_unsolved_runes": 0,
            "aborted": "same-start n=400 does not majority-plant (6 trials)",
        }, indent=2) + "\n")
        print("PLANT FAILED")
        return

    secs = {}
    for o0, o1, name in SECTIONS:
        v = section_stream(o0, o1)
        if len(v) >= MIN_N:
            secs[f"{name}_head"] = v[:CHUNK]
            secs[f"{name}_tail"] = v[-CHUNK:]
            print(f"section {name} n={len(v)} -> head+tail {CHUNK}", flush=True)

    book: list[int] = []
    for s in range(15, 71):
        book.extend(idxs_of(s))
    chunks = {}
    for i in range(0, len(book) - CHUNK + 1, CHUNK):
        chunks[f"c{i:05d}"] = np.array(book[i:i + CHUNK], np.int64)
    print(f"book={len(book)} chunks={len(chunks)} sections={len(secs)}", flush=True)

    results = {}
    any_flag = False
    for label, cat in (("sections", secs), ("chunks400", chunks)):
        hits, n = score_catalog(cat)
        print(f"{label} scored {n} max={hits[0][0]:.3f}", flush=True)
        surr = []
        for r in range(N_SURR):
            sh = {k: RNG.permutation(v) for k, v in cat.items()}
            sh_hits, _ = score_catalog(sh)
            surr.append(sh_hits[0][0] if sh_hits else -1e12)
            print(f"  {label} surr {r+1}/{N_SURR} {surr[-1]:.3f}", flush=True)
        exceeds = bool(hits and hits[0][0] > float(np.max(surr)))
        top = local_null(hits, cat)
        # Pair-local sep on the selected top-k is look-elsewhere (ALIGN).
        # Family-wise surrogate max is the gate.
        flag = exceeds
        any_flag = any_flag or flag
        results[label] = {
            "n_streams": len(cat),
            "scores": n,
            "observed_max": round(float(hits[0][0]), 3) if hits else None,
            "surrogate_max": round(float(np.max(surr)), 3) if surr else None,
            "exceeds_surrogate": exceeds,
            "top_local": top,
            "flag": flag,
        }

    result = {
        "experiment": "EXP-LP-SKIPAWARE-DEPTH-SECTIONS-001",
        "family": "same-start skip-aware depth on n>=400 sections and 400-rune blocks",
        "keep_bar": "detection only; not a Latin decrypt",
        "plant": plants,
        "scans": results,
        "skeptic_review": {
            "verdict": "depth flag — not a decrypt" if any_flag else "null",
        },
        "verified_new_unsolved_runes": 0,
    }
    (OUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print("wrote", OUT / "result.json", "flag", any_flag)


if __name__ == "__main__":
    main()
