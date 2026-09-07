#!/usr/bin/env python3
"""Two-square + slidefair; ink-density page keys; Ulysses/Quixote/Canterbury/Kafka skeleton."""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cicada.liber_primus.gematria import Gematria  # noqa: E402
from cicada.paths import ROOT as CICADA_ROOT  # noqa: E402
from cicada.scoring import score_candidate  # noqa: E402

GP = Gematria()
Q = 29
ROWS, COLS = 5, 6
PAGE_DIR = CICADA_ROOT / "corpus/normalized/rtkd_pages"
OUT = CICADA_ROOT / "experiments" / "EXP-LP-TWOSQUARE-INK-SKEL-001"
TRIAGE = CICADA_ROOT / "reports/candidates/image_triage.json"
CAS = CICADA_ROOT / "corpus/objects/sha256"


def find(pref: str) -> Path | None:
    xs = list((CAS / pref[:2]).glob(pref + "*"))
    return xs[0] if xs else None


def idxs_of(split: int) -> list[int]:
    return GP.rune_indices((PAGE_DIR / f"split_{split:03d}.txt").read_text(encoding="utf-8"))


def prefix(n: int = 900) -> list[int]:
    out: list[int] = []
    for s in range(15, 71):
        out.extend(idxs_of(s))
        if len(out) >= n:
            break
    return out[:n]


def keep(sc: dict, n: int) -> bool:
    return n >= 80 and sc["trigram_per_100"] >= 3.5 and 0.28 <= sc["vowelish_ratio"] <= 0.55 and sc["ioc"] >= 0.045


def grid(key: list[int]) -> list[int]:
    seen = set()
    cells: list[int] = []
    for x in key:
        x %= Q
        if x not in seen:
            seen.add(x)
            cells.append(x)
    for x in range(Q):
        if x not in seen:
            cells.append(x)
    cells.append(-1)
    return cells


def posmap(cells: list[int]) -> dict[int, tuple[int, int]]:
    return {v: divmod(i, COLS) for i, v in enumerate(cells) if v >= 0}


def twosquare_dec(ct: list[int], k1: list[int], k2: list[int]) -> list[int]:
    g1, g2 = grid(k1), grid(k2)
    p1, p2 = posmap(g1), posmap(g2)
    out: list[int] = []
    i = 0
    while i + 1 < len(ct):
        a, b = ct[i] % Q, ct[i + 1] % Q
        if a not in p1 or b not in p2:
            out.append(a)
            i += 1
            continue
        r1, c1 = p1[a]
        r2, c2 = p2[b]
        if r1 == r2:
            A = g1[r1 * COLS + (c1 - 1) % COLS]
            B = g2[r2 * COLS + (c2 - 1) % COLS]
        else:
            A = g1[r1 * COLS + c2]
            B = g2[r2 * COLS + c1]
        if A >= 0:
            out.append(A)
        if B >= 0:
            out.append(B)
        i += 2
    return out


def slidefair_dec(ct: list[int], key: list[int]) -> list[int]:
    """Playfair-like pair decrypt; second square rotated by key[i//2]."""
    base = grid([])
    pm0 = posmap(base)
    out: list[int] = []
    i = 0
    k = 0
    while i + 1 < len(ct):
        shift = key[k % len(key)] % Q
        cells = [(x + shift) % Q if x >= 0 else -1 for x in base]
        # last cell unused stays
        cells[-1] = -1
        pm = posmap(cells)
        a, b = ct[i] % Q, ct[i + 1] % Q
        if a not in pm or b not in pm:
            out.append(a)
            i += 1
            continue
        r1, c1 = pm[a]
        r2, c2 = pm[b]
        if r1 == r2:
            A = cells[r1 * COLS + (c1 - 1) % COLS]
            B = cells[r2 * COLS + (c2 - 1) % COLS]
        elif c1 == c2:
            A = cells[((r1 - 1) % ROWS) * COLS + c1]
            B = cells[((r2 - 1) % ROWS) * COLS + c2]
        else:
            A = cells[r1 * COLS + c2]
            B = cells[r2 * COLS + c1]
        if A >= 0:
            out.append(A)
        if B >= 0:
            out.append(B)
        i += 2
        k += 1
    return out


def word_lens_runes(text: str) -> list[int]:
    words, cur = [], []
    for tok in GP.tokenize(text):
        if tok.kind == "rune":
            cur.append(tok.raw)
        elif tok.kind in {"sep", "punct", "layout"} and cur:
            words.append(len(cur))
            cur = []
    if cur:
        words.append(len(cur))
    return words


def word_lens_latin(s: str) -> list[int]:
    out = []
    for w in re.findall(r"[A-Za-z]+", s.upper()):
        try:
            ix = GP.encode_latin_key(w)
        except ValueError:
            continue
        if ix:
            out.append(len(ix))
    return out


def longest_run(needle: list[int], hay: list[int]) -> tuple[int, int | None]:
    best, pos = 0, None
    if len(needle) < 4 or len(hay) < 4:
        return 0, None
    for i in range(len(hay) - 3):
        r = 0
        while r < len(needle) and i + r < len(hay) and needle[r] == hay[i + r]:
            r += 1
        if r > best:
            best, pos = r, i
            if best == len(needle):
                break
    return best, pos


def object_path(sha: str) -> Path:
    return CAS / sha[:2] / sha


def ink_key(path: Path, n: int) -> list[int]:
    """Row-band ink totals in the text column, tiled to n, as %29."""
    arr = np.asarray(Image.open(path).convert("RGB"))
    ink = arr.sum(axis=2) < 400
    col = ink[:, 500:1800].sum(axis=1)
    # 40px bands
    bands = [int(col[i : i + 40].sum()) % 29 for i in range(600, 3000, 40)]
    if not bands:
        return [0] * n
    return [bands[i % len(bands)] for i in range(n)]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    words = [
        "DIVINITY",
        "FIRFUMFERENFE",
        "INSTAR",
        "CIRCUMFERENCE",
        "PILGRIM",
        "PRIMES",
        "CICADA",
        "ANEND",
        "PARABLE",
        "WELCOME",
        "KOAN",
    ]
    keys = []
    for w in words:
        try:
            keys.append((w, GP.encode_latin_key(w)))
        except ValueError:
            pass
    keys.append(("seq", list(range(29))))
    ct = prefix(900)
    sec = idxs_of(15) + idxs_of(16) + idxs_of(17)
    hits = []
    tested = 0
    for label, stream in (("p900", ct), ("sec02", sec)):
        for i, (n1, k1) in enumerate(keys):
            for n2, k2 in keys[i:]:
                tested += 1
                pt = twosquare_dec(stream, k1, k2)
                lat = GP.latin_stream(pt)
                sc = score_candidate(pt, lat)
                if n1 == "DIVINITY" and n2 == "INSTAR":
                    print(f"2sq {label} {n1}/{n2} tri={sc['trigram_per_100']:.2f} ioc={sc['ioc']:.3f} {lat[:44]}")
                if keep(sc, len(pt)):
                    hits.append({"cipher": "twosquare", "span": label, "k1": n1, "k2": n2, "head": lat[:80], **sc})
        for n1, k1 in keys:
            tested += 1
            pt = slidefair_dec(stream, k1)
            lat = GP.latin_stream(pt)
            sc = score_candidate(pt, lat)
            if n1 == "DIVINITY":
                print(f"sld {label} {n1:16s} tri={sc['trigram_per_100']:.2f} ioc={sc['ioc']:.3f} {lat[:44]}")
            if keep(sc, len(pt)):
                hits.append({"cipher": "slidefair", "span": label, "k": n1, "head": lat[:80], **sc})
    print("pair ciphers tested", tested, "hits", len(hits))

    # skeletons
    pages = {s: word_lens_runes((PAGE_DIR / f"split_{s:03d}.txt").read_text(encoding="utf-8")) for s in range(15, 71)}
    hays = {}
    for name, pref, cap in (
        ("ulysses", "d432d18d2535a28e", 350000),
        ("quixote", "69ef241e632ef4fb", 350000),
        ("canterbury", "433661fd210e0351", 350000),
        ("kafka_meta", "c9f7245e700dc729", None),
    ):
        p = find(pref)
        if not p:
            print("missing", name)
            continue
        raw = p.read_text(encoding="utf-8", errors="replace")
        hays[name] = word_lens_latin(raw if cap is None else raw[:cap])
        print("hay", name, len(hays[name]))
    skel = []
    bests = []
    for s, needle in pages.items():
        if len(needle) < 8:
            continue
        for hid, hay in hays.items():
            best, pos = longest_run(needle, hay)
            bests.append((best, s, hid, pos, len(needle)))
            if best >= 10:
                skel.append({"split": s, "hay": hid, "run": best, "pos": pos, "needle_n": len(needle)})
                print("SKEL", skel[-1])
    bests.sort(reverse=True)
    print("skel top", bests[:10], "keeps>=10", len(skel))

    # ink-density keys
    triage = {x["url"].rsplit("/", 1)[-1]: x for x in json.loads(TRIAGE.read_text()) if "unsolved" in x["url"]}
    ink_hits = []
    ink_tested = 0
    for onion in range(0, 56):
        ix = idxs_of(15 + onion)
        if len(ix) < 80:
            continue
        path = object_path(triage[f"{onion}.jpg"]["sha256"])
        ks = ink_key(path, len(ix))
        for rel in ("sub", "add"):
            ink_tested += 1
            if rel == "sub":
                out = [(ix[i] - ks[i]) % 29 for i in range(len(ix))]
            else:
                out = [(ix[i] + ks[i]) % 29 for i in range(len(ix))]
            lat = GP.latin_stream(out)
            sc = score_candidate(out, lat)
            if onion < 3:
                print(f"ink {onion:02d} {rel} tri={sc['trigram_per_100']:.2f} ioc={sc['ioc']:.3f} {lat[:40]}")
            if keep(sc, len(ix)):
                ink_hits.append({"onion": onion, "rel": rel, "head": lat[:80], **sc})
    print("ink tested", ink_tested, "hits", len(ink_hits))

    (OUT / "result.json").write_text(
        json.dumps(
            {
                "pair_tested": tested,
                "pair_hits": hits,
                "skel_keeps": skel,
                "skel_top": [{"run": r, "split": s, "hay": h, "pos": p, "needle_n": n} for r, s, h, p, n in bests[:15]],
                "hay_n": {k: len(v) for k, v in hays.items()},
                "ink_tested": ink_tested,
                "ink_hits": ink_hits,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
