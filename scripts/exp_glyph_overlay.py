#!/usr/bin/env python3
"""Segment ink glyphs on LP2 JPEGs and label each red vs black.

Validated against page 56 (first 5 body runes red = AN END) and page 57
(first 7 red = PARABLE) before trusting unsolved heading lengths.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cicada.liber_primus.ciphers import (  # noqa: E402
    atbash,
    caesar,
    totient_prime_stream,
    totient_skip_ciphertext_f_ordinal,
    vigenere_decrypt,
)
from cicada.liber_primus.gematria import Gematria  # noqa: E402
from cicada.paths import ROOT as CICADA_ROOT  # noqa: E402
from cicada.scoring import score_candidate  # noqa: E402

GP = Gematria()
PAGE_DIR = CICADA_ROOT / "corpus/normalized/rtkd_pages"
OUT = CICADA_ROOT / "experiments" / "EXP-LP-GLYPH-OVERLAY-001"
TRIAGE = CICADA_ROOT / "reports/candidates/image_triage.json"


def object_path(sha: str) -> Path:
    return CICADA_ROOT / "corpus/objects/sha256" / sha[:2] / sha


def _runs(mask_1d: np.ndarray, min_len: int) -> list[tuple[int, int]]:
    out = []
    i = 0
    n = len(mask_1d)
    while i < n:
        if not mask_1d[i]:
            i += 1
            continue
        j = i + 1
        while j < n and mask_1d[j]:
            j += 1
        if j - i >= min_len:
            out.append((i, j))
        i = j
    return out


def segment(path: Path) -> dict:
    im = Image.open(path).convert("RGB")
    # half-res is enough for color+box; 1200x1800
    arr = np.asarray(im.resize((im.width // 2, im.height // 2), Image.BILINEAR))
    r = arr[:, :, 0].astype(np.int16)
    g = arr[:, :, 1].astype(np.int16)
    b = arr[:, :, 2].astype(np.int16)
    ink = (r + g + b) < 420
    red = (r - np.maximum(g, b)) > 40
    # text column: drop outer margins
    col0, col1 = 280, 900
    ink_c = ink[:, col0:col1]
    row_occ = ink_c.mean(axis=1) > 0.01
    line_bands = _runs(row_occ, min_len=8)
    lines = []
    for y0, y1 in line_bands:
        band = ink_c[y0:y1]
        col_occ = band.mean(axis=0) > 0.04
        glyphs = _runs(col_occ, min_len=3)
        row = []
        for x0, x1 in glyphs:
            sl_ink = ink[y0:y1, col0 + x0 : col0 + x1]
            sl_red = red[y0:y1, col0 + x0 : col0 + x1]
            n = int(sl_ink.sum()) or 1
            rf = float((sl_red & sl_ink).sum() / n)
            w = x1 - x0
            h = y1 - y0
            if n < 12 or w < 3:
                continue
            # separators (dots) are short and nearly square-small
            if w <= 6 and h <= 14 and n < 40:
                continue
            row.append(
                {
                    "x0": col0 + x0,
                    "y0": y0,
                    "x1": col0 + x1,
                    "y1": y1,
                    "px": n,
                    "red_frac": rf,
                    "is_red": rf >= 0.30,
                    "cx": col0 + (x0 + x1) / 2,
                    "cy": (y0 + y1) / 2,
                }
            )
        if row:
            lines.append(row)
    ordered = [b for line in lines for b in line]
    return {
        "n_ink_cc": sum(len(L) for L in lines),
        "n_runeish": len(ordered),
        "n_red": sum(1 for b in ordered if b["is_red"]),
        "red_runs": _red_runs(ordered),
        "line_counts": [len(L) for L in lines],
        "ordered_red": [int(b["is_red"]) for b in ordered],
    }


def _red_runs(ordered):
    runs = []
    i = 0
    while i < len(ordered):
        if not ordered[i]["is_red"]:
            i += 1
            continue
        j = i
        while j < len(ordered) and ordered[j]["is_red"]:
            j += 1
        runs.append({"start": i, "len": j - i})
        i = j
    return runs


def page_ix(onion: int) -> list[int]:
    return GP.rune_indices((PAGE_DIR / f"split_{15 + onion:03d}.txt").read_text(encoding="utf-8"))


def attack_span(onion: int, start: int, n: int) -> list[dict]:
    ix = page_ix(onion)
    if start + n > len(ix) or n < 4:
        return []
    ct = ix[start : start + n]
    body = ix[:start] + ix[start + n :]
    # remaining pages in a guessed section: just this page body for now
    hits = []
    plains = [
        ("direct", ct),
        ("atbash", atbash(ct)),
        ("atb3", caesar(atbash(ct), 3)),
        ("tot", totient_prime_stream(ct)),
        ("tot4", totient_skip_ciphertext_f_ordinal(ct, 4)),
    ]
    for s in range(29):
        plains.append((f"c{s}", caesar(ct, s)))
        plains.append((f"ac{s}", caesar(atbash(ct), s)))
    vocab = (
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
    )
    for name, pt in plains:
        latin = GP.latin_stream(pt)
        rec = {"onion": onion, "start": start, "n": n, "method": name, "latin": latin}
        if any(latin.startswith(v) or v in latin for v in vocab):
            rec["vocab"] = True
            hits.append(rec)
        if body and 4 <= n <= 20:
            out = vigenere_decrypt(body, pt, skip_plaintext_f=True)
            sc = score_candidate(out, GP.latin_stream(out))
            if sc["trigram_per_100"] >= 3.5 and sc["ioc"] >= 0.045:
                rec = {**rec, "body_key": True, **sc, "body_head": GP.latin_stream(out)[:80]}
                hits.append(rec)
    return hits


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    triage = {item["url"].rsplit("/", 1)[-1]: item for item in json.loads(TRIAGE.read_text()) if "unsolved" in item["url"]}
    # controls + pages with substantial red
    targets = [0, 3, 6, 7, 8, 15, 23, 27, 33, 39, 40, 53, 54, 56, 57]
    reports = []
    hits = []
    for onion in targets:
        name = f"{onion}.jpg"
        item = triage[name]
        path = object_path(item["sha256"])
        seg = segment(path)
        n_trans = len(page_ix(onion)) if onion <= 55 else (
            85 if onion == 56 else 95
        )
        # page 56/57 are splits 71/72
        if onion >= 56:
            n_trans = len(GP.rune_indices((PAGE_DIR / f"split_{15 + onion:03d}.txt").read_text(encoding="utf-8")))
        rec = {
            "onion": onion,
            "trans_runes": n_trans,
            **{k: seg[k] for k in ("n_ink_cc", "n_runeish", "n_red", "red_runs", "line_counts")},
        }
        reports.append(rec)
        print(
            f"{onion:2d} trans={n_trans:4d} cc={seg['n_runeish']:4d} red={seg['n_red']:3d} "
            f"runs={seg['red_runs'][:6]} lines={seg['line_counts'][:8]}"
        )
        # attack longest red run if it looks like a heading (4-34) or the p53 tail
        for run in seg["red_runs"]:
            if 4 <= run["len"] <= 60:
                hits.extend(attack_span(onion, run["start"], run["len"]))

    (OUT / "overlay.json").write_text(json.dumps(reports, indent=2) + "\n", encoding="utf-8")
    (OUT / "hits.json").write_text(json.dumps(hits, indent=2) + "\n", encoding="utf-8")
    print("overlay hits", len(hits))
    for h in hits[:20]:
        print(" ", h)


if __name__ == "__main__":
    main()
