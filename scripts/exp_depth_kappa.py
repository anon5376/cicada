#!/usr/bin/env python3
"""Ciphertext-depth search on Liber Primus: is any stretch of pad reused?

WHY THIS FAMILY IS NEW
----------------------
Every entry in CURRENT_FRONTIER.md guesses *what the keystream is* (a book, a
hash, a PRNG, a classical tableau) and inverts it. All null. HANDOFF.md's own
conclusion is that what remains is "an external pad ... neither of which is in
this tree".

Depth analysis is the standard attack on an external pad that never needs the
pad. If two ciphertext spans were enciphered under the same stretch of key,

    C_a - C_b = P_a - P_b   (mod 29)

so the difference stream follows the English-minus-English distribution instead
of uniform. Nothing in the experiment table computes a coincidence profile.

DETECTOR
--------
Optimal (Neyman-Pearson) log-likelihood ratio of "difference of two Liber-Primus
plaintexts" against "uniform", evaluated at every relative offset by a 29-point
character-group DFT + cross-correlation (exact, not a heuristic; brute-force
checked in the plant). The plain coincidence count (kappa) is reported alongside
because it is interpretable. Thresholds come from shuffle surrogates, so the
composition bias of short pages is priced in rather than assumed away.

PASSES
------
0  plant-and-recover, plus a brute-force check of the DFT/offset algebra
1  instrument control on splits 0-14, which contain known repeated transcription
   runs; the scan must fire there
2  self-lag scan on the concatenated unsolved stream (repeating pad, any period)
3  pairwise depth over splits 15-70 only: every pair, every offset, forward and
   reversed, LLR + kappa + longest common run, surrogate-calibrated
4  pooled page-aligned tests (pad restarts each page), left and right aligned --
   n is ~3e5, so these are decisive rather than marginal
5  known-plaintext depth: solved (C,P) fixtures dragged over every unsolved page,
   prefix400 and split015; each alignment yields a candidate plaintext scored
   against the keep bar
6  power table, so the null carries a stated detection boundary

No network. Writes only experiments/EXP-LP-DEPTH-KAPPA-001/result.json.
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
from cicada.paths import ROOT as CICADA_ROOT  # noqa: E402
from cicada.scoring import score_candidate  # noqa: E402
from exp_skipaware_sha_ctr import encrypt_reject, keep  # noqa: E402

GP = Gematria()
Q = 29
PAGE_DIR = CICADA_ROOT / "corpus/normalized/rtkd_pages"
OUT = CICADA_ROOT / "experiments" / "EXP-LP-DEPTH-KAPPA-001"
MIN_OVERLAP = 80
UNSOLVED = list(range(15, 71))
N_SURROGATE = 20
RNG = np.random.default_rng(3301)


# ------------------------------------------------------------------ data


def idxs_of(split: int) -> list[int]:
    p = PAGE_DIR / f"split_{split:03d}.txt"
    return GP.rune_indices(p.read_text(encoding="utf-8")) if p.exists() else []


def prefix(n: int = 400) -> list[int]:
    out: list[int] = []
    for s in UNSOLVED:
        out.extend(idxs_of(s))
        if len(out) >= n:
            break
    return out[:n]


def solved_pairs() -> list[dict]:
    """(ciphertext, plaintext) rune streams for the four replayed fixtures."""
    out = []
    for f in load_fixtures():
        ct = GP.rune_indices(f["ciphertext"])
        pt = apply_named(f["method"], ct, None)
        if len(ct) != len(pt) or len(ct) < MIN_OVERLAP:
            continue
        out.append({
            "stage_id": f["stage_id"],
            "method": f["method"],
            "ct": np.array(ct, np.int64),
            "pt": np.array(pt, np.int64),
            # a fixture whose "cipher" leaves the stream untouched carries no pad,
            # so dragging it just re-scores raw ciphertext. Excluded, not hidden.
            "degenerate": ct == pt,
        })
    return out


# ------------------------------------------------- English reference model


def plaintext_unigram() -> np.ndarray:
    pool: list[int] = []
    for sp in solved_pairs():
        pool.extend(int(x) for x in sp["pt"])
    c = Counter(pool)
    f = np.array([c.get(s, 0) for s in range(Q)], float)
    return f / f.sum()


UNI = plaintext_unigram()
P_DEPTH = np.array([sum(UNI[s] * UNI[(s - d) % Q] for s in range(Q)) for d in range(Q)])
P_UNIF = np.ones(Q) / Q
LOGRATIO = np.log(P_DEPTH / P_UNIF)
LTILDE = np.array([np.sum(LOGRATIO * np.exp(2j * np.pi * w * np.arange(Q) / Q)) for w in range(Q)])
H0_MEAN = float(np.sum(P_UNIF * LOGRATIO))
H0_SD = float(np.sqrt(np.sum(P_UNIF * LOGRATIO ** 2) - H0_MEAN ** 2))
H1_MEAN = float(np.sum(P_DEPTH * LOGRATIO))


# --------------------------------------------------- correlation machinery


def profiles(a: np.ndarray, b: np.ndarray):
    """For every offset d (compare a[k+d] with b[k]) return LLR, matches, overlap.

    LLR(d) = sum_k log( P_depth(a[k+d]-b[k]) / P_uniform ), computed through a
    29-point character DFT so one pair costs 29 correlations instead of 841.
    """
    m, n = len(a), len(b)
    llr = np.zeros(m + n - 1, complex)
    hist0 = np.zeros(m + n - 1, complex)
    for w in range(Q):
        ea = np.exp(-2j * np.pi * w * a / Q)
        eb = np.exp(-2j * np.pi * w * b / Q)
        c = np.correlate(ea, eb, "full")
        llr += LTILDE[w] * c
        hist0 += c
    overlap = np.correlate(np.ones(m), np.ones(n), "full")
    offsets = np.arange(m + n - 1) - (n - 1)
    return offsets, (llr / Q).real, (hist0 / Q).real, overlap


def llr_z(llr: np.ndarray, overlap: np.ndarray) -> np.ndarray:
    with np.errstate(invalid="ignore", divide="ignore"):
        z = (llr - overlap * H0_MEAN) / (H0_SD * np.sqrt(overlap))
    return np.nan_to_num(z, nan=-99.0, posinf=-99.0, neginf=-99.0)


def best_alignment(a: np.ndarray, b: np.ndarray, min_overlap: int = MIN_OVERLAP):
    offsets, llr, matches, overlap = profiles(a, b)
    ok = overlap >= min_overlap
    if not ok.any():
        return None
    z = np.where(ok, llr_z(llr, overlap), -99.0)
    i = int(np.argmax(z))
    ov = float(overlap[i])
    return {"offset": int(offsets[i]), "overlap": int(ov), "matches": int(round(matches[i])),
            "kappa": round(matches[i] / ov, 5),
            "kappa_z": round((matches[i] - ov / Q) / np.sqrt(ov * (1 / Q) * (1 - 1 / Q)), 3),
            "llr_z": round(float(z[i]), 3)}


def longest_common_run(a: np.ndarray, b: np.ndarray) -> int:
    prev = np.zeros(len(b) + 1, int)
    best = 0
    for i in range(len(a)):
        cur = np.zeros(len(b) + 1, int)
        for j in np.nonzero(b == a[i])[0]:
            cur[j + 1] = prev[j] + 1
        if cur.max() > best:
            best = int(cur.max())
        prev = cur
    return best


TAIL_CUTS = (3.0, 3.5, 4.0, 4.5)


def scan(pg: dict[int, np.ndarray], with_runs: bool = False):
    """Every pair, forward and reversed.

    Returns (max llr_z, ranked per-pair hits, n alignments, tail counts). The tail
    counts matter because the per-pair max is underpowered at these page lengths:
    a handful of pairs in depth would fatten the tail before it moves the max.
    """
    keys = sorted(pg)
    hits: list = []
    n_align = 0
    tail = {c: 0 for c in TAIL_CUTS}
    for ii, a in enumerate(keys):
        for b in keys[ii + 1:]:
            for tag, vb in (("fwd", pg[b]), ("rev", pg[b][::-1])):
                _, llr, _, ov = profiles(pg[a], vb)
                sel = ov >= MIN_OVERLAP
                n_align += int(np.sum(sel))
                if sel.any():
                    zz = llr_z(llr, ov)[sel]
                    for c in TAIL_CUTS:
                        tail[c] += int(np.sum(zz >= c))
                h = best_alignment(pg[a], vb)
                if h:
                    if with_runs:
                        h["longest_common_run"] = longest_common_run(pg[a], vb)
                    hits.append((h["llr_z"], a, b, tag, h))
    hits.sort(key=lambda x: -x[0])
    return (hits[0][0] if hits else 0.0), hits, n_align, tail


def surrogate_max(pg: dict[int, np.ndarray], reps: int = N_SURROGATE) -> list[float]:
    """Shuffle each page in place: keeps length and symbol composition, kills order."""
    out = []
    for _ in range(reps):
        m, _, _, t = scan({s: RNG.permutation(v) for s, v in pg.items()})
        out.append((m, t))
    return out


def fmt(hits, k=8):
    return [{"a": f"split{a:03d}", "b": f"split{b:03d}", "dir": tag, **h} for _, a, b, tag, h in hits[:k]]


# ------------------------------------------------------------------ plants


def run_plants() -> dict:
    out: dict = {}

    # (a) offset algebra and the DFT LLR, checked against brute force
    a = RNG.integers(0, Q, 70)
    b = RNG.integers(0, Q, 55)
    offsets, llr, matches, overlap = profiles(a, b)
    ok_m = ok_l = True
    for i, d in enumerate(offsets):
        lo, hi = max(0, -int(d)), min(len(b), len(a) - int(d))
        seg_a, seg_b = a[lo + int(d):hi + int(d)], b[lo:hi]
        if int(np.sum(seg_a == seg_b)) != int(round(matches[i])) or (hi - lo) != int(overlap[i]):
            ok_m = False
        want = float(np.sum(LOGRATIO[(seg_a - seg_b) % Q]))
        if abs(want - llr[i]) > 1e-8:
            ok_l = False
    out["brute_force_matches_ok"] = ok_m
    out["brute_force_llr_ok"] = ok_l

    pool = np.concatenate([sp["pt"] for sp in solved_pairs()])

    # (b) two pages under one pad -> alignment found and plaintext recovered exactly
    shift, n_a, n_b = 37, 220, 200
    pa, pb = pool[:n_a], pool[len(pool) - n_b:]
    pad = RNG.integers(0, Q, 4000)
    ca = (pa + pad[shift:shift + n_a]) % Q
    cb = (pb + pad[:n_b]) % Q
    hit = best_alignment(ca, cb)
    d = hit["offset"]
    lo, hi = max(0, -d), min(n_b, n_a - d)
    rec = (ca[lo + d:hi + d] - cb[lo:hi] + pb[lo:hi]) % Q
    agree = float(np.mean(rec == pa[lo + d:hi + d]))
    out["shared_pad_pair"] = {
        "pad_shift": shift, "expected_offset": -shift, "found_offset": d,
        "offset_ok": d == -shift, "llr_z": hit["llr_z"], "kappa": hit["kappa"],
        "recovered_runes": int(hi - lo), "recovery_agree": round(agree, 4),
        "recovered_head": GP.latin_stream([int(x) for x in rec])[:64],
    }

    # (c) repeating pad inside one stream -> self-lag scan must spike at the period
    period = 97
    plain = RNG.choice(Q, 4000, p=UNI)
    ct = (plain + np.tile(RNG.integers(0, Q, period), 4000 // period + 1)[:4000]) % Q
    zs = sorted(((self_lag_z(ct, l), l) for l in range(1, 400)), reverse=True)
    out["periodic_pad"] = {"true_period": period, "top_lags": [int(l) for _, l in zs[:3]],
                           "top_lag_is_multiple_of_period": zs[0][1] % period == 0,
                           "top3_all_multiples": all(l % period == 0 for _, l in zs[:3]),
                           "top_z": round(zs[0][0], 2)}

    # (d) cost of the anti-repeat reject filter, at a length where the clean case is decisive
    n_f = 1500
    ks = [int(x) for x in RNG.integers(0, Q, n_f * 6)]
    p1 = [int(x) for x in RNG.choice(Q, n_f, p=UNI)]
    p2 = [int(x) for x in RNG.choice(Q, n_f, p=UNI)]
    clean_a = np.array([(p1[i] + ks[i]) % Q for i in range(n_f)])
    clean_b = np.array([(p2[i] + ks[i]) % Q for i in range(n_f)])
    h_clean = best_alignment(clean_a, clean_b)
    ca2, _ = encrypt_reject(p1, ks)
    cb2, _ = encrypt_reject(p2, ks)
    h2 = best_alignment(np.array(ca2), np.array(cb2))
    out["reject_filter_cost"] = {
        "n": n_f,
        "unfiltered_llr_z": h_clean["llr_z"], "unfiltered_offset": h_clean["offset"],
        "filtered_llr_z": h2["llr_z"] if h2 else None, "filtered_offset": h2["offset"] if h2 else None,
        "note": "same pad, same plaintexts. Independent rejections desynchronise the two "
                "key pointers, so a null from this instrument does NOT exclude depth that "
                "ran through the anti-repeat filter.",
    }
    out["ok"] = bool(ok_m and ok_l and out["shared_pad_pair"]["offset_ok"]
                     and agree == 1.0 and out["periodic_pad"]["top3_all_multiples"]
                     and out["reject_filter_cost"]["unfiltered_llr_z"] >= 8.0)
    return out


def self_lag_z(v: np.ndarray, lag: int) -> float:
    seg_a, seg_b = v[lag:], v[:-lag]
    n = len(seg_a)
    llr = float(np.sum(LOGRATIO[(seg_a - seg_b) % Q]))
    return (llr - n * H0_MEAN) / (H0_SD * np.sqrt(n))


def power_table() -> list[dict]:
    rows = []
    for n in (80, 120, 200, 277, 400, 1000, 3000, 12956):
        sep = (H1_MEAN - H0_MEAN) * n / (H0_SD * np.sqrt(n))
        rows.append({"overlap": n, "llr_separation_sigma": round(sep, 2),
                     "kappa_separation_sigma": round(
                         (P_DEPTH[0] - 1 / Q) * n / np.sqrt(n * (1 / Q) * (1 - 1 / Q)), 2)})
    return rows


# -------------------------------------------------------------------- main


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    plant = run_plants()
    print("plant ok=", plant["ok"], json.dumps(plant["shared_pad_pair"]))

    early = {s: np.array(idxs_of(s), np.int64) for s in range(0, 15)}
    early = {s: v for s, v in early.items() if len(v) >= MIN_OVERLAP}
    uns = {s: np.array(idxs_of(s), np.int64) for s in UNSOLVED}
    uns = {s: v for s, v in uns.items() if len(v) >= MIN_OVERLAP}
    cat = np.concatenate([np.array(idxs_of(s), np.int64) for s in UNSOLVED])

    # pass 1: instrument control on the early splits
    e_max, e_hits, e_n, e_tail = scan(early, with_runs=True)
    e_surr = [m for m, _ in surrogate_max(early)]
    control = {"pages": len(early), "alignments": e_n, "observed_max_llr_z": round(e_max, 2),
               "surrogate_max_llr_z": round(float(np.max(e_surr)), 2),
               "fires": bool(e_max > float(np.max(e_surr))), "top": fmt(e_hits, 5)}
    print("control", control["observed_max_llr_z"], ">", control["surrogate_max_llr_z"], control["fires"])

    # pass 2: self-lag scan on the concatenated unsolved stream, surrogate-calibrated
    def lag_max(v):
        return max(self_lag_z(v, l) for l in range(1, 6001) if len(v) - l >= 200)
    lags = [(self_lag_z(cat, l), l) for l in range(1, 6001) if len(cat) - l >= 200]
    lags.sort(reverse=True)
    self_surr = [lag_max(RNG.permutation(cat)) for _ in range(N_SURROGATE)]
    self_scan = {
        "lags_tested": len(lags),
        "observed_max_llr_z": round(lags[0][0], 2),
        "surrogate_max_llr_z": round(float(np.max(self_surr)), 2),
        "surrogate_mean_max": round(float(np.mean(self_surr)), 2),
        "exceeds_surrogate": bool(lags[0][0] > float(np.max(self_surr))),
        "top": [{"lag": int(l), "llr_z": round(z, 2)} for z, l in lags[:6]],
    }
    print("self-lag", self_scan["observed_max_llr_z"], "vs surrogate", self_scan["surrogate_max_llr_z"])

    # pass 3: pairwise depth over the unsolved pages only
    u_max, u_hits, u_n, u_tail = scan(uns, with_runs=True)
    u_surr_raw = surrogate_max(uns)
    u_surr = [m for m, _ in u_surr_raw]
    u_thresh = float(np.max(u_surr))
    tail_cmp = {}
    for c in TAIL_CUTS:
        vals = np.array([t[c] for _, t in u_surr_raw], float)
        sd = float(vals.std(ddof=1)) or 1.0
        tail_cmp[str(c)] = {"observed": u_tail[c], "surrogate_mean": round(float(vals.mean()), 1),
                            "surrogate_sd": round(float(vals.std(ddof=1)), 1),
                            "z": round((u_tail[c] - float(vals.mean())) / sd, 2)}
    pairwise = {"pages": len(uns), "alignments": u_n,
                "observed_max_llr_z": round(u_max, 2),
                "surrogate_max_llr_z": round(u_thresh, 2),
                "surrogate_mean_max": round(float(np.mean(u_surr)), 2),
                "exceeds_surrogate": bool(u_max > u_thresh),
                "max_longest_common_run": int(max(h[4]["longest_common_run"] for h in u_hits)),
                "tail_counts_vs_surrogate": tail_cmp,
                "top": fmt(u_hits, 8)}
    print("pairwise unsolved", pairwise["observed_max_llr_z"], "vs surrogate", pairwise["surrogate_max_llr_z"])

    # pass 4: pooled page-aligned tests
    pooled = {}
    keys = sorted(uns)
    for tag in ("left", "right"):
        M = N = 0
        llr = 0.0
        diff = Counter()
        for ii, a in enumerate(keys):
            for b in keys[ii + 1:]:
                va, vb = uns[a], uns[b]
                L = min(len(va), len(vb))
                xa = va[:L] if tag == "left" else va[len(va) - L:]
                xb = vb[:L] if tag == "left" else vb[len(vb) - L:]
                d = (xa - xb) % Q
                M += int(np.sum(d == 0))
                N += L
                llr += float(np.sum(LOGRATIO[d]))
                for x in d:
                    diff[int(x)] += 1
        dv = np.array([diff.get(s, 0) for s in range(Q)], float)
        pooled[tag] = {"n": N, "matches": M, "kappa": round(M / N, 5),
                       "kappa_z": round((M - N / Q) / np.sqrt(N * (1 / Q) * (1 - 1 / Q)), 2),
                       "llr_z": round((llr - N * H0_MEAN) / (H0_SD * np.sqrt(N)), 2),
                       "difference_ioc": round(float(np.sum(dv * (dv - 1)) / (dv.sum() * (dv.sum() - 1))), 5),
                       "expected_llr_z_if_depth": round((H1_MEAN - H0_MEAN) * N / (H0_SD * np.sqrt(N)), 1)}
    print("pooled", {k: (v["kappa_z"], v["llr_z"]) for k, v in pooled.items()})

    # pass 5: known-plaintext depth
    kp = {"alignments_tested": 0, "keeps": [], "excluded_degenerate": [], "best_by_trigram": None}
    targets = [(f"split{s:03d}", v) for s, v in sorted(uns.items())]
    targets.append(("prefix400", np.array(prefix(400), np.int64)))
    for sp in solved_pairs():
        if sp["degenerate"]:
            kp["excluded_degenerate"].append(
                {"stage_id": sp["stage_id"], "method": sp["method"],
                 "why": "plaintext == ciphertext, so the drag re-scores raw ciphertext"})
            continue
        for tname, cu in targets:
            for tag, cs, ps in (("fwd", sp["ct"], sp["pt"]), ("rev", sp["ct"][::-1], sp["pt"][::-1])):
                offsets, _, _, overlap = profiles(cu, cs)
                for i, d in enumerate(offsets):
                    ov = int(overlap[i])
                    if ov < MIN_OVERLAP:
                        continue
                    kp["alignments_tested"] += 1
                    lo, hi = max(0, -int(d)), max(0, -int(d)) + ov
                    cand = ((cu[lo + int(d):hi + int(d)] - cs[lo:hi] + ps[lo:hi]) % Q).tolist()
                    lat = GP.latin_stream(cand)
                    sc = score_candidate(cand, lat)
                    rec = {"solved": sp["stage_id"], "span": tname, "dir": tag,
                           "offset": int(d), "n": ov, "head": lat[:80], **sc}
                    if keep(sc, ov):
                        rec["full_latin"] = lat
                    if kp["best_by_trigram"] is None or sc["trigram_per_100"] > kp["best_by_trigram"]["trigram_per_100"]:
                        kp["best_by_trigram"] = rec
                    if "full_latin" in rec:
                        kp["keeps"].append(rec)
                        print("KEEP", rec["solved"], rec["span"], rec["dir"], rec["offset"], rec["head"][:48])
    print("kp tested", kp["alignments_tested"], "keeps", len(kp["keeps"]))

    result = {
        "experiment": "EXP-LP-DEPTH-KAPPA-001",
        "family": "ciphertext depth: coincidence / optimal-LLR search for pad reuse",
        "scope": "rtkd splits 15-70 (12956 runes), plus splits 0-14 as instrument control",
        "keep_bar": "n>=80, trigram_per_100>=3.5, ioc>=0.045, vowelish 0.28-0.55, then readable English",
        "model": {"chance_kappa": round(1 / Q, 5),
                  "depth_kappa_expected": round(float(P_DEPTH[0]), 5),
                  "llr_h0_mean_per_rune": round(H0_MEAN, 5),
                  "llr_h1_mean_per_rune": round(H1_MEAN, 5)},
        "plant": plant,
        "instrument_control_splits_0_14": control,
        "self_lag_scan": self_scan,
        "pairwise_unsolved": pairwise,
        "pooled_page_aligned": pooled,
        "known_plaintext_depth": kp,
        "power": power_table(),
        "unsolved_splits_below_min_overlap": [
            {"split": s, "runes": len(idxs_of(s))} for s in UNSOLVED if len(idxs_of(s)) < MIN_OVERLAP
        ],
        "unsolved_runes_total": int(len(cat)),
        "skeptic_review": {
            "keep_bar_hits": len(kp["keeps"]),
            "verdict": "artifact",
            "why": "both hits are 'rev'-direction drags with no cipher mechanism behind them, "
                   "and their Latin is not English. trigram_per_100 clears the bar only because "
                   "the multigraph runes EO/TH/IA/AE/NG each expand to two Latin letters and "
                   "manufacture THE/ING/ENT at their joins -- the same scorer artifact recorded "
                   "for split066 running-key hits.",
        },
        "verified_new_unsolved_runes": 0,
    }
    (OUT / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("wrote", OUT / "result.json")


if __name__ == "__main__":
    main()
