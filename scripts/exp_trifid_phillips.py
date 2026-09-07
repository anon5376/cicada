#!/usr/bin/env python3
"""Trifid-27 and Phillips-29 — unused Delastelle/Phillips siblings of Bifid/Playfair.

Bifid {5,10,15,29} and Playfair 5×6 are closed. Trifid (3×3×3, period groups)
and Phillips (5×6 square, row-shift every 5) were not machines in this tree.
Runes 27–28 (the two that do not fit a 27-cell cube) pass through unencrypted
and do not consume a period slot — same idea as an F-interrupter.
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
from exp_playfair_bifid_headings import build_grid  # noqa: E402
from exp_skipaware_sha_ctr import idxs_of, keep, prefix  # noqa: E402

GP = Gematria()
Q = 29
OUT = CICADA_ROOT / "experiments" / "EXP-LP-TRIFID-PHILLIPS-001"
KEY_WORDS = ("DIVINITY", "CICADA3301", "FIRFUMFERENFE", "ANEND", "LIBERPRIMUS", "TOTIENT", "WELCOME")
PERIODS = (3, 5, 7, 15)


def key_idxs(word: str) -> list[int]:
    return GP.encode_latin_key(word)


def cube27(key: list[int]) -> tuple[list[int], dict[int, tuple[int, int, int]]]:
    """27-cell cube from a keyed 29-alphabet (first 27 unique)."""
    cells = build_grid(key)[:27]
    pos = {}
    for i, v in enumerate(cells):
        if v >= 0:
            pos[v] = (i // 9, (i % 9) // 3, i % 3)
    return cells, pos


def trifid_enc(pt: list[int], key: list[int], period: int) -> list[int]:
    cells, pos = cube27(key)
    inv = {p: cells[p[0] * 9 + p[1] * 3 + p[2]] for p in pos.values()}
    out: list[int] = []
    buf: list[int] = []

    def flush(g: list[int]) -> None:
        if not g:
            return
        coords = [pos[x] for x in g]
        stream = [c for t in coords for c in t]  # L,R,C per letter
        # Delastelle: write all L, then all R, then all C, read by threes
        n = len(g)
        ls = [c[0] for c in coords]
        rs = [c[1] for c in coords]
        cs = [c[2] for c in coords]
        flat = ls + rs + cs
        for i in range(n):
            trip = (flat[3 * i], flat[3 * i + 1], flat[3 * i + 2])
            out.append(inv[trip])

    for x in pt:
        if x not in pos:
            flush(buf)
            buf = []
            out.append(x)
            continue
        buf.append(x)
        if len(buf) == period:
            flush(buf)
            buf = []
    flush(buf)
    return out


def trifid_dec(ct: list[int], key: list[int], period: int) -> list[int]:
    cells, pos = cube27(key)
    inv_pos = {cells[i]: (i // 9, (i % 9) // 3, i % 3) for i in range(27) if cells[i] >= 0}
    out: list[int] = []
    buf: list[int] = []

    def flush(g: list[int]) -> None:
        if not g:
            return
        n = len(g)
        coords = [inv_pos[x] for x in g]
        flat = [c for t in coords for c in t]
        # inverse of LLL...RRR...CCC... : the encrypt wrote ls+rs+cs then grouped by 3
        # decrypt: take each CT letter's (L,R,C), concatenate, split into 3 rows of n
        ls = flat[0:n]
        rs = flat[n:2 * n]
        cs = flat[2 * n:3 * n]
        # wait — encrypt produced CT from (ls+rs+cs) grouped by 3, so CT coords
        # ARE the regrouped stream. Reconstruct ls+rs+cs from CT coords:
        stream = [c for t in coords for c in t]
        ls, rs, cs = stream[0:n], stream[n:2 * n], stream[2 * n:3 * n]
        for i in range(n):
            idx = ls[i] * 9 + rs[i] * 3 + cs[i]
            out.append(cells[idx])

    for x in ct:
        if x not in inv_pos:
            flush(buf)
            buf = []
            out.append(x)
            continue
        buf.append(x)
        if len(buf) == period:
            flush(buf)
            buf = []
    flush(buf)
    return out


def shift_rows(cells: list[int], n_shifts: int, rows: int = 5, cols: int = 6) -> list[int]:
    grid = [cells[i * cols:(i + 1) * cols] for i in range(rows)]
    k = n_shifts % rows
    grid = grid[-k:] + grid[:-k] if k else grid
    return [v for row in grid for v in row]


def phillips_enc(pt: list[int], key: list[int], group: int = 5) -> list[int]:
    cells = build_grid(key)
    out = []
    for i, p in enumerate(pt):
        sq = shift_rows(cells, i // group)
        pos = {v: k for k, v in enumerate(sq) if v >= 0}
        if p not in pos:
            out.append(p)
            continue
        r, c = divmod(pos[p], 6)
        v = p
        for k in range(1, 6):
            cand = sq[((r + k) % 5) * 6 + c]
            if cand >= 0:
                v = cand
                break
        out.append(v)
    return out


def phillips_dec(ct: list[int], key: list[int], group: int = 5) -> list[int]:
    cells = build_grid(key)
    out = []
    for i, c in enumerate(ct):
        sq = shift_rows(cells, i // group)
        pos = {v: k for k, v in enumerate(sq) if v >= 0}
        if c not in pos:
            out.append(c)
            continue
        r, col = divmod(pos[c], 6)
        v = c
        for k in range(1, 6):
            cand = sq[((r - k) % 5) * 6 + col]
            if cand >= 0:
                v = cand
                break
        out.append(v)
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    pt = GP.encode_latin_key(
        "THEPRIMESARESACREDTHETOTIENTFVNCTIANISSACREDALLTHNGSSHOVLDBEENCRYPTEDAWARNNGBELIEVENOTHNG"
    )
    k0 = key_idxs("DIVINITY")
    plants = {}
    for per in PERIODS:
        ct = trifid_enc(pt, k0, per)
        rec = trifid_dec(ct, k0, per)
        plants[f"trifid_p{per}"] = rec == pt
    plants["trifid_wrong_period"] = trifid_dec(trifid_enc(pt, k0, 5), k0, 7) != pt
    ct = phillips_enc(pt, k0, 5)
    plants["phillips"] = phillips_dec(ct, k0, 5) == pt
    plants["phillips_wrong"] = phillips_dec(ct, key_idxs("TOTIENT"), 5) != pt
    plants["ok"] = all(v is True for k, v in plants.items() if k != "ok")
    print("plant", plants, flush=True)
    if not plants["ok"]:
        (OUT / "result.json").write_text(json.dumps({
            "experiment": "EXP-LP-TRIFID-PHILLIPS-001", "plant": plants,
            "verified_new_unsolved_runes": 0, "aborted": "plant failed",
        }, indent=2) + "\n")
        return

    targets = [("prefix400", prefix(400))]
    for s in range(15, 71):
        ct = idxs_of(s)
        if len(ct) >= 80:
            targets.append((f"split{s:03d}", ct))

    hits, tested, best = [], 0, None
    for word in KEY_WORDS:
        key = key_idxs(word)
        for tname, ct in targets:
            for per in PERIODS:
                tested += 1
                rec = trifid_dec(ct, key, per)
                lat = GP.latin_stream(rec)
                sc = score_candidate(rec, lat)
                row = {"family": "trifid", "key": word, "period": per, "span": tname,
                       "head": lat[:80], **sc, "n": len(rec)}
                if best is None or sc["trigram_per_100"] > best["trigram_per_100"]:
                    best = row
                if keep(sc, len(rec)):
                    hits.append(row)
                    print("KEEP trifid", word, per, tname, sc["trigram_per_100"], lat[:40], flush=True)
            for g in (5, 6):
                tested += 1
                rec = phillips_dec(ct, key, g)
                lat = GP.latin_stream(rec)
                sc = score_candidate(rec, lat)
                row = {"family": "phillips", "key": word, "period": g, "span": tname,
                       "head": lat[:80], **sc, "n": len(rec)}
                if best is None or sc["trigram_per_100"] > best["trigram_per_100"]:
                    best = row
                if keep(sc, len(rec)):
                    hits.append(row)
                    print("KEEP phillips", word, g, tname, sc["trigram_per_100"], lat[:40], flush=True)

    result = {
        "experiment": "EXP-LP-TRIFID-PHILLIPS-001",
        "family": "Trifid-27 (period 3/5/7/15) + Phillips-29 (group 5/6)",
        "plant": plants,
        "tested": tested,
        "keep_bar_hits": len(hits),
        "keeps": hits[:12],
        "best": {k: best[k] for k in ("family", "key", "period", "span", "head", "trigram_per_100", "ioc")} if best else None,
        "skeptic_review": {"verdict": "null" if not hits else "keep-bar needs human English"},
        "verified_new_unsolved_runes": 0,
    }
    (OUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print("tested", tested, "keeps", len(hits),
          "best", None if not best else (best["trigram_per_100"], best["family"], best["head"][:40]))


if __name__ == "__main__":
    main()
