#!/usr/bin/env python3
"""Marked-seed xorshift / xoroshiro / PCG / Galois-LFSR keystreams.

LCG and lagged-Fibonacci mod 29 are closed exhaustively (tiny state).
MT19937 marked seeds are closed. This is the remaining common short-seed
binary PRNG family: 32-bit xorshift (Marsaglia triples), xoroshiro64**,
PCG-XSH-RR, and a 32-bit Galois LFSR. State space is 2^32 so this is not
exhaustive — only puzzle-attested integer seeds, as MT19937 was.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from cicada.liber_primus.gematria import Gematria  # noqa: E402
from cicada.paths import ROOT as CICADA_ROOT  # noqa: E402
from cicada.scoring import score_candidate  # noqa: E402
from exp_skipaware_sha_ctr import beam_decode, encrypt_reject, idxs_of, keep, prefix  # noqa: E402

GP = Gematria()
Q = 29
MASK32 = 0xFFFFFFFF
MASK64 = 0xFFFFFFFFFFFFFFFF
OUT = CICADA_ROOT / "experiments" / "EXP-LP-XORSHIFT-PCG-001"

# Marsaglia 2003 Table 3 triples for 32-bit xorshift (a,b,c) = (shift-left, shift-right, shift-left)
XS32_TRIPLES = ((13, 17, 5), (5, 14, 1), (9, 7, 13), (7, 1, 9))


def _nz32(s: int) -> int:
    return (s & MASK32) or 1


def xorshift32(seed: int, n: int, a: int = 13, b: int = 17, c: int = 5) -> list[int]:
    y = _nz32(seed)
    out: list[int] = []
    for _ in range(n):
        y ^= (y << a) & MASK32
        y ^= y >> b
        y ^= (y << c) & MASK32
        y &= MASK32
        out.append(y % Q)
    return out


def _rotl32(x: int, k: int) -> int:
    x &= MASK32
    return ((x << k) | (x >> (32 - k))) & MASK32


def xoroshiro64ss(seed: int, n: int) -> list[int]:
    """xoroshiro64** with s0=seed, s1=seed*0x9E3779B9 (Blackman/Vigna)."""
    s0 = _nz32(seed)
    s1 = _nz32(seed * 0x9E3779B9)
    out: list[int] = []
    for _ in range(n):
        result = (_rotl32((s0 * 0x9E3779BB) & MASK32, 5) * 5) & MASK32
        out.append(result % Q)
        s1 ^= s0
        s0 = (_rotl32(s0, 26) ^ s1 ^ ((s1 << 9) & MASK32)) & MASK32
        s1 = _rotl32(s1, 13)
    return out


def pcg32(seed: int, n: int) -> list[int]:
    """PCG-XSH-RR with 64-bit state, increment 1442695040888963407."""
    state = (seed & MASK64) or 1
    if state < 2:
        state = 0x853C49E6748FEA9B  # PCG default init if tiny
        if seed:
            state = seed & MASK64
    inc = 1442695040888963407
    out: list[int] = []
    for _ in range(n):
        old = state
        state = (old * 6364136223846793005 + inc) & MASK64
        xorshifted = (((old >> 18) ^ old) >> 27) & MASK32
        rot = (old >> 59) & 31
        val = ((xorshifted >> rot) | ((xorshifted << ((-rot) & 31)) & MASK32)) & MASK32
        out.append(val % Q)
    return out


def galois32(seed: int, n: int, poly: int = 0x80200003) -> list[int]:
    s = _nz32(seed)
    out: list[int] = []
    for _ in range(n):
        lsb = s & 1
        s >>= 1
        if lsb:
            s ^= poly
        s &= MASK32
        if s == 0:
            s = 1
        out.append(s % Q)
    return out


def generators() -> list[tuple[str, callable]]:
    gens = [
        ("xoroshiro64ss", xoroshiro64ss),
        ("pcg32", pcg32),
        ("galois32", galois32),
    ]
    for a, b, c in XS32_TRIPLES:
        gens.append((f"xs32_{a}_{b}_{c}", lambda n, seed, a=a, b=b, c=c: xorshift32(seed, n, a, b, c)))
    return gens


def marked_seeds() -> list[tuple[str, int]]:
    out: list[tuple[str, int]] = []
    for n in (
        1, 15, 56, 57, 3301, 2012, 2013, 2014, 2017, 1295, 1033,
        0x7A35090F, 0x57A35090, 0x6D854CD7, 0x181F01E5, 0x845145127 & MASK32,
    ):
        out.append((f"int:{n}", n & MASK32))
    for word in (b"CICADA3301", b"3301", b"DIVINITY", b"AN END", b"LIBERPRIMUS", b"TOTIENT"):
        h = hashlib.sha256(word).digest()
        out.append((f"sha32:{word.decode()}", int.from_bytes(h[:4], "big")))
    seen = set()
    uniq = []
    for label, seed in out:
        if seed in seen or seed == 0:
            continue
        seen.add(seed)
        uniq.append((label, seed))
    return uniq


def apply_p(c: int, k: int, rel: str) -> int:
    if rel == "sub":
        return (c - k) % Q
    if rel == "add":
        return (c + k) % Q
    return (k - c) % Q


def rigid(ct: list[int], ks: list[int], rel: str) -> list[int]:
    return [apply_p(c, ks[i], rel) for i, c in enumerate(ct)]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    plant_pt = GP.encode_latin_key(
        "THEPRIMESARESACREDTHETOTIENTFVNCTIANISSACREDALLTHNGSSHOVLDBEENCRYPTEDAWARNNGBELIEVENOTHNG"
    )
    plants = {}
    for name, gen in generators():
        # gen signatures: xoroshiro/pcg/galois are (seed, n); xs32 lambda is (n, seed=...)
        def ks_of(gname: str, g, seed: int, n: int) -> list[int]:
            if gname.startswith("xs32_"):
                return g(n, seed=seed)
            return g(seed, n)

        pks = ks_of(name, gen, 3301, len(plant_pt) * 4)
        rec = rigid( [(p + pks[i]) % Q for i, p in enumerate(plant_pt)], pks, "sub")
        plants[f"{name}_rigid"] = rec == plant_pt
        ct, _ = encrypt_reject(plant_pt, pks)
        recb = beam_decode(ct, pks)
        agree = sum(a == b for a, b in zip(recb, plant_pt)) / len(plant_pt) if recb else 0.0
        plants[f"{name}_beam"] = {"agree": round(agree, 4), "ok": agree >= 0.89}
    plants["ok"] = all(
        (v is True) or (isinstance(v, dict) and v.get("ok")) for k, v in plants.items() if k != "ok"
    )
    print("plant", plants, flush=True)
    if not plants["ok"]:
        (OUT / "result.json").write_text(json.dumps({
            "experiment": "EXP-LP-XORSHIFT-PCG-001", "plant": plants,
            "verified_new_unsolved_runes": 0, "aborted": "plant failed",
        }, indent=2) + "\n")
        return

    gens = generators()
    seeds = marked_seeds()
    targets_beam = [("prefix400", prefix(400)), ("split015", idxs_of(15))]
    pages = [(f"split{s:03d}", idxs_of(s)) for s in range(15, 71) if len(idxs_of(s)) >= 80]

    def ks_of(gname: str, g, seed: int, n: int) -> list[int]:
        if gname.startswith("xs32_"):
            return g(n, seed=seed)
        return g(seed, n)

    hits, tested_r, tested_b, best = [], 0, 0, None
    # rigid: all gens × marked seeds × n>=80 pages × 3 rels — too many if we
    # also do every xs32 triple. Cap rigid to prefix400 + split015/017/040/063
    # plus all pages for the primary xorshift32(13,17,5) + xoroshiro + pcg.
    rigid_targets = [("prefix400", prefix(400))] + [
        (n, t) for n, t in pages if n in ("split015", "split017", "split040", "split063")
    ]
    primary = [g for g in gens if g[0] in ("xoroshiro64ss", "pcg32", "galois32", "xs32_13_17_5")]
    for gname, gen in primary:
        for slabel, seed in seeds:
            for tname, ct in rigid_targets:
                ks = ks_of(gname, gen, seed, len(ct))
                for rel in ("sub", "add", "beau"):
                    tested_r += 1
                    rec = rigid(ct, ks, rel)
                    lat = GP.latin_stream(rec)
                    sc = score_candidate(rec, lat)
                    row = {"pass": "rigid", "gen": gname, "seed": slabel, "span": tname,
                           "rel": rel, "head": lat[:80], **sc, "n": len(rec)}
                    if best is None or sc["trigram_per_100"] > best["trigram_per_100"]:
                        best = row
                    if keep(sc, len(rec)):
                        hits.append(row)
                        print("KEEP", row["pass"], gname, slabel, tname, rel,
                              sc["trigram_per_100"], lat[:40], flush=True)

    # skip-aware beam: primary gens × seeds × prefix400 + split015
    for gname, gen in primary:
        for slabel, seed in seeds:
            for tname, ct in targets_beam:
                tested_b += 1
                ks = ks_of(gname, gen, seed, len(ct) * 4)
                rec = beam_decode(ct, ks)
                lat = GP.latin_stream(rec)
                sc = score_candidate(rec, lat)
                row = {"pass": "beam", "gen": gname, "seed": slabel, "span": tname,
                       "rel": "sub", "head": lat[:80], **sc, "n": len(rec)}
                if best is None or sc["trigram_per_100"] > best["trigram_per_100"]:
                    best = row
                if keep(sc, len(rec)):
                    hits.append(row)
                    print("KEEP", row["pass"], gname, slabel, tname,
                          sc["trigram_per_100"], lat[:40], flush=True)

    result = {
        "experiment": "EXP-LP-XORSHIFT-PCG-001",
        "family": "marked-seed xorshift32 / xoroshiro64** / PCG-XSH-RR / Galois LFSR",
        "plant": plants,
        "n_seeds": len(seeds),
        "n_gens_primary": [g[0] for g in primary],
        "tested_rigid": tested_r,
        "tested_beam": tested_b,
        "tested": tested_r + tested_b,
        "keep_bar_hits": len(hits),
        "keeps": hits[:20],
        "best": {k: best[k] for k in ("pass", "gen", "seed", "span", "rel", "head", "trigram_per_100", "ioc")} if best else None,
        "skeptic_review": {"verdict": "null" if not hits else "keep-bar needs human English"},
        "verified_new_unsolved_runes": 0,
        "boundary": "not exhaustive over 2^32 seeds; not other output maps (high bits)",
    }
    (OUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print("tested_rigid", tested_r, "tested_beam", tested_b, "keeps", len(hits),
          "best", None if not best else (best["trigram_per_100"], best["gen"], best["head"][:40]))


if __name__ == "__main__":
    main()
