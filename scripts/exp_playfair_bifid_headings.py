#!/usr/bin/env python3
"""Playfair/Bifid (non-additive) on unsolved runes + drop-cap-aware heading lengths.

Heading segmenter: hex bands (~65px) dropped; tall drop-cap bands split into
~115px body rows; leftmost tall red box counted as rune 0.
Controls: onion 56 → 85 runes / first 5 red; onion 57 → 95 / first 7 red.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cicada.liber_primus.ciphers import atbash, caesar  # noqa: E402
from cicada.liber_primus.gematria import Gematria  # noqa: E402
from cicada.paths import ROOT as CICADA_ROOT  # noqa: E402
from cicada.scoring import score_candidate  # noqa: E402

GP = Gematria()
Q = 29
PAGE_DIR = CICADA_ROOT / "corpus/normalized/rtkd_pages"
OUT = CICADA_ROOT / "experiments" / "EXP-LP-PLAYFAIR-BIFID-HEADING-001"
TRIAGE = CICADA_ROOT / "reports/candidates/image_triage.json"
ROWS, COLS = 5, 6  # 30 cells; last cell unused


def object_path(sha: str) -> Path:
    return CICADA_ROOT / "corpus/objects/sha256" / sha[:2] / sha


def idxs_of(split: int) -> list[int]:
    return GP.rune_indices((PAGE_DIR / f"split_{split:03d}.txt").read_text(encoding="utf-8"))


def keep(sc: dict, n: int) -> bool:
    return (
        n >= 80
        and sc["trigram_per_100"] >= 3.5
        and 0.28 <= sc["vowelish_ratio"] <= 0.55
        and sc["ioc"] >= 0.045
    )


def build_grid(key: list[int]) -> list[int]:
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
    cells.append(-1)  # unused
    assert len(cells) == 30
    return cells


def pos_map(cells: list[int]) -> dict[int, tuple[int, int]]:
    m = {}
    for i, v in enumerate(cells):
        if v >= 0:
            m[v] = divmod(i, COLS)
    return m


def playfair_decrypt(ct: list[int], key: list[int]) -> list[int]:
    cells = build_grid(key)
    pos = pos_map(cells)
    out: list[int] = []
    i = 0
    n = len(ct)
    while i < n - 1:
        a, b = ct[i] % Q, ct[i + 1] % Q
        if a == b:
            # no filler convention known; leave pair and advance 1
            out.append(a)
            i += 1
            continue
        r1, c1 = pos[a]
        r2, c2 = pos[b]
        if r1 == r2:
            out.append(cells[r1 * COLS + (c1 - 1) % COLS])
            out.append(cells[r2 * COLS + (c2 - 1) % COLS])
        elif c1 == c2:
            out.append(cells[((r1 - 1) % ROWS) * COLS + c1])
            out.append(cells[((r2 - 1) % ROWS) * COLS + c2])
        else:
            out.append(cells[r1 * COLS + c2])
            out.append(cells[r2 * COLS + c1])
        i += 2
    if i < n:
        out.append(ct[-1] % Q)
    return [x for x in out if x >= 0]


def bifid_decrypt(ct: list[int], key: list[int], period: int) -> list[int]:
    cells = build_grid(key)
    pos = pos_map(cells)
    out: list[int] = []
    for start in range(0, len(ct), period):
        block = [x % Q for x in ct[start : start + period]]
        coords = []
        for x in block:
            r, c = pos[x]
            coords.append(r)
            coords.append(c)
        half = len(block)
        # encrypt wrote rows then cols; decrypt interleaves
        rows, cols_ = coords[:half], coords[half:]
        for r, c in zip(rows, cols_):
            if not (0 <= r < ROWS and 0 <= c < COLS):
                continue
            val = cells[r * COLS + c]
            if val >= 0:
                out.append(val)
    return out


def _runs(mask: np.ndarray, min_len: int) -> list[tuple[int, int]]:
    out = []
    i = 0
    n = len(mask)
    while i < n:
        if not mask[i]:
            i += 1
            continue
        j = i + 1
        while j < n and mask[j]:
            j += 1
        if j - i >= min_len:
            out.append((i, j))
        i = j
    return out


def segment_page(path: Path) -> dict:
    im = Image.open(path).convert("RGB")
    arr = np.asarray(im)
    r = arr[:, :, 0].astype(np.int16)
    g = arr[:, :, 1].astype(np.int16)
    b = arr[:, :, 2].astype(np.int16)
    ink = (r + g + b) < 400
    red = (r - np.maximum(g, b)) > 40
    col0, col1 = 400, 1850
    row_occ = ink[:, col0:col1].mean(axis=1) > 0.015
    bands = _runs(row_occ, min_len=40)
    glyphs = []
    line_counts = []
    for y0, y1 in bands:
        h = y1 - y0
        if h < 90:
            continue  # hex (~65) and stipple crumbs
        if h > 200:
            # drop-cap fused block: left tall red = one rune; split remainder into ~115 rows
            left = ink[y0:y1, col0 : col0 + 220]
            if left.mean() > 0.02:
                sl = ink[y0:y1, col0 : col0 + 220]
                rd = red[y0:y1, col0 : col0 + 220]
                n = int(sl.sum()) or 1
                rf = float((rd & sl).sum() / n)
                glyphs.append({"is_red": rf >= 0.25, "kind": "drop", "rf": rf})
            inner0 = col0 + 160
            sub = ink[y0:y1, inner0:col1].mean(axis=1) > 0.02
            for sy0, sy1 in _runs(sub, min_len=50):
                if (sy1 - sy0) < 70:
                    continue
                row = _line_glyphs(ink, red, y0 + sy0, y0 + sy1, inner0, col1)
                glyphs.extend(row)
                if row:
                    line_counts.append(len(row))
        else:
            row = _line_glyphs(ink, red, y0, y1, col0, col1)
            glyphs.extend(row)
            if row:
                line_counts.append(len(row))
    red_runs = []
    i = 0
    while i < len(glyphs):
        if not glyphs[i]["is_red"]:
            i += 1
            continue
        j = i
        while j < len(glyphs) and glyphs[j]["is_red"]:
            j += 1
        red_runs.append({"start": i, "len": j - i})
        i = j
    return {
        "n": len(glyphs),
        "n_red": sum(1 for g in glyphs if g["is_red"]),
        "red_runs": red_runs,
        "line_counts": line_counts,
    }


def _line_glyphs(ink, red, y0, y1, x0, x1) -> list[dict]:
    col = ink[y0:y1, x0:x1].mean(axis=0) > 0.07
    boxes = _runs(col, min_len=6)
    out = []
    for a, b in boxes:
        w = b - a
        sl = ink[y0:y1, x0 + a : x0 + b]
        n = int(sl.sum())
        if n < 80:
            continue
        if w <= 16 and n < 200:
            continue  # word-separator dots
        ih = int(sl.any(axis=1).sum())
        if ih < 55:
            continue
        rd = red[y0:y1, x0 + a : x0 + b]
        rf = float((rd & sl).sum() / max(n, 1))
        out.append({"is_red": rf >= 0.25, "kind": "rune", "w": w, "rf": rf})
    return out


HEADING_VOCAB = (
    "ANEND",
    "PARABLE",
    "AWARNING",
    "WELCOME",
    "AKOAN",
    "SOMEWISDOM",
    "KNOWTHIS",
    "ANINSTRUCTION",
    "THELOSSOFDIVINITY",
    "PRESERVATION",
    "ADHERENCE",
    "CONSUMPTION",
    "FORALLISSACRED",
    "COMMANDYOUROWNSELF",
    "AWISDOM",
    "WISDOM",
)


def attack_heading(onion: int, n: int) -> list[dict]:
    if onion > 55 or n < 3:
        return []
    ix = idxs_of(15 + onion)
    if n > len(ix):
        return []
    ct = ix[:n]
    hits = []
    plains = [("direct", ct), ("atbash", atbash(ct))]
    for s in range(29):
        plains.append((f"c{s}", caesar(ct, s)))
        plains.append((f"ac{s}", caesar(atbash(ct), s)))
    for name, pt in plains:
        latin = GP.latin_stream(pt)
        if any(latin == v or latin.startswith(v) for v in HEADING_VOCAB):
            hits.append({"onion": onion, "n": n, "method": name, "latin": latin})
    return hits


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    triage = {
        x["url"].rsplit("/", 1)[-1]: x
        for x in json.loads(TRIAGE.read_text())
        if "unsolved" in x["url"]
    }

    # --- headings ---
    heading_pages = [0, 3, 6, 7, 8, 15, 23, 27, 33, 39, 40, 53, 54, 56, 57]
    overlays = []
    heading_hits = []
    for onion in heading_pages:
        path = object_path(triage[f"{onion}.jpg"]["sha256"])
        seg = segment_page(path)
        if onion <= 55:
            n_trans = len(idxs_of(15 + onion))
        else:
            n_trans = 85 if onion == 56 else 95
        rec = {"onion": onion, "trans": n_trans, **seg}
        overlays.append(rec)
        fr = seg["red_runs"][0]["len"] if seg["red_runs"] else 0
        print(
            f"glyph {onion:2d} trans={n_trans:4d} cc={seg['n']:4d} red={seg['n_red']:3d} "
            f"first_red={fr} lines={seg['line_counts'][:12]}"
        )
        if onion <= 55:
            for run in seg["red_runs"]:
                if 3 <= run["len"] <= 34 and run["start"] <= 1:
                    heading_hits.extend(attack_heading(onion, run["len"]))

    controls = {
        "p57_n": next(o["n"] for o in overlays if o["onion"] == 57),
        "p57_first_red": (next(o for o in overlays if o["onion"] == 57)["red_runs"] or [{"len": 0}])[0]["len"],
        "p56_n": next(o["n"] for o in overlays if o["onion"] == 56),
        "p56_first_red": (next(o for o in overlays if o["onion"] == 56)["red_runs"] or [{"len": 0}])[0]["len"],
    }
    controls["p57_ok"] = abs(controls["p57_n"] - 95) <= 6 and controls["p57_first_red"] == 7
    controls["p56_ok"] = abs(controls["p56_n"] - 85) <= 6 and controls["p56_first_red"] == 5
    print("controls", controls)
    print("heading vocab", heading_hits)

    # --- Playfair / Bifid ---
    key_words = [
        "DIVINITY",
        "FIRFUMFERENFE",
        "INSTAR",
        "CIRCUMFERENCE",
        "PILGRIM",
        "PRIMES",
        "CICADA",
        "LIBERPRIMUS",
        "ANEND",
        "PARABLE",
        "WELCOME",
        "AWARNING",
        "SOMEWISDOM",
        "KNOWTHIS",
        "THELOSSOFDIVINITY",
        "PRESERVATION",
        "ADHERENCE",
        "CONSUMPTION",
        "3301",
        "KOAN",
        "ENLIGHTENMENT",
        "DEEPWEB",
        "TOTIENT",
        "PHI",
    ]
    keys = []
    for w in key_words:
        try:
            keys.append((w, GP.encode_latin_key(w)))
        except ValueError:
            pass
    # identity / sequential
    keys.append(("seq", list(range(29))))
    keys.append(("atbash_order", [(28 - i) for i in range(29)]))

    prefix = []
    for s in range(15, 71):
        prefix.extend(idxs_of(s))
        if len(prefix) >= 900:
            break
    prefix = prefix[:900]
    # also first unsolved section 0-2 (splits 15-17)
    sec02 = idxs_of(15) + idxs_of(16) + idxs_of(17)

    hits = []
    tested = 0
    for label, ct in (("prefix900", prefix), ("sec0-2", sec02)):
        for kn, key in keys:
            tested += 1
            pt = playfair_decrypt(ct, key)
            latin = GP.latin_stream(pt)
            sc = score_candidate(pt, latin)
            print(f"pf {label:10s} {kn:20s} tri={sc['trigram_per_100']:.2f} ioc={sc['ioc']:.3f} {latin[:48]}")
            if keep(sc, len(pt)) or (sc["trigram_per_100"] >= 3.0 and sc["ioc"] >= 0.045 and len(pt) >= 80):
                hits.append({"cipher": "playfair", "span": label, "key": kn, "head": latin[:80], **sc})
            for per in (5, 10, 15, 29):
                tested += 1
                pt = bifid_decrypt(ct, key, per)
                latin = GP.latin_stream(pt)
                sc = score_candidate(pt, latin)
                if kn == keys[0][0] and per == 5:
                    print(f"bf{per} {label:10s} {kn:20s} tri={sc['trigram_per_100']:.2f} ioc={sc['ioc']:.3f} {latin[:48]}")
                if keep(sc, len(pt)) or (sc["trigram_per_100"] >= 3.0 and sc["ioc"] >= 0.045 and len(pt) >= 80):
                    hits.append({"cipher": f"bifid{per}", "span": label, "key": kn, "head": latin[:80], **sc})
                    print(f"HIT bf{per} {label:10s} {kn:20s} tri={sc['trigram_per_100']:.2f} {latin[:48]}")

    # page-local playfair with that page's own heading CT as key
    for onion in (0, 3, 8, 15, 23, 27, 33, 40, 54):
        ix = idxs_of(15 + onion)
        ov = next((o for o in overlays if o["onion"] == onion), None)
        n = 8
        if ov and ov["red_runs"] and 3 <= ov["red_runs"][0]["len"] <= 20:
            n = ov["red_runs"][0]["len"]
        key = ix[:n]
        body = ix[n:]
        if len(body) < 40:
            continue
        tested += 1
        pt = playfair_decrypt(body, key)
        latin = GP.latin_stream(pt)
        sc = score_candidate(pt, latin)
        print(f"pf page{onion:02d} headkey n={n} tri={sc['trigram_per_100']:.2f} ioc={sc['ioc']:.3f} {latin[:48]}")
        if keep(sc, len(pt)) or (sc["trigram_per_100"] >= 3.0 and sc["ioc"] >= 0.045):
            hits.append({"cipher": "playfair_headingkey", "onion": onion, "n": n, "head": latin[:80], **sc})

    print("tested", tested, "hits", len(hits))
    (OUT / "result.json").write_text(
        json.dumps(
            {
                "controls": controls,
                "overlays": overlays,
                "heading_hits": heading_hits,
                "tested": tested,
                "hits": hits,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
