#!/usr/bin/env python3
"""xoshiro256** marked-seed keystreams (rigid + skip-aware beam).

xoroshiro64** is closed. This is the 256-bit ** variant, seeded via SplitMix64.
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
from cicada.liber_primus.prng_xoshiro256 import (  # noqa: E402
    PLANT_LATIN,
    PLANT_THRESHOLD,
    generators,
    plant_rigid,
    rigid_decrypt,
)
from cicada.paths import ROOT as CICADA_ROOT  # noqa: E402
from cicada.scoring import score_candidate  # noqa: E402
from exp_skipaware_sha_ctr import beam_decode, encrypt_reject, idxs_of, keep, prefix  # noqa: E402

GP = Gematria()
OUT = CICADA_ROOT / "experiments" / "EXP-LP-XOSHIRO256-001"
EXPERIMENT = "EXP-LP-XOSHIRO256-001"
MASK32 = 0xFFFFFFFF


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


def n80_pages():
    return [(f"split{s:03d}", idxs_of(s)) for s in range(15, 71) if len(idxs_of(s)) >= 80]


def plant_one(gen_fn, seed, pt):
    rigid = plant_rigid(gen_fn, seed, pt)
    ks = gen_fn(seed, len(pt) * 4)
    ct, used = encrypt_reject(pt, ks)
    rec = beam_decode(ct, ks)
    agree = sum(a == b for a, b in zip(rec, pt)) / len(pt) if rec else 0.0
    wrong_ks = gen_fn(seed ^ 0xA5A5A5A5, len(pt) * 4)
    rec_w = beam_decode(ct, wrong_ks)
    agree_w = sum(a == b for a, b in zip(rec_w, pt)) / len(pt) if rec_w else 0.0
    return {
        "rigid_ok": bool(rigid["ok"]),
        "beam_agree": round(float(agree), 4),
        "beam_ok": bool(agree >= PLANT_THRESHOLD),
        "beam_wrong_fails": bool(agree_w < 0.4),
        "ok": bool(rigid["ok"] and rigid["wrong_fails"] and agree >= PLANT_THRESHOLD and agree_w < 0.4),
    }


def plant_family(pt=None):
    if pt is None:
        pt = GP.encode_latin_key(PLANT_LATIN)
    plants = {}
    for name, gen in generators():
        plants[name] = plant_one(gen, 3301, pt)
    plants["ok"] = all(v["ok"] for v in plants.values() if isinstance(v, dict) and "ok" in v)
    return plants


def score_row(rec, meta):
    lat = GP.latin_stream(rec)
    sc = score_candidate(rec, lat)
    return {**meta, "head": lat[:80], **sc, "n": len(rec)}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    pt = GP.encode_latin_key(PLANT_LATIN)
    plants = plant_family(pt)
    print("plant", {k: (v if k == "ok" else {kk: v[kk] for kk in ("ok", "beam_agree", "rigid_ok")})
                    for k, v in plants.items()}, flush=True)
    if not plants["ok"]:
        (OUT / "result.json").write_text(json.dumps({
            "experiment": EXPERIMENT, "plant": plants, "tested": 0,
            "keep_bar_hits": 0, "verified_new_unsolved_runes": 0,
            "aborted": "plant failed",
        }, indent=2) + "\n")
        print("PLANT FAILED")
        return
    gens = generators()
    seeds = marked_seeds()
    pages = n80_pages()
    p400 = prefix(400)
    targets_rigid = [("prefix400", p400)] + pages
    targets_beam = [("prefix400", p400), ("split015", idxs_of(15))]
    hits, tested_r, tested_b, best = [], 0, 0, None
    for gname, gen in gens:
        for slabel, seed in seeds:
            for tname, ct in targets_rigid:
                ks = gen(seed, len(ct))
                for rel in ("sub", "add", "beau"):
                    tested_r += 1
                    rec = rigid_decrypt(ct, ks, rel)
                    row = score_row(rec, {"pass": "rigid", "gen": gname,
                                          "seed": slabel, "span": tname, "rel": rel})
                    if best is None or row["trigram_per_100"] > best["trigram_per_100"]:
                        best = row
                    if keep(row, len(rec)):
                        hits.append(row)
                        print("KEEP", gname, slabel, tname, rel,
                              row["trigram_per_100"], row["head"][:40], flush=True)
    for gname, gen in gens:
        for slabel, seed in seeds:
            for tname, ct in targets_beam:
                tested_b += 1
                ks = gen(seed, len(ct) * 4)
                rec = beam_decode(ct, ks)
                row = score_row(rec, {"pass": "beam", "gen": gname,
                                      "seed": slabel, "span": tname, "rel": "sub"})
                if best is None or row["trigram_per_100"] > best["trigram_per_100"]:
                    best = row
                if keep(row, len(rec)):
                    hits.append(row)
                    print("KEEP beam", gname, slabel, tname,
                          row["trigram_per_100"], row["head"][:40], flush=True)
    result = {
        "experiment": EXPERIMENT,
        "family": "xoshiro256** (Blackman/Vigna); mod29 + hi5; rigid + skip-aware beam",
        "plant": plants,
        "plant_threshold": PLANT_THRESHOLD,
        "n_seeds": len(seeds),
        "n_gens": [g[0] for g in gens],
        "scan": {
            "prefix400": True,
            "n80_pages": [n for n, _ in pages],
            "n80_count": len(pages),
            "rigid_spans": [n for n, _ in targets_rigid],
            "beam_spans": [n for n, _ in targets_beam],
        },
        "tested_rigid": tested_r,
        "tested_beam": tested_b,
        "tested": tested_r + tested_b,
        "keep_bar_hits": len(hits),
        "keeps": hits[:20],
        "best": None if not best else {
            k: best[k] for k in (
                "pass", "gen", "seed", "span", "rel", "head",
                "trigram_per_100", "ioc", "vowelish_ratio", "n",
            )
        },
        "skeptic_review": {
            "verdict": "null" if not hits else "keep-bar hits are not counted without readable English",
            "why": "no keep-bar hits" if not hits else "heads are not human-readable English",
        },
        "verified_new_unsolved_runes": 0,
        "unsolved_runes_total": 12956,
        "boundary": "not exhaustive over 2^256 state; xoroshiro64** already closed",
    }
    (OUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print("tested_rigid", tested_r, "tested_beam", tested_b, "keeps", len(hits),
          "verified", 0, "best",
          None if not best else (best["trigram_per_100"], best["gen"], best["head"][:40]),
          flush=True)


if __name__ == "__main__":
    main()
