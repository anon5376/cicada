#!/usr/bin/env python3
"""SPECK-64/128 + SIMON-64/128 CTR and xoroshiro128** marked-seed keystreams.

AES-CTR / ChaCha / xoshiro256** / xoroshiro64** are closed. These are the
unused NSA ARX siblings and the unused 128-bit xoroshiro ** scramble.
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
MASK64 = (1 << 64) - 1
OUT = CICADA_ROOT / "experiments" / "EXP-LP-SPECK-SIMON-001"


def _rol32(x: int, r: int) -> int:
    x &= MASK32
    return ((x << r) | (x >> (32 - r))) & MASK32


def _ror32(x: int, r: int) -> int:
    x &= MASK32
    return ((x >> r) | (x << (32 - r))) & MASK32


def _rol64(x: int, r: int) -> int:
    x &= MASK64
    return ((x << r) | (x >> (64 - r))) & MASK64


def speck_ks(key: bytes) -> list[int]:
    """SPECK-64/128 key schedule: 4 × 32-bit words, 27 rounds."""
    k = [int.from_bytes(key[i : i + 4], "little") for i in range(0, 16, 4)]
    l = [k[1], k[2], k[3]]
    rk = [k[0]]
    for i in range(26):
        l[i % 3] = (_ror32(l[i % 3], 8) + rk[i]) & MASK32 ^ i
        rk.append(_rol32(rk[i], 3) ^ l[i % 3])
    return rk


def speck_enc(pt: int, rk: list[int]) -> int:
    y = pt & MASK32
    x = (pt >> 32) & MASK32
    for k in rk:
        x = (_ror32(x, 8) + y) & MASK32 ^ k
        y = _rol32(y, 3) ^ x
    return ((x << 32) | y) & ((1 << 64) - 1)


def simon_ks(key: bytes) -> list[int]:
    """SIMON-64/128 key schedule: 4 × 32-bit words, 44 rounds."""
    k = [int.from_bytes(key[i : i + 4], "little") for i in range(0, 16, 4)]
    c = 0xFFFFFFFC
    z = 0xFD9CE8A6  # z2 for SIMON-64/128 (first 62 bits used)
    for i in range(4, 44):
        tmp = _ror32(k[i - 1], 3) ^ k[i - 3]
        tmp ^= _ror32(tmp, 1)
        bit = (z >> ((i - 4) % 62)) & 1
        k.append((c ^ bit ^ tmp ^ k[i - 4]) & MASK32)
    return k


def simon_enc(pt: int, rk: list[int]) -> int:
    y = pt & MASK32
    x = (pt >> 32) & MASK32
    for k in rk:
        tmp = x
        x = y ^ (_rol32(tmp, 1) & _rol32(tmp, 8)) ^ _rol32(tmp, 2) ^ k
        y = tmp
    return ((x << 32) | y) & ((1 << 64) - 1)


def block_ctr(enc_fn, rk, n: int, hi5: bool = False) -> list[int]:
    out: list[int] = []
    ctr = 0
    while len(out) < n:
        block = enc_fn(ctr, rk)
        raw = block.to_bytes(8, "little")
        for b in raw:
            out.append((b >> 3) % Q if hi5 else b % Q)
            if len(out) >= n:
                break
        ctr += 1
    return out


def key_from_seed(seed: int) -> bytes:
    return hashlib.sha256(seed.to_bytes(8, "big")).digest()[:16]


def speck_stream(seed: int, n: int, hi5: bool = False) -> list[int]:
    return block_ctr(speck_enc, speck_ks(key_from_seed(seed)), n, hi5)


def simon_stream(seed: int, n: int, hi5: bool = False) -> list[int]:
    return block_ctr(simon_enc, simon_ks(key_from_seed(seed)), n, hi5)


def xoroshiro128ss(seed: int, n: int, hi5: bool = False) -> list[int]:
    h = hashlib.sha256(seed.to_bytes(8, "big")).digest()
    s0 = int.from_bytes(h[:8], "little") or 1
    s1 = int.from_bytes(h[8:16], "little") or 2
    out: list[int] = []
    while len(out) < n:
        r = (_rol64(s0 * 5, 7) * 9) & MASK64
        raw = r.to_bytes(8, "little")
        for b in raw:
            out.append((b >> 3) % Q if hi5 else b % Q)
            if len(out) >= n:
                break
        s1 ^= s0
        s0 = (_rol64(s0, 24) ^ s1 ^ ((s1 << 16) & MASK64)) & MASK64
        s1 = _rol64(s1, 37)
    return out


def marked_seeds():
    out = []
    for n in (
        1, 15, 56, 57, 3301, 2012, 2013, 2014, 2017, 1295, 1033,
        0x7A35090F, 0x57A35090, 0x6D854CD7, 0x181F01E5, 0x845145127 & MASK32,
    ):
        out.append((f"int:{n}", n & MASK32))
    for word in (b"CICADA3301", b"3301", b"DIVINITY", b"AN END", b"LIBERPRIMUS", b"TOTIENT"):
        h = hashlib.sha256(word).digest()
        out.append((f"sha32:{word.decode()}", int.from_bytes(h[:4], "big")))
    seen, uniq = set(), []
    for label, seed in out:
        if seed in seen or seed == 0:
            continue
        seen.add(seed)
        uniq.append((label, seed))
    return uniq


def apply_p(c, k, rel):
    if rel == "sub":
        return (c - k) % Q
    if rel == "add":
        return (c + k) % Q
    return (k - c) % Q


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    pt = GP.encode_latin_key(
        "THEPRIMESARESACREDTHETOTIENTFVNCTIANISSACREDALLTHNGSSHOVLDBEENCRYPTEDAWARNNGBELIEVENOTHNG"
    )
    gens = [
        ("speck64_128", lambda s, n: speck_stream(s, n, False)),
        ("simon64_128", lambda s, n: simon_stream(s, n, False)),
        ("xoroshiro128ss", lambda s, n: xoroshiro128ss(s, n, False)),
        ("speck_hi5", lambda s, n: speck_stream(s, n, True)),
    ]
    plants = {}
    a = speck_stream(3301, 16)
    plants["det"] = a == speck_stream(3301, 16)
    plants["ne_simon"] = a != simon_stream(3301, 16)
    plants["ne_xoro"] = a != xoroshiro128ss(3301, 16)
    plants["ne_hi"] = a != speck_stream(3301, 16, True)
    for name, gen in gens:
        ks = gen(3301, len(pt) * 4)
        rec = [(p + ks[i]) % Q for i, p in enumerate(pt)]
        plants[f"{name}_rigid"] = [apply_p(c, ks[i], "sub") for i, c in enumerate(rec)] == pt
        ct, _ = encrypt_reject(pt, ks)
        recb = beam_decode(ct, ks)
        agree = sum(x == y for x, y in zip(recb, pt)) / len(pt) if recb else 0.0
        plants[f"{name}_beam"] = {"agree": round(agree, 4), "ok": agree >= 0.85}
        wrong = gen(2014, len(pt))
        plants[f"{name}_wrong"] = [apply_p((p + ks[i]) % Q, wrong[i], "sub") for i, p in enumerate(pt)] != pt
    plants["ok"] = all(
        (v is True) or (isinstance(v, dict) and v.get("ok"))
        for k, v in plants.items() if k != "ok"
    )
    print("plant", plants, flush=True)
    if not plants["ok"]:
        (OUT / "result.json").write_text(json.dumps({
            "experiment": "EXP-LP-SPECK-SIMON-001", "plant": plants,
            "verified_new_unsolved_runes": 0, "aborted": "plant failed",
        }, indent=2) + "\n")
        return

    seeds = marked_seeds()
    pages = [(f"split{s:03d}", idxs_of(s)) for s in range(15, 71) if len(idxs_of(s)) >= 80]
    compact = [("prefix400", prefix(400))] + [
        (n, t) for n, t in pages if n in ("split015", "split017", "split040", "split063")
    ]
    hits, tested_r, tested_b, best = [], 0, 0, None
    core = gens[:3]
    for slabel, seed in seeds:
        for tname, ct in ([("prefix400", prefix(400))] + pages):
            for gname, gen in core:
                ks = gen(seed, len(ct))
                for rel in ("sub", "add", "beau"):
                    tested_r += 1
                    rec = [apply_p(c, ks[i], rel) for i, c in enumerate(ct)]
                    lat = GP.latin_stream(rec)
                    sc = score_candidate(rec, lat)
                    row = {"pass": "rigid", "gen": gname, "seed": slabel, "span": tname,
                           "rel": rel, "head": lat[:80], **sc, "n": len(rec)}
                    if best is None or sc["trigram_per_100"] > best["trigram_per_100"]:
                        best = row
                    if keep(sc, len(rec)):
                        hits.append(row)
                        print("KEEP", gname, slabel, tname, rel, sc["trigram_per_100"], lat[:40], flush=True)
        for tname, ct in compact:
            ks = gens[3][1](seed, len(ct))
            for rel in ("sub", "add", "beau"):
                tested_r += 1
                rec = [apply_p(c, ks[i], rel) for i, c in enumerate(ct)]
                lat = GP.latin_stream(rec)
                sc = score_candidate(rec, lat)
                row = {"pass": "rigid", "gen": "speck_hi5", "seed": slabel, "span": tname,
                       "rel": rel, "head": lat[:80], **sc, "n": len(rec)}
                if best is None or sc["trigram_per_100"] > best["trigram_per_100"]:
                    best = row
                if keep(sc, len(rec)):
                    hits.append(row)

    for slabel, seed in seeds:
        for tname, ct in (("prefix400", prefix(400)), ("split015", idxs_of(15))):
            for gname, gen in core:
                tested_b += 1
                ks = gen(seed, len(ct) * 4)
                rec = beam_decode(ct, ks)
                lat = GP.latin_stream(rec)
                sc = score_candidate(rec, lat)
                row = {"pass": "beam", "gen": gname, "seed": slabel, "span": tname,
                       "rel": "sub", "head": lat[:80], **sc, "n": len(rec)}
                if best is None or sc["trigram_per_100"] > best["trigram_per_100"]:
                    best = row
                if keep(sc, len(rec)):
                    hits.append(row)
                    print("KEEP beam", gname, slabel, tname, sc["trigram_per_100"], lat[:40], flush=True)

    result = {
        "experiment": "EXP-LP-SPECK-SIMON-001",
        "family": "SPECK-64/128 + SIMON-64/128 CTR + xoroshiro128** (`%29` + speck hi5)",
        "plant": plants,
        "n_seeds": len(seeds),
        "tested_rigid": tested_r,
        "tested_beam": tested_b,
        "tested": tested_r + tested_b,
        "keep_bar_hits": len(hits),
        "keeps": hits[:16],
        "best": {k: best[k] for k in ("pass", "gen", "seed", "span", "rel", "head", "trigram_per_100", "ioc")} if best else None,
        "skeptic_review": {"verdict": "null" if not hits else "keep-bar needs human English", "english": False},
        "verified_new_unsolved_runes": 0,
        "boundary": "not a 2^128 grind; AES-CTR / ChaCha / xoshiro256 already closed",
    }
    (OUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print("tested_r", tested_r, "tested_b", tested_b, "keeps", len(hits),
          "best", None if not best else (best["trigram_per_100"], best["gen"], best["head"][:40]))


if __name__ == "__main__":
    main()
