#!/usr/bin/env python3
"""Bazeries cylinder-29 + Fleissner turning grille.

Quagmire I/III is closed (EXP-LP-GROMARK-QUAGMIRE-001). Columnar-then-totient
is closed per-word. This is the unused pair: independently mixed disks with a
fixed reading-row shift, and a 4-turn hole grille at page scale (not per-word).
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
OUT = CICADA_ROOT / "experiments" / "EXP-LP-BAZERIES-GRILLE-001"
WORDS = ("DIVINITY", "CICADA3301", "FIRFUMFERENFE", "ANEND", "LIBERPRIMUS", "TOTIENT", "PRIMES")


def key_idxs(word: str) -> list[int]:
    return GP.encode_latin_key(word)


def mixed_alpha(seed: list[int]) -> list[int]:
    seen: set[int] = set()
    out: list[int] = []
    for x in seed:
        x %= Q
        if x not in seen:
            seen.add(x)
            out.append(x)
    for x in range(Q):
        if x not in seen:
            out.append(x)
    return out


def disks_for(key: list[int]) -> list[list[int]]:
    """29 independently mixed disks (key + disk-index salt)."""
    return [mixed_alpha(key + [i, (i * 7 + 3) % Q]) for i in range(Q)]


def baz_enc(pt: list[int], key: list[int], shift: int) -> list[int]:
    disks = disks_for(key)
    period = key if key else [0]
    out = []
    for i, p in enumerate(pt):
        d = disks[period[i % len(period)] % Q]
        j = d.index(p)
        out.append(d[(j + shift) % Q])
    return out


def baz_dec(ct: list[int], key: list[int], shift: int) -> list[int]:
    disks = disks_for(key)
    period = key if key else [0]
    out = []
    for i, c in enumerate(ct):
        d = disks[period[i % len(period)] % Q]
        j = d.index(c)
        out.append(d[(j - shift) % Q])
    return out


def _rot(r: int, c: int, n: int, k: int) -> tuple[int, int]:
    for _ in range(k % 4):
        r, c = c, n - 1 - r
    return r, c


def fleissner_holes(n: int, key: list[int]) -> list[tuple[int, int]]:
    """One cell per 90° orbit, pick via key digits."""
    holes: list[tuple[int, int]] = []
    seen: set[frozenset] = set()
    ki = 0
    for r in range(n):
        for c in range(n):
            orbit = frozenset(
                (_rot(r, c, n, k) for k in range(4))
            )
            if orbit in seen:
                continue
            seen.add(orbit)
            opts = list(orbit)
            opts.sort()
            pick = opts[key[ki % len(key)] % 4]
            holes.append(pick)
            ki += 1
    return holes


def grille_enc(pt: list[int], n: int, holes: list[tuple[int, int]]) -> list[int]:
    grid = [[None] * n for _ in range(n)]
    i = 0
    for rot in range(4):
        cells = sorted(_rot(r, c, n, rot) for r, c in holes)
        for r, c in cells:
            grid[r][c] = pt[i] if i < len(pt) else 0
            i += 1
    return [grid[r][c] for r in range(n) for c in range(n)]


def grille_dec(ct: list[int], n: int, holes: list[tuple[int, int]]) -> list[int]:
    need = n * n
    if len(ct) < need:
        return []
    grid = [ct[r * n:(r + 1) * n] for r in range(n)]
    out: list[int] = []
    for rot in range(4):
        cells = sorted(_rot(r, c, n, rot) for r, c in holes)
        for r, c in cells:
            out.append(grid[r][c])
    return out


def even_orders(nrunes: int) -> list[int]:
    return [n for n in (8, 10, 12, 14, 16) if n * n <= nrunes]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    pt = GP.encode_latin_key(
        "THEPRIMESARESACREDTHETOTIENTFVNCTIANISSACREDALLTHNGSSHOVLDBEENCRYPTEDAWARNNGBELIEVENOTHNG"
    )
    k0 = key_idxs("DIVINITY")
    plants = {}
    for sh in (1, 5, 14):
        plants[f"baz_{sh}"] = baz_dec(baz_enc(pt, k0, sh), k0, sh) == pt
    plants["baz_wrong"] = baz_dec(baz_enc(pt, k0, 5), key_idxs("TOTIENT"), 5) != pt
    holes = fleissner_holes(10, k0)
    gpt = (pt * 4)[:100]
    plants["grille_10"] = grille_dec(grille_enc(gpt, 10, holes), 10, holes) == gpt
    plants["grille_wrong"] = grille_dec(
        grille_enc(gpt, 10, holes), 10, fleissner_holes(10, key_idxs("TOTIENT"))
    ) != gpt
    plants["ok"] = all(v is True for k, v in plants.items() if k != "ok")
    print("plant", plants, flush=True)
    if not plants["ok"]:
        (OUT / "result.json").write_text(json.dumps({
            "experiment": "EXP-LP-BAZERIES-GRILLE-001", "plant": plants,
            "verified_new_unsolved_runes": 0, "aborted": "plant failed",
        }, indent=2) + "\n")
        return

    targets = [("prefix400", prefix(400))]
    for s in range(15, 71):
        ct = idxs_of(s)
        if len(ct) >= 80:
            targets.append((f"split{s:03d}", ct))

    hits, tested, best = [], 0, None
    for word in WORDS:
        key = key_idxs(word)
        for tname, ct in targets:
            for sh in (1, 2, 3, 5, 7, 11, 14):
                tested += 1
                rec = baz_dec(ct, key, sh)
                lat = GP.latin_stream(rec)
                sc = score_candidate(rec, lat)
                row = {"family": "bazeries", "key": word, "add": f"s{sh}", "span": tname,
                       "head": lat[:80], **sc, "n": len(rec)}
                if best is None or sc["trigram_per_100"] > best["trigram_per_100"]:
                    best = row
                if keep(sc, len(rec)):
                    hits.append(row)
                    print("KEEP baz", word, sh, tname, sc["trigram_per_100"], lat[:40], flush=True)
            for n in even_orders(len(ct)):
                tested += 1
                rec = grille_dec(ct, n, fleissner_holes(n, key))
                if len(rec) < 64:
                    continue
                lat = GP.latin_stream(rec)
                sc = score_candidate(rec, lat)
                row = {"family": "grille", "key": word, "add": f"n{n}", "span": tname,
                       "head": lat[:80], **sc, "n": len(rec)}
                if best is None or sc["trigram_per_100"] > best["trigram_per_100"]:
                    best = row
                if keep(sc, len(rec)):
                    hits.append(row)
                    print("KEEP grille", word, n, tname, sc["trigram_per_100"], lat[:40], flush=True)

    result = {
        "experiment": "EXP-LP-BAZERIES-GRILLE-001",
        "family": "Bazeries cylinder-29 (independent disks) + Fleissner turning grille",
        "plant": plants,
        "tested": tested,
        "keep_bar_hits": len(hits),
        "keeps": hits[:12],
        "best": {k: best[k] for k in ("family", "key", "add", "span", "head", "trigram_per_100", "ioc")} if best else None,
        "skeptic_review": {
            "verdict": "null" if not hits else "keep-bar needs human English",
            "english": False,
        },
        "verified_new_unsolved_runes": 0,
        "note": "Quagmire already closed; disks here are independently mixed, not one mixed alphabet + periodic Caesar.",
    }
    (OUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print("tested", tested, "keeps", len(hits),
          "best", None if not best else (best["trigram_per_100"], best["family"], best["head"][:40]))


if __name__ == "__main__":
    main()
