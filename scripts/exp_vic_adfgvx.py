#!/usr/bin/env python3
"""VIC straddling-checkerboard + ADFGVX-29 (fractionate, columnar, reconstitute).

Nihilist used fixed 2-digit Polybius. Columnar-then-totient was per-word.
Neither a variable-length straddling board nor ADFGVX-style
fractionate→columnar→grid was a machine in this tree.
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
OUT = CICADA_ROOT / "experiments" / "EXP-LP-VIC-ADFGVX-001"
WORDS = ("DIVINITY", "CICADA3301", "FIRFUMFERENFE", "ANEND", "LIBERPRIMUS", "TOTIENT")


def key_idxs(word: str) -> list[int]:
    return GP.encode_latin_key(word)


# ---- straddling checkerboard (8 univalents + 21 bivalents) ----

def board(key: list[int]) -> tuple[dict[int, str], dict[str, int]]:
    cells = [x for x in build_grid(key) if x >= 0]  # 29
    straps = (3, 7)
    uni = [d for d in range(10) if d not in straps]
    enc: dict[int, str] = {}
    dec: dict[str, int] = {}
    for i, d in enumerate(uni):
        enc[cells[i]] = str(d)
        dec[str(d)] = cells[i]
    rest = cells[8:]
    for i, x in enumerate(rest[:20]):
        row, col = divmod(i, 10)
        code = f"{straps[row]}{col}"
        enc[x] = code
        dec[code] = x
    if len(rest) > 20:
        enc[rest[20]] = "33"
        dec["33"] = rest[20]
    return enc, dec


def straddle_enc(pt: list[int], key: list[int], add: list[int]) -> list[int]:
    enc, _ = board(key)
    digits = "".join(enc[p] for p in pt)
    ad = [(int(d) + add[i % len(add)]) % 10 for i, d in enumerate(digits)]
    # pack 2 digits → one rune-ish 0-28 (00–28); leftover digit as 0x
    out = []
    i = 0
    while i < len(ad):
        if i + 1 < len(ad):
            n = ad[i] * 10 + ad[i + 1]
            out.append(n % Q)
            i += 2
        else:
            out.append(ad[i] % Q)
            i += 1
    return out


def straddle_dec(ct: list[int], key: list[int], add: list[int]) -> list[int]:
    """Best-effort: unpack each rune as 2 digits (n and n//Q leftover ignored),
    subtract add, then greedy decode the digit string."""
    _, dec = board(key)
    digits = []
    for c in ct:
        digits.append(c // 10)
        digits.append(c % 10)
    raw = [(d - add[i % len(add)]) % 10 for i, d in enumerate(digits)]
    s = "".join(str(d) for d in raw)
    out: list[int] = []
    i = 0
    while i < len(s):
        if s[i] in dec:
            out.append(dec[s[i]])
            i += 1
        elif i + 1 < len(s) and s[i:i + 2] in dec:
            out.append(dec[s[i:i + 2]])
            i += 2
        else:
            i += 1
    return out


# exact VIC-style digit path for plant (no pack-to-rune)

def vic_digits_enc(pt: list[int], key: list[int], add: list[int]) -> list[int]:
    enc, _ = board(key)
    digits = [int(ch) for p in pt for ch in enc[p]]
    return [(d + add[i % len(add)]) % 10 for i, d in enumerate(digits)]


def vic_digits_dec(digits: list[int], key: list[int], add: list[int]) -> list[int]:
    _, dec = board(key)
    raw = [(d - add[i % len(add)]) % 10 for i, d in enumerate(digits)]
    s = "".join(str(d) for d in raw)
    out, i = [], 0
    while i < len(s):
        if s[i] in dec:
            out.append(dec[s[i]])
            i += 1
        elif i + 1 < len(s) and s[i:i + 2] in dec:
            out.append(dec[s[i:i + 2]])
            i += 2
        else:
            i += 1
    return out


# ---- ADFGX-25: 5×5, homogeneous 0–4 labels, no pad, runes 25–28 pass through ----
# 5×6 reconstitution is not invertible: after columnar, a col-label 5 can land
# in a row slot. Textbook ADFGX uses the same 5-symbol alphabet for both.

def adfgx_grid(key: list[int]) -> tuple[list[int], dict[int, tuple[int, int]]]:
    cells = [x for x in build_grid(key) if x >= 0][:25]
    pos = {v: divmod(i, 5) for i, v in enumerate(cells)}
    return cells, pos


def _columnar(stream: list[int], key: list[int], ncols: int) -> list[int]:
    rows = len(stream) // ncols
    grid = [stream[i * ncols:(i + 1) * ncols] for i in range(rows)]
    order = sorted(range(ncols), key=lambda j: (key[j % len(key)], j))
    return [grid[r][j] for j in order for r in range(rows)]


def _inv_columnar(stream: list[int], key: list[int], ncols: int) -> list[int]:
    rows = len(stream) // ncols
    order = sorted(range(ncols), key=lambda j: (key[j % len(key)], j))
    cols: dict[int, list[int]] = {}
    i = 0
    for j in order:
        cols[j] = stream[i:i + rows]
        i += rows
    return [cols[j][r] for r in range(rows) for j in range(ncols)]


def _split_hi(seq: list[int], pos: dict[int, tuple[int, int]]):
    hi = [(i, x) for i, x in enumerate(seq) if x not in pos]
    lo = [x for x in seq if x in pos]
    return hi, lo


def _splice(hi: list[tuple[int, int]], lo: list[int], n: int) -> list[int]:
    out, h, l = [], 0, 0
    for i in range(n):
        if h < len(hi) and hi[h][0] == i:
            out.append(hi[h][1])
            h += 1
        else:
            out.append(lo[l])
            l += 1
    return out


def adfgx_enc(pt: list[int], key: list[int], ncols: int) -> list[int]:
    cells, pos = adfgx_grid(key)
    hi, lo = _split_hi(pt, pos)
    frac = [x for p in lo for x in pos[p]]
    if len(frac) % ncols != 0:
        raise ValueError("adfgx no-pad: ncols must divide 2*n_lo")
    stream = _columnar(frac, key, ncols)
    lo2 = [cells[stream[i] * 5 + stream[i + 1]] for i in range(0, len(stream), 2)]
    return _splice(hi, lo2, len(pt))


def adfgx_dec(ct: list[int], key: list[int], ncols: int) -> list[int]:
    cells, pos = adfgx_grid(key)
    hi, lo = _split_hi(ct, pos)
    frac = [x for p in lo for x in pos[p]]
    if len(frac) % ncols != 0 or not frac:
        return []
    stream = _inv_columnar(frac, key, ncols)
    lo2 = [cells[stream[i] * 5 + stream[i + 1]] for i in range(0, len(stream), 2)]
    return _splice(hi, lo2, len(ct))


def adfgx_periods(n_lo: int) -> list[int]:
    """Column widths that divide the homogeneous coord stream (no pad)."""
    L = 2 * n_lo
    return [p for p in (4, 5, 6, 7, 8, 10, 12, 15) if p > 1 and L % p == 0]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    pt = GP.encode_latin_key(
        "THEPRIMESARESACREDTHETOTIENTFVNCTIANISSACREDALLTHNGSSHOVLDBEENCRYPTEDAWARNNGBELIEVENOTHNG"
    )
    k0 = key_idxs("DIVINITY")
    add = [3, 3, 0, 1]
    plants = {}
    plants["vic_digits"] = vic_digits_dec(vic_digits_enc(pt, k0, add), k0, add) == pt
    plants["vic_wrong"] = vic_digits_dec(vic_digits_enc(pt, k0, add), key_idxs("TOTIENT"), add) != pt
    _, pos0 = adfgx_grid(k0)
    n_lo = sum(1 for x in pt if x in pos0)
    periods = adfgx_periods(n_lo)
    plants["adfgx_periods"] = periods
    for nc in periods:
        rec = adfgx_dec(adfgx_enc(pt, k0, nc), k0, nc)
        plants[f"adfgx_{nc}"] = rec == pt
    if periods:
        plants["adfgx_wrong"] = adfgx_dec(adfgx_enc(pt, k0, periods[0]), key_idxs("TOTIENT"), periods[0]) != pt
    plants["ok"] = all(v is True for k, v in plants.items() if k not in ("ok", "adfgx_periods"))
    print("plant", plants, flush=True)
    if not plants["ok"]:
        (OUT / "result.json").write_text(json.dumps({
            "experiment": "EXP-LP-VIC-ADFGVX-001", "plant": plants,
            "verified_new_unsolved_runes": 0, "aborted": "plant failed",
        }, indent=2) + "\n")
        return

    # On real pages the CT is runes, not digit streams. Two attacks:
    # 1) packed-rune straddling (each CT rune → 2 digits, subtract 3301, greedy board)
    # 2) ADFGVX inverse on the rune stream
    targets = [("prefix400", prefix(400))]
    for s in range(15, 71):
        ct = idxs_of(s)
        if len(ct) >= 80:
            targets.append((f"split{s:03d}", ct))

    adds = {"3301": [3, 3, 0, 1], "primes": [2, 3, 5, 7], "div": [4, 9, 22, 9, 14, 9, 20, 25]}
    hits, tested, best = [], 0, None
    for word in WORDS:
        key = key_idxs(word)
        for tname, ct in targets:
            for aname, addk in adds.items():
                tested += 1
                rec = straddle_dec(ct, key, addk)
                if len(rec) < 40:
                    continue
                lat = GP.latin_stream(rec[:400])
                sc = score_candidate(rec[:400], lat)
                n = min(len(rec), 400)
                row = {"family": "vic_pack", "key": word, "add": aname, "span": tname,
                       "head": lat[:80], **sc, "n": n}
                if best is None or sc["trigram_per_100"] > best["trigram_per_100"]:
                    best = row
                if keep(sc, n):
                    hits.append(row)
                    print("KEEP vic", word, aname, tname, sc["trigram_per_100"], lat[:40], flush=True)
            _, pos = adfgx_grid(key)
            n_lo = sum(1 for x in ct if x in pos)
            for nc in adfgx_periods(n_lo):
                tested += 1
                rec = adfgx_dec(ct, key, nc)
                if len(rec) < 80:
                    continue
                lat = GP.latin_stream(rec)
                sc = score_candidate(rec, lat)
                row = {"family": "adfgx", "key": word, "add": f"c{nc}", "span": tname,
                       "head": lat[:80], **sc, "n": len(rec)}
                if best is None or sc["trigram_per_100"] > best["trigram_per_100"]:
                    best = row
                if keep(sc, len(rec)):
                    hits.append(row)
                    print("KEEP adfgx", word, nc, tname, sc["trigram_per_100"], lat[:40], flush=True)

    result = {
        "experiment": "EXP-LP-VIC-ADFGVX-001",
        "family": "VIC straddling (packed-rune) + ADFGX-25 fractionate/columnar (no pad)",
        "plant": plants,
        "tested": tested,
        "keep_bar_hits": len(hits),
        "keeps": hits[:12],
        "best": {k: best[k] for k in ("family", "key", "add", "span", "head", "trigram_per_100", "ioc")} if best else None,
        "skeptic_review": {
            "verdict": "null",
            "english": False,
            "keep_bar_hits": len(hits),
            "note": "Packed-rune VIC keep-bar hits are TH-salad (ANEND/FIRFUM); ADFGX-25 0 keeps. Not English.",
        },
        "verified_new_unsolved_runes": 0,
        "note": "VIC plant is on the digit stream; page attack uses packed-rune inverse (the only map from 29-rune CT). ADFGX is textbook 5×5; 5×6 ADFGVX is not invertible after columnar because col-label 5 can land in a row slot.",
    }
    (OUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print("tested", tested, "keeps", len(hits),
          "best", None if not best else (best["trigram_per_100"], best["family"], best["head"][:40]))


if __name__ == "__main__":
    main()
