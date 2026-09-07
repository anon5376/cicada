#!/usr/bin/env python3
"""Where does the anti-doublet filter stop? (EXP-LP-BOUNDARY-DOUBLET-001)

WHY THIS IS A NEW MEASUREMENT
-----------------------------
Every "skip-aware" experiment in this tree assumes the anti-repeat rule is applied
to the *continuous rune stream* of a page: encrypt_reject() walks the whole page and
burns an extra key symbol whenever the output would equal the previous output rune.
That assumption has never been tested against the transcription's own structure.

The rtkd transcription carries two kinds of boundary that survive the cipher:
`-` word separators and `/` line breaks (EXP-LP-WORD-DEPTH-001 established that the
word lengths are not enciphered). So each adjacent rune pair can be labelled by what
sits between the two runes, and the doublet deficit can be measured *per class*:

    none    the two runes are directly adjacent inside one word
    sep     a word boundary sits between them
    brk     a line break sits between them
    punct   punctuation sits between them

Two hypotheses make opposite predictions:

    H_stream  the rule sees the whole page  -> every class is suppressed
    H_word    the rule resets at each word  -> `none` is suppressed, `sep` is at chance

The global count (86 doublets vs ~445 expected, EXP-LP-COND-PREV-IOC-001) cannot
separate these, because it pools all classes. This experiment separates them.

NULL
----
Shuffling the runes within a page preserves the rune marginal and the boundary
layout while destroying the position-rune link, which is exactly H0. Expected
counts and z-scores come from 2000 such shuffles per corpus, not from a formula.

CONTROLS
--------
The same instrument is run on the solved region (splits 0-14) and the two solved
fixture pages (071 = onion 56, 072 = onion 57). Those pages are English or
near-English in the clear, so the instrument must NOT report a deficit there.

No network. Writes only experiments/EXP-LP-BOUNDARY-DOUBLET-001/result.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cicada.liber_primus.gematria import Gematria  # noqa: E402

GP = Gematria()
Q = 29
PAGE_DIR = ROOT / "corpus/normalized/rtkd_pages"
OUT = ROOT / "experiments" / "EXP-LP-BOUNDARY-DOUBLET-001"
N_SHUFFLE = 2000
RNG = np.random.default_rng(3301)

UNSOLVED = list(range(15, 71))
SOLVED_EARLY = list(range(0, 15))
FIXTURE_PAGES = [71, 72]

CLASSES = ("none", "sep", "brk", "punct")


def page_pairs(split: int):
    """Adjacent rune pairs of one page, each labelled by the material between them.

    Returns (runes, labels) where labels[i] describes the gap between rune i and
    rune i+1.  `number` and `layout` tokens (the page-56 hex block, `&` marks)
    break the chain entirely: those pairs are dropped, not labelled.
    """
    p = PAGE_DIR / f"split_{split:03d}.txt"
    if not p.exists():
        return [], []
    toks = GP.tokenize(p.read_text(encoding="utf-8"))
    runes: list[int] = []
    labels: list[str | None] = []
    gap: set[str] = set()
    broken = False
    for t in toks:
        if t.kind == "rune":
            if runes:
                if broken:
                    labels.append(None)
                elif "punct" in gap:
                    labels.append("punct")
                elif "break" in gap:
                    labels.append("brk")
                elif "sep" in gap:
                    labels.append("sep")
                else:
                    labels.append("none")
            runes.append(t.index)
            gap = set()
            broken = False
        elif t.kind in ("sep", "break", "punct"):
            gap.add(t.kind)
        elif t.kind in ("number", "layout", "other"):
            broken = True
    return runes, labels


def corpus(splits: list[int]):
    return [page_pairs(s) for s in splits if page_pairs(s)[0]]


def count_by_class(pages, lag: int = 1):
    """Observed equal-pairs per class at the given lag (lag 1 = adjacent)."""
    obs = {c: 0 for c in CLASSES}
    tot = {c: 0 for c in CLASSES}
    for runes, labels in pages:
        for i, lab in enumerate(labels):
            if lab is None:
                continue
            j = i + lag
            if j >= len(runes):
                continue
            # for lag>1 the label is still the gap at the *first* step
            tot[lab] += 1
            if runes[i] == runes[j]:
                obs[lab] += 1
    return obs, tot


def shuffle_null(pages, lag: int, n: int):
    """Within-page rune shuffles: preserves marginals + layout, kills position link."""
    draws = {c: np.zeros(n, dtype=np.int64) for c in CLASSES}
    arrs = [(np.array(r), l) for r, l in pages]
    for k in range(n):
        shuffled = []
        for r, l in arrs:
            rr = r.copy()
            RNG.shuffle(rr)
            shuffled.append((rr, l))
        o, _ = count_by_class(shuffled, lag)
        for c in CLASSES:
            draws[c][k] = o[c]
    return draws


def report(name: str, splits: list[int], lags=(1, 2, 3)):
    pages = corpus(splits)
    n_runes = sum(len(r) for r, _ in pages)
    out = {"corpus": name, "splits": splits, "pages": len(pages), "runes": n_runes,
           "ioc": None, "lags": {}}

    allr = np.concatenate([np.array(r) for r, _ in pages]) if pages else np.array([])
    if allr.size:
        cnt = np.bincount(allr, minlength=Q).astype(float)
        p = cnt / cnt.sum()
        out["ioc"] = round(float((p * p).sum()), 5)

    for lag in lags:
        obs, tot = count_by_class(pages, lag)
        null = shuffle_null(pages, lag, N_SHUFFLE)
        rows = {}
        for c in CLASSES:
            if tot[c] == 0:
                continue
            mu = float(null[c].mean())
            sd = float(null[c].std(ddof=1))
            z = (obs[c] - mu) / sd if sd > 0 else 0.0
            rows[c] = {
                "pairs": tot[c],
                "observed": obs[c],
                "rate": round(obs[c] / tot[c], 5),
                "null_mean": round(mu, 2),
                "null_sd": round(sd, 2),
                "null_rate": round(mu / tot[c], 5),
                "z": round(float(z), 2),
                "ratio_obs_over_null": round(obs[c] / mu, 3) if mu > 0 else None,
            }
        tot_obs = sum(obs[c] for c in CLASSES)
        tot_pairs = sum(tot[c] for c in CLASSES)
        tot_null = np.zeros(N_SHUFFLE)
        for c in CLASSES:
            tot_null = tot_null + null[c]
        rows["ALL"] = {
            "pairs": tot_pairs, "observed": tot_obs,
            "rate": round(tot_obs / tot_pairs, 5) if tot_pairs else None,
            "null_mean": round(float(tot_null.mean()), 2),
            "null_sd": round(float(tot_null.std(ddof=1)), 2),
            "z": round(float((tot_obs - tot_null.mean()) / tot_null.std(ddof=1)), 2),
            "ratio_obs_over_null": round(tot_obs / tot_null.mean(), 3),
        }
        out["lags"][str(lag)] = rows
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    res = {
        "experiment_id": "EXP-LP-BOUNDARY-DOUBLET-001",
        "question": "Does the anti-doublet rule apply to the whole rune stream, "
                    "or does it reset at transcribed word / line boundaries?",
        "null": f"{N_SHUFFLE} within-page rune shuffles (marginals and layout fixed)",
        "mapping_version": GP.version,
        "corpora": [],
    }
    for name, splits in (
        ("unsolved_15_70", UNSOLVED),
        ("solved_early_0_14", SOLVED_EARLY),
        ("fixture_pages_71_72", FIXTURE_PAGES),
    ):
        r = report(name, splits)
        res["corpora"].append(r)
        print(f"\n=== {name}  pages={r['pages']} runes={r['runes']} IoC={r['ioc']} ===")
        for lag, rows in r["lags"].items():
            print(f"  lag {lag}:")
            for c, v in rows.items():
                print(f"    {c:6s} pairs={v['pairs']:6d} obs={v['observed']:5d} "
                      f"rate={v['rate']} null={v['null_rate'] if 'null_rate' in v else '-'} "
                      f"ratio={v['ratio_obs_over_null']} z={v['z']}")
    (OUT / "result.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(f"\nwrote {OUT/'result.json'}")


if __name__ == "__main__":
    main()
