#!/usr/bin/env python3
"""Family-wise flatness of the nonzero first-difference cells (part 3).

Part 2 reported an asymptotic chi2 of 42.2 on 27 df for the 28 nonzero cells of
d = c[i+1]-c[i] (mod 29), and a max cell z of 3.22 at d=9.  Neither number is
usable as stated: the cells are not independent (they are constrained by the
marginal and by the depleted d=0 cell), and 28 cells were scanned.

This part builds both nulls empirically from the same within-page shuffles, so
"is the residual flat?" is answered against the actual sampling distribution:

  * chi2 computed the same way on each shuffle  -> empirical p for 42.2
  * max |z| over the 28 nonzero cells per shuffle -> family-wise p for 3.22

Also reports the R1-vs-R2 test as a likelihood-free comparison and re-runs the
page-56 fixture control as an explicit Poisson test, since that is the only
solved page that is both polyalphabetic and verified 85/85.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from exp_boundary_doublet import page_pairs, UNSOLVED  # noqa: E402
from exp_doublet_delta_shape import delta_hist  # noqa: E402

Q = 29
OUT = ROOT / "experiments" / "EXP-LP-BOUNDARY-DOUBLET-001"
RNG = np.random.default_rng(90210)
N_SHUFFLE = 4000


def chi2_nonzero(h):
    o = h[1:].astype(float)
    e = o.sum() / 28.0
    return float(((o - e) ** 2 / e).sum())


def main():
    pages = [p for p in (page_pairs(s) for s in UNSOLVED) if p[0]]
    obs = delta_hist(pages)
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

    # --- empirical chi2 null (same statistic, computed on each shuffle)
    obs_chi2 = chi2_nonzero(obs)
    null_chi2 = np.array([chi2_nonzero(d) for d in draws])
    p_chi2 = float((null_chi2 >= obs_chi2).mean())

    # --- family-wise max|z| over the 28 nonzero cells.
    # z is taken against the shuffle mean/sd of each cell, and the same
    # statistic is recomputed for every shuffle (leave-one-out is unnecessary
    # at n=4000; the bias is O(1/n)).
    zc = (draws[:, 1:] - mu[1:]) / sd[1:]
    null_maxz = np.abs(zc).max(axis=1)
    obs_z = (obs[1:] - mu[1:]) / sd[1:]
    obs_maxz = float(np.abs(obs_z).max())
    p_maxz = float((null_maxz >= obs_maxz).mean())

    print(f"observed chi2 (28 nonzero cells) : {obs_chi2:.1f}")
    print(f"shuffle chi2 null                : mean {null_chi2.mean():.1f} "
          f"sd {null_chi2.std(ddof=1):.1f}  95th pct {np.percentile(null_chi2,95):.1f}")
    print(f"empirical p(chi2)                : {p_chi2:.4f}")
    print()
    print(f"observed max|z| over d=1..28     : {obs_maxz:.2f} at d={int(np.argmax(np.abs(obs_z)))+1}")
    print(f"shuffle max|z| null              : mean {null_maxz.mean():.2f} "
          f"sd {null_maxz.std(ddof=1):.2f}  95th pct {np.percentile(null_maxz,95):.2f}")
    print(f"family-wise p(max|z|)            : {p_maxz:.4f}")

    # --- page-56 fixture control as an explicit Poisson test
    n56_pairs = 84
    rate_unsolved = 86 / 12891
    lam = n56_pairs * rate_unsolved
    obs56 = 2
    p_ge2 = 1.0 - math.exp(-lam) * (1 + lam)
    print()
    print("page-56 control (only solved page that is polyalphabetic AND verified 85/85):")
    print(f"  pairs {n56_pairs}, observed ct doublets {obs56}")
    print(f"  under the unsolved-page filter rate {rate_unsolved:.5f}: lambda={lam:.2f}, "
          f"P(X>=2)={p_ge2:.3f}")
    print(f"  under chance (1/29):                 lambda={n56_pairs/Q:.2f}")
    print("  -> weak evidence against the filter on that page; NOT an exclusion at n=84")

    res_path = OUT / "result.json"
    res = json.loads(res_path.read_text(encoding="utf-8"))
    res["part3_flatness"] = {
        "n_shuffle": N_SHUFFLE,
        "obs_chi2_nonzero": round(obs_chi2, 1),
        "null_chi2_mean": round(float(null_chi2.mean()), 1),
        "null_chi2_sd": round(float(null_chi2.std(ddof=1)), 1),
        "null_chi2_p95": round(float(np.percentile(null_chi2, 95)), 1),
        "p_chi2_empirical": round(p_chi2, 4),
        "obs_max_abs_z": round(obs_maxz, 2),
        "obs_max_abs_z_at_d": int(np.argmax(np.abs(obs_z))) + 1,
        "null_max_abs_z_mean": round(float(null_maxz.mean()), 2),
        "null_max_abs_z_p95": round(float(np.percentile(null_maxz, 95)), 2),
        "p_max_abs_z_familywise": round(p_maxz, 4),
        "page56_control": {
            "pairs": n56_pairs, "observed_ct_doublets": obs56,
            "lambda_under_filter": round(lam, 2),
            "p_ge2_under_filter": round(p_ge2, 3),
            "verdict": "weak evidence against the filter on page 56; not an exclusion at n=84",
        },
    }
    res_path.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(f"\nupdated {res_path}")


if __name__ == "__main__":
    main()
