#!/usr/bin/env python3
"""Geffe combiner and shrinking generator — unused classical LFSR combiners.

xorshift/PCG/ISAAC/KISS/MWC/MT19937/LCG-mod29 are closed. Geffe (three LFSRs,
majority-style AND/XOR) and the shrinking generator were not a keystream here.
Marked seeds only.
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
from exp_skipaware_sha_ctr import beam_decode, encrypt_reject, idxs_of, keep, prefix  # noqa: E402
from exp_xorshift_pcg import marked_seeds, rigid  # noqa: E402

GP = Gematria()
Q = 29
MASK16 = 0xFFFF
OUT = CICADA_ROOT / "experiments" / "EXP-LP-GEFFE-SHRINK-001"
# primitive-ish 16-bit taps (x^16+x^5+x^3+x^2+1 etc. as right-shift Galois)
POLYS = (0x8016, 0x801C, 0x804E, 0x8299)


def lfsr16(seed: int, poly: int, nbits: int) -> list[int]:
    s = (seed & MASK16) or 1
    out = []
    for _ in range(nbits):
        bit = s & 1
        s >>= 1
        if bit:
            s ^= poly
        s &= MASK16
        if s == 0:
            s = 1
        out.append(bit)
    return out


def bits_to_runes(bits: list[int]) -> list[int]:
    out = []
    acc = 0
    k = 0
    for b in bits:
        acc = (acc << 1) | b
        k += 1
        if k == 5:
            out.append(acc % Q)
            acc = k = 0
    return out


def geffe(seed: int, n: int) -> list[int]:
    need = n * 5 + 16
    x = lfsr16(seed, POLYS[0], need)
    y = lfsr16(seed ^ 0x3301, POLYS[1], need)
    z = lfsr16((seed * 3 + 1) & MASK16, POLYS[2], need)
    bits = [((x[i] & y[i]) ^ ((1 - x[i]) & z[i])) for i in range(need)]
    return bits_to_runes(bits)[:n]


def shrink(seed: int, n: int) -> list[int]:
    # generate extra bits; keep data bits when control is 1
    need = n * 5 * 3 + 32
    data = lfsr16(seed, POLYS[0], need)
    ctrl = lfsr16(seed ^ 0x5A5A, POLYS[3], need)
    bits = [d for d, c in zip(data, ctrl) if c]
    return bits_to_runes(bits)[:n]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    plant_pt = GP.encode_latin_key(
        "THEPRIMESARESACREDTHETOTIENTFVNCTIANISSACREDALLTHNGSSHOVLDBEENCRYPTEDAWARNNGBELIEVENOTHNG"
    )
    gens = [("geffe", geffe), ("shrink", shrink)]
    plants = {}
    for name, gen in gens:
        pks = gen(3301, len(plant_pt) * 4)
        rec = rigid([(p + pks[i]) % Q for i, p in enumerate(plant_pt)], pks, "sub")
        plants[f"{name}_rigid"] = rec == plant_pt
        ct, _ = encrypt_reject(plant_pt, pks)
        recb = beam_decode(ct, pks)
        agree = sum(a == b for a, b in zip(recb, plant_pt)) / len(plant_pt) if recb else 0.0
        plants[f"{name}_beam"] = {"agree": round(agree, 4), "ok": agree >= 0.85}
        plants[f"{name}_wrong"] = rigid(
            [(p + pks[i]) % Q for i, p in enumerate(plant_pt)],
            gen(3302, len(plant_pt) * 4), "sub") != plant_pt
    plants["ok"] = all(
        (v is True) or (isinstance(v, dict) and v.get("ok"))
        for k, v in plants.items() if k != "ok"
    )
    print("plant", plants, flush=True)
    if not plants["ok"]:
        (OUT / "result.json").write_text(json.dumps({
            "experiment": "EXP-LP-GEFFE-SHRINK-001", "plant": plants,
            "verified_new_unsolved_runes": 0, "aborted": "plant failed",
        }, indent=2) + "\n")
        return

    seeds = marked_seeds()
    pages = [("prefix400", prefix(400)), ("split015", idxs_of(15)),
             ("split017", idxs_of(17)), ("split040", idxs_of(40))]
    hits, tested_r, tested_b, best = [], 0, 0, None
    for gname, gen in gens:
        for slabel, seed in seeds:
            for tname, ct in pages:
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
            rec = beam_decode(ct, gen(seed, len(ct) * 4))
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
        "experiment": "EXP-LP-GEFFE-SHRINK-001",
        "family": "marked-seed Geffe combiner + shrinking LFSR",
        "plant": plants,
        "n_seeds": len(seeds),
        "tested_rigid": tested_r,
        "tested_beam": tested_b,
        "tested": tested_r + tested_b,
        "keep_bar_hits": len(hits),
        "keeps": hits[:12],
        "best": {k: best[k] for k in ("pass", "gen", "seed", "span", "rel", "head", "trigram_per_100", "ioc")} if best else None,
        "skeptic_review": {"verdict": "null" if not hits else "keep-bar needs human English"},
        "verified_new_unsolved_runes": 0,
    }
    (OUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print("tested_r", tested_r, "tested_b", tested_b, "keeps", len(hits),
          "best", None if not best else (best["trigram_per_100"], best["gen"], best["head"][:40]))


if __name__ == "__main__":
    main()
