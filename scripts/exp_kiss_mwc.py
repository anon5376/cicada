#!/usr/bin/env python3
"""Marked-seed Marsaglia KISS / MWC / CMWC keystreams (rigid + skip-aware beam).

LCG, lagged-Fibonacci, MT19937, xorshift32, xoroshiro64**, PCG, Galois LFSR,
and ISAAC are closed. Marsaglia's *files* were slid as pads; his *generators*
were not. Marked seeds only (3301, 1033, 0x7A35090F, SHA32 of attested words).
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
from cicada.liber_primus.prng_kiss import (  # noqa: E402
    MASK32,
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
Q = 29
OUT = CICADA_ROOT / "experiments" / "EXP-LP-KISS-MWC-001"
EXPERIMENT = "EXP-LP-KISS-MWC-001"


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


def n80_pages() -> list[tuple[str, list[int]]]:
    pages = []
    for s in range(15, 71):
        ct = idxs_of(s)
        if len(ct) >= 80:
            pages.append((f"split{s:03d}", ct))
    return pages


def plant_one(gen_fn, seed: int, pt: list[int]) -> dict:
    """Rigid exact + skip-aware beam; wrong seed must fail both."""
    rigid = plant_rigid(gen_fn, seed, pt)
    ks = gen_fn(seed, len(pt) * 4)
    ct, used = encrypt_reject(pt, ks)
    rec = beam_decode(ct, ks)
    agree = sum(a == b for a, b in zip(rec, pt)) / len(pt) if rec else 0.0
    wrong_ks = gen_fn(seed ^ 0xA5A5A5A5, len(pt) * 4)
    rec_w = beam_decode(ct, wrong_ks)
    agree_w = sum(a == b for a, b in zip(rec_w, pt)) / len(pt) if rec_w else 0.0
    beam_ok = agree >= PLANT_THRESHOLD
    wrong_fails = agree_w < 0.4
    return {
        "rigid_ok": bool(rigid["ok"]),
        "rigid_agree": round(float(rigid["agree"]), 4),
        "rigid_wrong_fails": bool(rigid["wrong_fails"]),
        "beam_agree": round(float(agree), 4),
        "beam_ok": bool(beam_ok),
        "beam_wrong_agree": round(float(agree_w), 4),
        "beam_wrong_fails": bool(wrong_fails),
        "extra_skips": int(sum(1 for a, b in zip([0] + used, used) if b - a > 1)),
        "ok": bool(rigid["ok"] and rigid["wrong_fails"] and beam_ok and wrong_fails),
    }


def plant_family(pt: list[int] | None = None) -> dict:
    if pt is None:
        pt = GP.encode_latin_key(PLANT_LATIN)
    plants = {}
    for name, gen in generators():
        plants[name] = plant_one(gen, 3301, pt)
    plants["ok"] = all(v["ok"] for v in plants.values() if isinstance(v, dict) and "ok" in v)
    return plants


def score_row(rec: list[int], meta: dict) -> dict:
    lat = GP.latin_stream(rec)
    sc = score_candidate(rec, lat)
    return {**meta, "head": lat[:80], **sc, "n": len(rec)}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    pt = GP.encode_latin_key(PLANT_LATIN)
    plants = plant_family(pt)
    print("plant", {k: (v if k == "ok" else {kk: v[kk] for kk in ("ok", "beam_agree", "rigid_ok")})
                    for k, v in plants.items()}, flush=True)
    if not plants["ok"]:
        (OUT / "result.json").write_text(json.dumps({
            "experiment": EXPERIMENT,
            "plant": plants,
            "tested": 0,
            "keep_bar_hits": 0,
            "verified_new_unsolved_runes": 0,
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
    # beam is slower: %29 maps only (hi-bit is the output-map twin, rigid covers it)
    beam_gens = [(n, g) for n, g in gens if n.endswith("_mod")]

    hits, tested_r, tested_b, best = [], 0, 0, None
    page_names = [n for n, _ in targets_rigid]

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

    for gname, gen in beam_gens:
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

    verified = 0

    result = {
        "experiment": EXPERIMENT,
        "family": "marked-seed Marsaglia KISS99 / 16-bit MWC / 32-bit MWC / CMWC-lag3 (mod29 + hi5)",
        "plant": {k: v for k, v in plants.items()},
        "plant_threshold": PLANT_THRESHOLD,
        "n_seeds": len(seeds),
        "n_gens": [g[0] for g in gens],
        "scan": {
            "prefix400": True,
            "n80_pages": [n for n, _ in pages],
            "n80_count": len(pages),
            "rigid_spans": page_names,
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
            "why": (
                "no keep-bar hits"
                if not hits else
                "keep bar is rigid-unique only; none of the heads are human-readable English"
            ),
        },
        "verified_new_unsolved_runes": verified,
        "unsolved_runes_total": 12956,
        "boundary": "not exhaustive over 2^32 seeds; not skip-aware at arbitrary offsets",
    }
    (OUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print("tested_rigid", tested_r, "tested_beam", tested_b, "keeps", len(hits),
          "verified", verified, "best",
          None if not best else (best["trigram_per_100"], best["gen"], best["head"][:40]),
          flush=True)


if __name__ == "__main__":
    main()
