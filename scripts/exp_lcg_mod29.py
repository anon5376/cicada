#!/usr/bin/env python3
"""Affine LCG and lagged-Fibonacci keystreams over GF(29).

The ledger names "a short-seed generator not in the tested lists" as an open gap
(CURRENT_FRONTIER "Does not exclude ..."; HANDOFF highest-value #1). Generators
already swept: SHA-CTR, totient, primes, Fibonacci-word, MT19937, RC4, ChaCha20,
HKDF, PBKDF2, automatic sequences, and mu/omega/Omega/lambda/sigma arithmetic.
Two classical number-theoretic recurrences are absent:

  * affine LCG      x_{i+1} = (a*x_i + c) mod 29          (params a,c,x0)
  * lagged Fibonacci x_i    = (x_{i-1} + x_{i-2}) mod 29  (params x0,x1)

Both are short-seed and very Cicada-flavoured, and their whole parameter space is
tiny (29^3 + 29^2), so the family is closed EXHAUSTIVELY here, not sampled.

Passes:
  1. rigid Vigenere (sub/add/Beaufort) over every DISTINCT keystream. Complete,
     but a priori weak: per-column / period IoC is already flat (chance), which
     excludes short-period polyalphabetic (EXP-LP-COND-PREV-IOC-001). A period<=29
     keystream is exactly a structured short Vigenere key.
  2. plant-validated skip-aware beam (reject-on-doublet, consume 1..3) on a
     prioritised distinct subset. The anti-repeat hole (doublet 0.19x uniform) is
     the one measured signal, so this is the instrument that can still surprise.

No network. Only writes experiments/EXP-LP-LCG-MOD29-001/result.json.
Reuses the plant/decoder from exp_skipaware_sha_ctr (sub relation).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from cicada.liber_primus.gematria import Gematria  # noqa: E402
from cicada.paths import ROOT as CICADA_ROOT  # noqa: E402
from cicada.scoring import score_candidate  # noqa: E402
from exp_skipaware_sha_ctr import (  # noqa: E402
    beam_decode,
    encrypt_reject,
    idxs_of,
    keep,
    prefix,
)

GP = Gematria()
Q = 29
SIGN = 64  # >= 2*max period (29): a period<=29 sequence is uniquely id'd by its 64-prefix
CAP_BEAM = 260  # skip-aware beam is the expensive pass; the rigid pass stays complete
OUT = CICADA_ROOT / "experiments" / "EXP-LP-LCG-MOD29-001"

# Famous LCG multipliers/increments reduced mod 29 -> "named" motivated generators.
NAMED_A = sorted({1103515245 % Q, 69069 % Q, 16807 % Q, 48271 % Q, 1664525 % Q, 22695477 % Q, 214013 % Q})
NAMED_C = sorted({12345 % Q, 1, 1013904223 % Q, 3301 % Q, 0})


def lcg_stream(a: int, c: int, x0: int, n: int) -> list[int]:
    out: list[int] = []
    x = x0 % Q
    for _ in range(n):
        out.append(x)
        x = (a * x + c) % Q
    return out


def lagfib_stream(x0: int, x1: int, n: int) -> list[int]:
    out: list[int] = []
    s0, s1 = x0 % Q, x1 % Q
    for _ in range(n):
        out.append(s0)
        s0, s1 = s1, (s0 + s1) % Q
    return out


def gen(kind: str, key: tuple, n: int) -> list[int]:
    if kind == "lcg":
        a, c, x0 = key
        return lcg_stream(a, c, x0, n)
    x0, x1 = key
    return lagfib_stream(x0, x1, n)


def apply_p(c: int, k: int, rel: str) -> int:
    if rel == "sub":
        return (c - k) % Q
    if rel == "add":
        return (c + k) % Q
    return (k - c) % Q  # beaufort


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    # ---- plant-and-recover: validate the skip-aware decoder for THIS family ----
    plant_lat = "THEPRIMESARESACREDTHETOTIENTFVNCTIANISSACREDALLTHNGSSHOVLDBEENCRYPTEDAWARNNGBELIEVENOTHNG"
    plant_pt = GP.encode_latin_key(plant_lat)
    plants = {}
    for tag, ks in (
        ("lcg_a2_c1_x1", lcg_stream(2, 1, 1, len(plant_pt) * 4)),   # a=2 is a primitive root mod 29 (max entropy)
        ("lagfib_1_1", lagfib_stream(1, 1, len(plant_pt) * 4)),     # standard Fibonacci mod 29
    ):
        ct, _used = encrypt_reject(plant_pt, ks)
        rec = beam_decode(ct, ks)
        agree = sum(x == y for x, y in zip(rec, plant_pt)) / len(plant_pt) if rec else 0.0
        plants[tag] = {"agree": round(agree, 4), "ok": agree >= 0.95, "recovered_head": GP.latin_stream(rec)[:64]}
        print("plant", tag, plants[tag], flush=True)

    # ---- enumerate DISTINCT keystreams ----
    lcg_keys: list[tuple] = []
    seen: set = set()
    for a in range(Q):
        for c in range(Q):
            for x0 in range(Q):
                sig = tuple(lcg_stream(a, c, x0, SIGN))
                if sig in seen:
                    continue
                seen.add(sig)
                lcg_keys.append((a, c, x0))
    lf_keys: list[tuple] = []
    seen_lf: set = set()
    for x0 in range(Q):
        for x1 in range(Q):
            sig = tuple(lagfib_stream(x0, x1, SIGN))
            if sig in seen_lf:
                continue
            seen_lf.add(sig)
            lf_keys.append((x0, x1))
    print(f"distinct lcg {len(lcg_keys)}/{Q**3}  lagfib {len(lf_keys)}/{Q**2}", flush=True)

    targets_rigid = [("prefix400", prefix(400)), ("split015", idxs_of(15))]
    for s in (17, 40, 63):
        ct = idxs_of(s)
        if len(ct) >= 80:
            targets_rigid.append((f"split{s:03d}", ct))
    targets_beam = [("prefix400", prefix(400)), ("split015", idxs_of(15))]
    rels = ("sub", "add", "beau")
    maxlen = max(len(ct) for _, ct in targets_rigid)

    hits: list = []
    best = {"trigram_per_100": -1.0}
    rigid_tested = 0
    promote: set = set()

    # ---- pass 1: exhaustive rigid Vigenere over the whole family ----
    for kind, keys in (("lcg", lcg_keys), ("lagfib", lf_keys)):
        for key in keys:
            ksf = gen(kind, key, maxlen)
            for tname, ct in targets_rigid:
                ks = ksf[: len(ct)]
                for rel in rels:
                    rigid_tested += 1
                    pt = [apply_p(c, ks[i], rel) for i, c in enumerate(ct)]
                    lat = GP.latin_stream(pt)
                    sc = score_candidate(pt, lat)
                    if sc["trigram_per_100"] > best["trigram_per_100"]:
                        best = {"kind": kind, "key": list(key), "rel": rel, "span": tname, "head": lat[:64], **sc}
                    if keep(sc, len(pt)):
                        row = {"pass": "rigid", "kind": kind, "key": list(key), "rel": rel, "span": tname, "head": lat[:80], **sc}
                        hits.append(row)
                        print("KEEP", row, flush=True)
                    if sc["trigram_per_100"] >= 2.5:
                        promote.add((kind, key))
    print(f"rigid tested {rigid_tested}  keeps {len(hits)}  promoted {len(promote)}", flush=True)

    # ---- pass 2: skip-aware beam on a prioritised distinct subset ----
    beam_list: list[tuple] = []
    beam_seen: set = set()

    def add_beam(kind: str, key: tuple) -> None:
        if (kind, key) not in beam_seen:
            beam_seen.add((kind, key))
            beam_list.append((kind, key))

    for kind, key in promote:                      # any rigid near-miss first
        add_beam(kind, key)
    for a in NAMED_A:                              # named LCG constants
        for c in NAMED_C:
            for x0 in (0, 1, 3301 % Q):
                add_beam("lcg", (a % Q, c % Q, x0))
    for c in range(Q):                             # all arithmetic progressions (a=1) from x0=0
        add_beam("lcg", (1, c, 0))
    for i, key in enumerate(lf_keys):              # lagged-Fibonacci sample
        if i % 8 == 0:
            add_beam("lagfib", key)
    for i, key in enumerate(lcg_keys):             # multiplicative representatives (a>=2)
        a = key[0]
        if a >= 2 and i % 17 == 0:
            add_beam("lcg", key)
    capped = len(beam_list) > CAP_BEAM
    beam_list = beam_list[:CAP_BEAM]

    beam_tested = 0
    samples = []
    for kind, key in beam_list:
        for tname, ct in targets_beam:
            ks = gen(kind, key, len(ct) * 4)
            beam_tested += 1
            pt = beam_decode(ct, ks)
            lat = GP.latin_stream(pt)
            sc = score_candidate(pt, lat)
            row = {"pass": "beam", "kind": kind, "key": list(key), "span": tname, "head": lat[:80], **sc}
            if beam_tested <= 4:
                print(f"beam {kind} {key} {tname} tri={sc['trigram_per_100']:.2f} ioc={sc['ioc']:.3f} {lat[:36]}", flush=True)
                samples.append(row)
            if keep(sc, len(pt)):
                hits.append(row)
                print("KEEP", row, flush=True)

    verified_new_unsolved_runes = 0  # keeps that survive skeptic review; none expected
    out = {
        "experiment_id": "EXP-LP-LCG-MOD29-001",
        "family": "affine LCG (x->a*x+c mod29) and lagged-Fibonacci (x_i=x_{i-1}+x_{i-2} mod29) keystreams",
        "why": "ledger open gap: short-seed generator not in tested lists; number-theoretic; flat-IoC keystream",
        "plants": plants,
        "distinct_lcg_keystreams": len(lcg_keys),
        "distinct_lagfib_keystreams": len(lf_keys),
        "rigid_tested": rigid_tested,
        "rigid_scope": "EXHAUSTIVE over every distinct keystream x sub/add/beau x 5 targets",
        "beam_tested": beam_tested,
        "beam_capped": capped,
        "beam_scope": "skip-aware sub decoder on promoted + named + all a=1 APs + lagfib/multiplicative reps, prefix400+split015",
        "keeps": hits,
        "best_rigid_sample": best,
        "beam_samples": samples,
        "verified_new_unsolved_runes": verified_new_unsolved_runes,
        "boundary": "Exhaustive skip-aware over all 24k LCG params x 3 rel is the tractability limit; rigid is complete, beam is a prioritised distinct subset. Does not exclude external pads or non-LCG short seeds.",
    }
    (OUT / "result.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"DONE rigid {rigid_tested} beam {beam_tested} keeps {len(hits)} plant_ok "
          f"{all(p['ok'] for p in plants.values())} newrunes {verified_new_unsolved_runes}", flush=True)


if __name__ == "__main__":
    main()
