#!/usr/bin/env python3
"""Marked-seed Wolfram Rule 30 CA and xoshiro256** keystreams.

xoroshiro64** is closed (EXP-LP-XORSHIFT-PCG-001). HANDOFF named the unused
siblings: Rule 30 (Mathematica-style CA) and xoshiro256**. State space is
huge — marked integer/SHA32 seeds only, as with the other PRNG slices.
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
OUT = CICADA_ROOT / "experiments" / "EXP-LP-RULE30-XOSHIRO-001"


def _rotl64(x: int, k: int) -> int:
    x &= MASK64
    return ((x << k) | (x >> (64 - k))) & MASK64


def splitmix64_next(state: int) -> tuple[int, int]:
    state = (state + 0x9E3779B97F4A7C15) & MASK64
    z = state
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & MASK64
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & MASK64
    return state, (z ^ (z >> 31)) & MASK64


def seed_xoshiro256(seed: int) -> list[int]:
    s: list[int] = []
    st = seed & MASK64
    if st == 0:
        st = 1
    for _ in range(4):
        st, z = splitmix64_next(st)
        s.append(z)
    return s


def xoshiro256ss(seed: int, n: int) -> list[int]:
    """xoshiro256** (Blackman/Vigna), output % 29."""
    s = seed_xoshiro256(seed)
    out: list[int] = []
    for _ in range(n):
        result = (_rotl64((s[1] * 5) & MASK64, 7) * 9) & MASK64
        out.append(result % Q)
        t = (s[1] << 17) & MASK64
        s[2] ^= s[0]
        s[3] ^= s[1]
        s[1] ^= s[2]
        s[0] ^= s[3]
        s[2] ^= t
        s[3] = _rotl64(s[3], 45)
    return out


def xoshiro256ss_hi5(seed: int, n: int) -> list[int]:
    s = seed_xoshiro256(seed)
    out: list[int] = []
    for _ in range(n):
        result = (_rotl64((s[1] * 5) & MASK64, 7) * 9) & MASK64
        out.append((result >> 59) % Q)
        t = (s[1] << 17) & MASK64
        s[2] ^= s[0]
        s[3] ^= s[1]
        s[1] ^= s[2]
        s[0] ^= s[3]
        s[2] ^= t
        s[3] = _rotl64(s[3], 45)
    return out


def _bits_from_seed(seed: int, width: int) -> list[int]:
    row = [0] * width
    if seed == 0:
        row[width // 2] = 1
        return row
    x = seed & MASK64
    # sprinkle seed bits around the centre (Mathematica-style finite CA)
    mid = width // 2
    for i in range(64):
        if (x >> i) & 1:
            row[(mid - 32 + i) % width] = 1
    if not any(row):
        row[mid] = 1
    return row


def _evolve30(row: list[int]) -> list[int]:
    w = len(row)
    nxt = [0] * w
    for i in range(w):
        left = row[(i - 1) % w]
        cell = row[i]
        right = row[(i + 1) % w]
        nxt[i] = left ^ (cell | right)
    return nxt


def rule30_center_pack5(seed: int, n: int, width: int = 257) -> list[int]:
    """Centre-cell bitstream, 5 bits → symbol (reject 29–31)."""
    row = _bits_from_seed(seed, width)
    mid = width // 2
    out: list[int] = []
    acc = 0
    bits = 0
    # bound steps: worst case some 5-bit windows are 29–31
    steps = 0
    limit = n * 8 + 64
    while len(out) < n and steps < limit:
        acc = (acc << 1) | row[mid]
        bits += 1
        if bits == 5:
            if acc < Q:
                out.append(acc)
            acc = 0
            bits = 0
        row = _evolve30(row)
        steps += 1
    while len(out) < n:
        out.append(0)
    return out


def rule30_row_mod(seed: int, n: int, width: int = 64) -> list[int]:
    """Each generation the row integer % 29."""
    row = _bits_from_seed(seed, width)
    out: list[int] = []
    for _ in range(n):
        val = 0
        for b in row:
            val = (val << 1) | b
        out.append(val % Q)
        row = _evolve30(row)
    return out


def generators() -> list[tuple[str, callable]]:
    return [
        ("xoshiro256ss", xoshiro256ss),
        ("xoshiro256ss_hi5", xoshiro256ss_hi5),
        ("rule30_c257", rule30_center_pack5),
        ("rule30_row64", rule30_row_mod),
    ]


def marked_seeds() -> list[tuple[str, int]]:
    out: list[tuple[str, int]] = []
    for n in (
        1, 15, 56, 57, 3301, 2012, 2013, 2014, 2017, 1295, 1033,
        0x7A35090F, 0x57A35090, 0x6D854CD7, 0x181F01E5, 0x845145127 & MASK32,
    ):
        out.append((f"int:{n}", n & MASK64))
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
        pks = gen(3301, len(plant_pt) * 4)
        rec = rigid([(p + pks[i]) % Q for i, p in enumerate(plant_pt)], pks, "sub")
        plants[f"{name}_rigid"] = rec == plant_pt
        ct, _ = encrypt_reject(plant_pt, pks)
        recb = beam_decode(ct, pks)
        agree = sum(a == b for a, b in zip(recb, plant_pt)) / len(plant_pt) if recb else 0.0
        plants[f"{name}_beam"] = {"agree": round(agree, 4), "ok": agree >= 0.89}
        wrong = gen(2014, len(plant_pt))
        plants[f"{name}_wrong"] = rigid(
            [(p + pks[i]) % Q for i, p in enumerate(plant_pt)], wrong, "sub"
        ) != plant_pt
    plants["ok"] = all(
        (v is True) or (isinstance(v, dict) and v.get("ok"))
        for k, v in plants.items() if k != "ok"
    )
    print("plant", plants, flush=True)
    if not plants["ok"]:
        (OUT / "result.json").write_text(json.dumps({
            "experiment": "EXP-LP-RULE30-XOSHIRO-001", "plant": plants,
            "verified_new_unsolved_runes": 0, "aborted": "plant failed",
        }, indent=2) + "\n")
        return

    gens = generators()
    seeds = marked_seeds()
    pages = [(f"split{s:03d}", idxs_of(s)) for s in range(15, 71) if len(idxs_of(s)) >= 80]
    rigid_targets = [("prefix400", prefix(400))] + [
        (n, t) for n, t in pages if n in ("split015", "split017", "split040", "split063")
    ]
    # full-page rigid on the two primary gens only
    primary = [g for g in gens if g[0] in ("xoshiro256ss", "rule30_c257")]
    hits, tested_r, tested_b, best = [], 0, 0, None

    for gname, gen in primary:
        for slabel, seed in seeds:
            for tname, ct in ([("prefix400", prefix(400))] + pages if gname == "xoshiro256ss" else rigid_targets):
                ks = gen(seed, len(ct))
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

    # remaining gens: compact rigid
    extra = [g for g in gens if g[0] not in ("xoshiro256ss",)]
    for gname, gen in extra:
        if gname == "rule30_c257":
            continue
        for slabel, seed in seeds:
            for tname, ct in rigid_targets:
                ks = gen(seed, len(ct))
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

    targets_beam = [("prefix400", prefix(400)), ("split015", idxs_of(15))]
    for gname, gen in primary:
        for slabel, seed in seeds:
            for tname, ct in targets_beam:
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
                    print("KEEP", row["pass"], gname, slabel, tname,
                          sc["trigram_per_100"], lat[:40], flush=True)

    result = {
        "experiment": "EXP-LP-RULE30-XOSHIRO-001",
        "family": "marked-seed Wolfram Rule 30 CA + xoshiro256**",
        "plant": plants,
        "n_seeds": len(seeds),
        "tested_rigid": tested_r,
        "tested_beam": tested_b,
        "tested": tested_r + tested_b,
        "keep_bar_hits": len(hits),
        "keeps": hits[:20],
        "best": {k: best[k] for k in ("pass", "gen", "seed", "span", "rel", "head", "trigram_per_100", "ioc")} if best else None,
        "skeptic_review": {
            "verdict": "null" if not hits else "keep-bar needs human English",
            "english": False,
        },
        "verified_new_unsolved_runes": 0,
        "boundary": "not exhaustive over 2^256 / CA ICs; not other rule numbers",
    }
    (OUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print("tested_rigid", tested_r, "tested_beam", tested_b, "keeps", len(hits),
          "best", None if not best else (best["trigram_per_100"], best["gen"], best["head"][:40]))


if __name__ == "__main__":
    main()
