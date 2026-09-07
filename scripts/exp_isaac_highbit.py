#!/usr/bin/env python3
"""ISAAC CSPRNG + high-bit output maps of xorshift/PCG (the XORSHIFT-PCG boundary).

EXP-LP-XORSHIFT-PCG-001 used `state % 29`. High bits are the usual PRNG extract
(xorshift >> 27, xoroshiro already uses a ** scramble). ISAAC was never a
keystream in this tree. Marked seeds only — not a 2^32 grind.
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
from exp_xorshift_pcg import (  # noqa: E402
    MASK32,
    galois32,
    marked_seeds,
    pcg32,
    rigid,
    xoroshiro64ss,
    xorshift32,
)

GP = Gematria()
Q = 29
OUT = CICADA_ROOT / "experiments" / "EXP-LP-ISAAC-HIGHBIT-001"


def xorshift32_hi(seed: int, n: int) -> list[int]:
    y = (seed & MASK32) or 1
    out: list[int] = []
    for _ in range(n):
        y ^= (y << 13) & MASK32
        y ^= y >> 17
        y ^= (y << 5) & MASK32
        y &= MASK32
        out.append((y >> 27) % Q)
    return out


def galois32_hi(seed: int, n: int) -> list[int]:
    s = (seed & MASK32) or 1
    poly = 0x80200003
    out: list[int] = []
    for _ in range(n):
        lsb = s & 1
        s >>= 1
        if lsb:
            s ^= poly
        s &= MASK32
        if s == 0:
            s = 1
        out.append((s >> 27) % Q)
    return out


def pcg32_hi(seed: int, n: int) -> list[int]:
    """Reuse PCG output but take high 5 bits of the 32-bit result, not % 29."""
    # Recreate the 32-bit values: call pcg32 then we need raw. Duplicate inner loop.
    state = (seed & 0xFFFFFFFFFFFFFFFF) or 1
    inc = 1442695040888963407
    out: list[int] = []
    for _ in range(n):
        old = state
        state = (old * 6364136223846793005 + inc) & 0xFFFFFFFFFFFFFFFF
        xorshifted = (((old >> 18) ^ old) >> 27) & MASK32
        rot = (old >> 59) & 31
        val = ((xorshifted >> rot) | ((xorshifted << ((-rot) & 31)) & MASK32)) & MASK32
        out.append((val >> 27) % Q)
    return out


class Isaac:
    """Bob Jenkins ISAAC. Seeded by filling mm[] from a 32-bit seed expanded."""

    def __init__(self, seed: int) -> None:
        self.mm = [0] * 256
        self.randrsl = [0] * 256
        self.aa = self.bb = self.cc = 0
        h = hashlib.sha256(seed.to_bytes(8, "big")).digest()
        for i in range(256):
            block = hashlib.sha256(h + i.to_bytes(4, "big")).digest()
            self.randrsl[i] = int.from_bytes(block[:4], "little")
        self._randinit()
        self.idx = 256

    def _mix(self, a):
        a[0] ^= (a[1] << 11) & MASK32; a[3] = (a[3] + a[0]) & MASK32; a[1] = (a[1] + a[2]) & MASK32
        a[1] ^= (a[2] >> 2); a[4] = (a[4] + a[1]) & MASK32; a[2] = (a[2] + a[3]) & MASK32
        a[2] ^= (a[3] << 8) & MASK32; a[5] = (a[5] + a[2]) & MASK32; a[3] = (a[3] + a[4]) & MASK32
        a[3] ^= (a[4] >> 16); a[6] = (a[6] + a[3]) & MASK32; a[4] = (a[4] + a[5]) & MASK32
        a[4] ^= (a[5] << 10) & MASK32; a[7] = (a[7] + a[4]) & MASK32; a[5] = (a[5] + a[6]) & MASK32
        a[5] ^= (a[6] >> 4); a[0] = (a[0] + a[5]) & MASK32; a[6] = (a[6] + a[7]) & MASK32
        a[6] ^= (a[7] << 8) & MASK32; a[1] = (a[1] + a[6]) & MASK32; a[7] = (a[7] + a[0]) & MASK32
        a[7] ^= (a[0] >> 9); a[2] = (a[2] + a[7]) & MASK32; a[0] = (a[0] + a[1]) & MASK32
        return a

    def _isaac(self) -> None:
        self.cc = (self.cc + 1) & MASK32
        self.bb = (self.bb + self.cc) & MASK32
        for i in range(256):
            x = self.mm[i]
            if i % 4 == 0:
                self.aa = (self.aa ^ ((self.aa << 13) & MASK32)) & MASK32
            elif i % 4 == 1:
                self.aa = (self.aa ^ (self.aa >> 6)) & MASK32
            elif i % 4 == 2:
                self.aa = (self.aa ^ ((self.aa << 2) & MASK32)) & MASK32
            else:
                self.aa = (self.aa ^ (self.aa >> 16)) & MASK32
            self.aa = (self.mm[(i + 128) & 255] + self.aa) & MASK32
            y = self.mm[(x >> 2) & 255] + self.aa + self.bb
            y &= MASK32
            self.mm[i] = y
            self.bb = (self.mm[(y >> 10) & 255] + x) & MASK32
            self.randrsl[i] = self.bb

    def _randinit(self) -> None:
        a = [0x9E3779B9] * 8
        for _ in range(4):
            a = self._mix(a)
        for i in range(0, 256, 8):
            for j in range(8):
                a[j] = (a[j] + self.randrsl[i + j]) & MASK32
            a = self._mix(a)
            for j in range(8):
                self.mm[i + j] = a[j]
        for i in range(0, 256, 8):
            for j in range(8):
                a[j] = (a[j] + self.mm[i + j]) & MASK32
            a = self._mix(a)
            for j in range(8):
                self.mm[i + j] = a[j]
        self._isaac()

    def next32(self) -> int:
        if self.idx >= 256:
            self._isaac()
            self.idx = 0
        v = self.randrsl[self.idx]
        self.idx += 1
        return v


def isaac_mod(seed: int, n: int) -> list[int]:
    rng = Isaac(seed)
    return [rng.next32() % Q for _ in range(n)]


def isaac_hi(seed: int, n: int) -> list[int]:
    rng = Isaac(seed)
    return [(rng.next32() >> 27) % Q for _ in range(n)]


def generators() -> list[tuple[str, callable]]:
    return [
        ("isaac_mod", isaac_mod),
        ("isaac_hi", isaac_hi),
        ("xs32_hi", xorshift32_hi),
        ("pcg32_hi", pcg32_hi),
        ("galois32_hi", galois32_hi),
        ("xoroshiro64ss", xoroshiro64ss),  # already ** scramble; include for hi-bit twin via % already closed
    ]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    plant_pt = GP.encode_latin_key(
        "THEPRIMESARESACREDTHETOTIENTFVNCTIANISSACREDALLTHNGSSHOVLDBEENCRYPTEDAWARNNGBELIEVENOTHNG"
    )
    # drop xoroshiro from this experiment's plant/scan — already closed; keep hi maps + isaac
    gens = [g for g in generators() if g[0] != "xoroshiro64ss"]
    plants = {}
    for name, gen in gens:
        pks = gen(3301, len(plant_pt) * 4)
        rec = rigid([(p + pks[i]) % Q for i, p in enumerate(plant_pt)], pks, "sub")
        plants[f"{name}_rigid"] = rec == plant_pt
        ct, _ = encrypt_reject(plant_pt, pks)
        recb = beam_decode(ct, pks)
        agree = sum(a == b for a, b in zip(recb, plant_pt)) / len(plant_pt) if recb else 0.0
        plants[f"{name}_beam"] = {"agree": round(agree, 4), "ok": agree >= 0.85}
    plants["ok"] = all(
        (v is True) or (isinstance(v, dict) and v.get("ok")) for k, v in plants.items() if k != "ok"
    )
    print("plant", plants, flush=True)
    if not plants["ok"]:
        (OUT / "result.json").write_text(json.dumps({
            "experiment": "EXP-LP-ISAAC-HIGHBIT-001", "plant": plants,
            "verified_new_unsolved_runes": 0, "aborted": "plant failed",
        }, indent=2) + "\n")
        return

    seeds = marked_seeds()
    pages_sel = [("prefix400", prefix(400)), ("split015", idxs_of(15)),
                 ("split017", idxs_of(17)), ("split040", idxs_of(40))]
    hits, tested_r, tested_b, best = [], 0, 0, None
    for gname, gen in gens:
        for slabel, seed in seeds:
            for tname, ct in pages_sel:
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
                        print("KEEP", gname, slabel, tname, rel, sc["trigram_per_100"], lat[:40], flush=True)
    for gname, gen in gens:
        for slabel, seed in seeds:
            ct = prefix(400)
            tested_b += 1
            ks = gen(seed, len(ct) * 4)
            rec = beam_decode(ct, ks)
            lat = GP.latin_stream(rec)
            sc = score_candidate(rec, lat)
            row = {"pass": "beam", "gen": gname, "seed": slabel, "span": "prefix400",
                   "rel": "sub", "head": lat[:80], **sc, "n": len(rec)}
            if best is None or sc["trigram_per_100"] > best["trigram_per_100"]:
                best = row
            if keep(sc, len(rec)):
                hits.append(row)
                print("KEEP beam", gname, slabel, sc["trigram_per_100"], lat[:40], flush=True)

    result = {
        "experiment": "EXP-LP-ISAAC-HIGHBIT-001",
        "family": "ISAAC CSPRNG + high-bit extracts of xorshift32/PCG/Galois",
        "plant": plants,
        "n_seeds": len(seeds),
        "tested_rigid": tested_r,
        "tested_beam": tested_b,
        "tested": tested_r + tested_b,
        "keep_bar_hits": len(hits),
        "keeps": hits[:15],
        "best": {k: best[k] for k in ("pass", "gen", "seed", "span", "rel", "head", "trigram_per_100", "ioc")} if best else None,
        "skeptic_review": {"verdict": "null" if not hits else "keep-bar needs human English"},
        "verified_new_unsolved_runes": 0,
    }
    (OUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print("tested_rigid", tested_r, "tested_beam", tested_b, "keeps", len(hits),
          "best", None if not best else (best["trigram_per_100"], best["gen"], best["head"][:40]))


if __name__ == "__main__":
    main()
