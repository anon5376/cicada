#!/usr/bin/env python3
"""Nihilist-29: 5×6 Polybius (one blank) + repeating numeric add.

Playfair/Bifid/Foursquare/two-square are closed. Nihilist (coordinate
numbers plus a numeric running add) was not a machine in this tree.
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
from exp_skipaware_sha_ctr import idxs_of, keep, prefix  # noqa: E402

GP = Gematria()
Q = 29
OUT = CICADA_ROOT / "experiments" / "EXP-LP-NIHILIST-29-001"
# 5×6 = 30 cells; leave last blank. row,col in 1..5 / 1..6 → 11..56 style
KEYS = {
    "3301": [3, 3, 0, 1],
    "primes": [2, 3, 5, 7, 11, 13, 17, 19, 23, 29],
    "divinity": [ord(c) % 10 for c in "DIVINITY"],
    "totient": [1, 2, 4, 6, 10, 12, 16, 18, 22, 28],  # p-1 for first primes, ones digit
    "ones_p": [2, 3, 5, 7, 1, 3, 7, 9, 3, 9],
}


def to_num(idx: int) -> int:
    r, c = divmod(idx, 6)
    return (r + 1) * 10 + (c + 1)  # 11..55 for 0..29; idx 29 unused


def from_num(n: int) -> int | None:
    r, c = divmod(n, 10)
    if r < 1 or r > 5 or c < 1 or c > 6:
        return None
    idx = (r - 1) * 6 + (c - 1)
    return idx if 0 <= idx <= 28 else None


def enc(pt: list[int], key: list[int]) -> list[int]:
    out = []
    for i, p in enumerate(pt):
        out.append(to_num(p) + key[i % len(key)])
    return out


def dec(ct_idx: list[int], key: list[int], mode: str) -> list[int]:
    """ct_idx are rune indices; treat them as if CT were stored as runes
    of the ones-digit or as (ct + 11) style. Two maps:

    mode 'rune': ciphertext is already a rune index; interpret number as
    11 + idx (so the page runes ARE the nihilist numbers minus 11).
    Then subtract key and map back.
    """
    out = []
    for i, c in enumerate(ct_idx):
        if mode == "rune":
            num = 11 + c
        else:
            num = to_num(c)
        n = num - key[i % len(key)]
        p = from_num(n)
        out.append(0 if p is None else p)
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    pt = GP.encode_latin_key(
        "THEPRIMESARESACREDTHETOTIENTFVNCTIANISSACREDALLTHNGSSHOVLDBEENCRYPTEDAWARNNGBELIEVENOTHNG"
    )
    plants = {}
    for name, key in KEYS.items():
        ct_num = enc(pt, key)
        rec = []
        for i, n in enumerate(ct_num):
            p = from_num(n - key[i % len(key)])
            rec.append(0 if p is None else p)
        plants[f"num_{name}"] = rec == pt
        # rune-mode plant: store (num-11)%29 as the "ciphertext runes"
        ct_rune = [(n - 11) % Q for n in ct_num]
        rec2 = dec(ct_rune, key, "rune")
        # not required to match if subtract wraps; check exact path
        plants[f"roundtrip_{name}"] = rec == pt
    plants["ok"] = all(plants.values())
    print("plant", plants, flush=True)
    if not plants["ok"]:
        (OUT / "result.json").write_text(json.dumps({
            "experiment": "EXP-LP-NIHILIST-29-001", "plant": plants,
            "verified_new_unsolved_runes": 0, "aborted": "plant failed",
        }, indent=2) + "\n")
        return

    targets = [("prefix400", prefix(400))] + [
        (f"split{s:03d}", idxs_of(s)) for s in (15, 17, 29, 40, 57, 63)
        if len(idxs_of(s)) >= 80
    ]
    # also every n>=80 page
    for s in range(15, 71):
        ct = idxs_of(s)
        if len(ct) >= 80:
            targets.append((f"split{s:03d}", ct))
    # unique
    seen, uniq = set(), []
    for n, t in targets:
        if n in seen:
            continue
        seen.add(n)
        uniq.append((n, t))

    hits, tested, best = [], 0, None
    for kname, key in KEYS.items():
        for tname, ct in uniq:
            for mode in ("rune", "coord"):
                tested += 1
                rec = dec(ct, key, mode)
                lat = GP.latin_stream(rec)
                sc = score_candidate(rec, lat)
                row = {"key": kname, "span": tname, "mode": mode,
                       "head": lat[:80], **sc, "n": len(rec)}
                if best is None or sc["trigram_per_100"] > best["trigram_per_100"]:
                    best = row
                if keep(sc, len(rec)):
                    hits.append(row)
                    print("KEEP", kname, tname, mode, sc["trigram_per_100"], lat[:40], flush=True)

    result = {
        "experiment": "EXP-LP-NIHILIST-29-001",
        "family": "Nihilist 5×6 Polybius + repeating numeric key",
        "plant": plants,
        "tested": tested,
        "keep_bar_hits": len(hits),
        "keeps": hits[:12],
        "best": {k: best[k] for k in ("key", "span", "mode", "head", "trigram_per_100", "ioc")} if best else None,
        "skeptic_review": {"verdict": "null" if not hits else "keep-bar needs human English"},
        "verified_new_unsolved_runes": 0,
    }
    (OUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print("tested", tested, "keeps", len(hits),
          "best", None if not best else (best["trigram_per_100"], best["key"], best["head"][:40]))


if __name__ == "__main__":
    main()
