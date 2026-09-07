#!/usr/bin/env python3
"""Where does the missing doublet mass go? (EXP-LP-BOUNDARY-DOUBLET-001, part 2)

EXP-LP-BOUNDARY-DOUBLET-001 part 1 showed the lag-1 deficit is stream-level (it
crosses word AND line boundaries at the same strength) and is confined to lag 1
(lags 2 and 3 sit exactly on the shuffle null).  That pins the rule to
"c[i] != c[i-1]" but does NOT say how the encoder enforced it.

Different enforcement rules put the missing probability mass in different places
in the first-difference distribution d = c[i] - c[i-1] (mod 29):

    R1  advance the key an extra step and re-emit   -> d=0 empty, d=1..28 FLAT
    R2  nudge the output (c := c+1 on collision)    -> d=0 empty, d=+1 DOUBLED
    R3  drop / skip the offending plaintext rune    -> d=0 empty, shape follows
                                                       the plaintext bigram
    R4  no rule; the key itself is anti-repeating   -> deficit would ride on the
                                                       key's own d-shape

Every skip-aware beam in this tree hard-codes R1.  R2 has never been tested, and
it is the cheapest rule a human scribe would actually apply at the page.

Also runs the decisive fixture control: page 56 (split_071) is the one solved page
that is genuinely polyalphabetic and whose plaintext is verified 85/85, so its
ciphertext doublet count says whether real Cicada ciphertext ever contains a
doublet at all.

No network. Appends to experiments/EXP-LP-BOUNDARY-DOUBLET-001/result.json.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from cicada.liber_primus.ciphers import apply_named  # noqa: E402
from cicada.liber_primus.fixtures import load_fixtures  # noqa: E402
from cicada.liber_primus.gematria import Gematria  # noqa: E402

from exp_boundary_doublet import page_pairs, UNSOLVED  # noqa: E402

GP = Gematria()
Q = 29
OUT = ROOT / "experiments" / "EXP-LP-BOUNDARY-DOUBLET-001"
RNG = np.random.default_rng(3301)
N_SHUFFLE = 4000


def delta_hist(pages):
    """Histogram of d = c[i+1]-c[i] mod 29 over all chained adjacent pairs."""
    h = np.zeros(Q, dtype=np.int64)
    for runes, labels in pages:
        for i, lab in enumerate(labels):
            if lab is None:
                continue
            h[(runes[i + 1] - runes[i]) % Q] += 1
    return h


def main():
    pages = [page_pairs(s) for s in UNSOLVED]
    pages = [p for p in pages if p[0]]
    obs = delta_hist(pages)
    n = int(obs.sum())

    # null: within-page shuffles (marginals + layout fixed)
    arrs = [(np.array(r), l) for r, l in pages]
    draws = np.zeros((N_SHUFFLE, Q), dtype=np.int64)
    for k in range(N_SHUFFLE):
        sh = []
        for r, l in arrs:
            rr = r.copy()
            RNG.shuffle(rr)
            sh.append((rr, l))
        draws[k] = delta_hist(sh)
    mu = draws.mean(axis=0)
    sd = draws.std(axis=0, ddof=1)
    z = (obs - mu) / sd

    print(f"first-difference distribution, unsolved splits 15-70, n={n} pairs")
    print(f"{'d':>3} {'obs':>6} {'null':>8} {'z':>7}   latin(d)")
    for d in range(Q):
        mark = "  <-- doublets" if d == 0 else ""
        print(f"{d:>3} {obs[d]:>6} {mu[d]:>8.1f} {z[d]:>7.2f}{mark}")

    missing = float(mu[0] - obs[0])
    nonzero_z = z[1:]
    print(f"\nmissing doublet mass : {missing:.1f} pairs")
    print(f"nonzero-d z          : min {nonzero_z.min():.2f}  max {nonzero_z.max():.2f}  "
          f"mean {nonzero_z.mean():.2f}")
    print(f"argmax nonzero d     : d={int(np.argmax(obs[1:]))+1} "
          f"(z={nonzero_z.max():.2f})")
    # chi-square flatness of the 28 nonzero cells
    o28 = obs[1:].astype(float)
    e28 = o28.sum() / 28.0
    chi2 = float(((o28 - e28) ** 2 / e28).sum())
    print(f"chi2 flatness of d=1..28 : {chi2:.1f} on 27 df "
          f"(expect ~27 +- {np.sqrt(2*27):.1f} if flat)")

    # R2 prediction: all missing mass lands on d=+1
    r2_pred = mu[1] + missing
    r2_z = (obs[1] - r2_pred) / sd[1]
    print(f"\nR2 (nudge c:=c+1) predicts d=+1 count ~ {r2_pred:.1f}; "
          f"observed {obs[1]} -> {r2_z:.2f} sigma from R2")
    print(f"R1 (key advance) predicts d=+1 count ~ {mu[1]+missing/28:.1f}; "
          f"observed {obs[1]} -> {(obs[1]-(mu[1]+missing/28))/sd[1]:.2f} sigma from R1")

    # ---- fixture control: does real Cicada ciphertext ever carry a doublet?
    fixtures = []
    for f in load_fixtures():
        ct = GP.rune_indices(f["ciphertext"])
        pt = apply_named(f["method"], ct, None)
        ctd = sum(1 for a, b in zip(ct, ct[1:]) if a == b)
        ptd = sum(1 for a, b in zip(pt, pt[1:]) if a == b)
        fixtures.append({
            "stage_id": f["stage_id"], "method": f["method"], "n": len(ct),
            "ct_doublets": ctd, "pt_doublets": ptd,
            "expected_at_chance": round((len(ct) - 1) / Q, 1),
        })
        print(f"\nfixture {f['stage_id']:22s} method={f['method']:12s} n={len(ct):4d} "
              f"ct_doublets={ctd} pt_doublets={ptd} "
              f"(chance {(len(ct)-1)/Q:.1f})")

    # ---- per-page dispersion of the 86 surviving doublets
    per_page = []
    for s, (runes, labels) in zip([x for x in UNSOLVED if page_pairs(x)[0]], pages):
        d = sum(1 for i, lab in enumerate(labels)
                if lab is not None and runes[i] == runes[i + 1])
        per_page.append({"split": s, "runes": len(runes), "doublets": d})
    cnt = np.array([p["doublets"] for p in per_page], float)
    ln = np.array([p["runes"] for p in per_page], float)
    exp = cnt.sum() * ln / ln.sum()
    chi2_p = float((((cnt - exp) ** 2) / np.maximum(exp, 1e-9)).sum())
    df = len(cnt) - 1
    print(f"\nper-page doublets: total {int(cnt.sum())} over {len(cnt)} pages; "
          f"chi2 {chi2_p:.1f} on {df} df (expect ~{df} +- {np.sqrt(2*df):.1f} if Poisson-uniform)")
    print(f"max page: split_{per_page[int(np.argmax(cnt))]['split']:03d} "
          f"with {int(cnt.max())} doublets")

    res_path = OUT / "result.json"
    res = json.loads(res_path.read_text(encoding="utf-8"))
    res["part2_delta_shape"] = {
        "n_pairs": n,
        "delta_observed": obs.tolist(),
        "delta_null_mean": [round(float(x), 2) for x in mu],
        "delta_z": [round(float(x), 2) for x in z],
        "missing_doublet_mass": round(missing, 1),
        "nonzero_chi2": round(chi2, 1),
        "nonzero_chi2_df": 27,
        "R2_nudge_sigma": round(float(r2_z), 2),
        "R1_keyadvance_sigma": round(float((obs[1]-(mu[1]+missing/28))/sd[1]), 2),
        "fixtures": fixtures,
        "per_page": per_page,
        "per_page_chi2": round(chi2_p, 1),
        "per_page_df": df,
    }
    res_path.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(f"\nupdated {res_path}")


if __name__ == "__main__":
    main()
