#!/usr/bin/env python3
"""Align rtkd line rune-counts to image ink bands; color the first N glyphs
of each line. Control: 56.jpg first 5 of line 0 red; 57.jpg first 7 of line 0 red.
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
    vigenere_decrypt,
)
from cicada.liber_primus.gematria import Gematria  # noqa: E402
from cicada.paths import ROOT as CICADA_ROOT  # noqa: E402
from cicada.scoring import score_candidate  # noqa: E402

GP = Gematria()
PAGE_DIR = CICADA_ROOT / "corpus/normalized/rtkd_pages"
OUT = CICADA_ROOT / "experiments" / "EXP-LP-ALIGN-RED-001"
TRIAGE = CICADA_ROOT / "reports/candidates/image_triage.json"


def object_path(sha: str) -> Path:
    return CICADA_ROOT / "corpus/objects/sha256" / sha[:2] / sha


def trans_lines(onion: int) -> list[list[int]]:
    text = (PAGE_DIR / f"split_{15 + onion:03d}.txt").read_text(encoding="utf-8")
    lines: list[list[int]] = []
    cur: list[int] = []
    for tok in GP.tokenize(text):
        if tok.kind == "rune" and tok.index is not None:
            cur.append(tok.index)
        elif tok.kind == "break" and tok.raw == "/":
            if cur:
                lines.append(cur)
                cur = []
        elif tok.kind == "layout" and tok.raw == "&":
            if cur:
                lines.append(cur)
                cur = []
            # hex / ornament block: skip until next runes
    if cur:
        lines.append(cur)
    return [ln for ln in lines if ln]


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


def image_line_glyph_red(path: Path) -> list[list[float]]:
    """Per text-like ink band: redness of each x-gap glyph."""
    im = Image.open(path).convert("RGB")
    arr = np.asarray(im.resize((im.width // 2, im.height // 2), Image.BILINEAR))
    r, g, b = arr[:, :, 0].astype(np.int16), arr[:, :, 1].astype(np.int16), arr[:, :, 2].astype(np.int16)
    ink = (r + g + b) < 400
    red = (r - np.maximum(g, b)) > 40
    col0, col1 = 290, 880
    ink_c = ink[:, col0:col1]
    row_occ = ink_c.mean(axis=1) > 0.012
    bands = _runs(row_occ, min_len=10)
    # keep bands that look like text lines (height 12-40 at half-res ≈ 24-80 full px)
    bands = [(y0, y1) for y0, y1 in bands if 10 <= (y1 - y0) <= 45]
    lines = []
    for y0, y1 in bands:
        band = ink_c[y0:y1]
        col_occ = band.mean(axis=0) > 0.05
        glyphs = _runs(col_occ, min_len=2)
        reds = []
        for x0, x1 in glyphs:
            w = x1 - x0
            n_ink = int(ink[y0:y1, col0 + x0 : col0 + x1].sum())
            if n_ink < 10 or w <= 4:
                continue  # dots
            sl_red = red[y0:y1, col0 + x0 : col0 + x1]
            sl_ink = ink[y0:y1, col0 + x0 : col0 + x1]
            rf = float((sl_red & sl_ink).sum() / (int(sl_ink.sum()) or 1))
            reds.append(rf)
        if reds:
            lines.append(reds)
    return lines


def align(trans: list[list[int]], img_lines: list[list[float]]) -> dict:
    """Find a subsequence of image lines whose glyph counts match trans line lengths."""
    tlen = [len(ln) for ln in trans]
    ilen = [len(ln) for ln in img_lines]
    # sliding window
    for off in range(0, max(1, len(img_lines) - len(trans) + 1)):
        chunk = ilen[off : off + len(trans)]
        if len(chunk) < len(trans):
            break
        if chunk == tlen:
            return {"ok": True, "off": off, "tlen": tlen, "ilen": ilen, "match": "exact"}
        # allow ±1 on each line (separator leakage)
        if all(abs(a - b) <= 1 for a, b in zip(chunk, tlen)):
            return {"ok": True, "off": off, "tlen": tlen, "ilen": ilen, "match": "pm1", "chunk": chunk}
    return {"ok": False, "tlen": tlen, "ilen": ilen}


def heading_from_alignment(trans, img_lines, off: int) -> list[int] | None:
    """Take a prefix of line 0 while glyphs are red."""
    if off >= len(img_lines) or not trans:
        return None
    reds = img_lines[off]
    n = 0
    for rf in reds:
        if rf >= 0.30:
            n += 1
        else:
            break
    if n < 4:
        return None
    return trans[0][: min(n, len(trans[0]))]


def attack(ct: list[int], body: list[int]) -> list[dict]:
    hits = []
    plains = [
        ("direct", ct),
        ("atbash", atbash(ct)),
        ("atb3", caesar(atbash(ct), 3)),
        ("tot", totient_prime_stream(ct)),
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
        "THELOSS",
        "PRESERVATION",
        "ADHERENCE",
    )
    for name, pt in plains:
        latin = GP.latin_stream(pt)
        if any(latin.startswith(v) for v in vocab):
            hits.append({"kind": "vocab", "method": name, "latin": latin})
        if body and 4 <= len(pt) <= 24:
            out = vigenere_decrypt(body, pt, skip_plaintext_f=True)
            sc = score_candidate(out, GP.latin_stream(out))
            if sc["trigram_per_100"] >= 3.5 and sc["ioc"] >= 0.045:
                hits.append({"kind": "body", "method": name, "latin": latin, "head": GP.latin_stream(out)[:70], **sc})
    return hits


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    triage = {x["url"].rsplit("/", 1)[-1]: x for x in json.loads(TRIAGE.read_text()) if "unsolved" in x["url"]}
    targets = [0, 3, 8, 15, 23, 27, 33, 40, 53, 54, 56, 57]
    reports = []
    all_hits = []
    for onion in targets:
        path = object_path(triage[f"{onion}.jpg"]["sha256"])
        trans = trans_lines(onion)
        img = image_line_glyph_red(path)
        al = align(trans, img)
        rec = {"onion": onion, "n_trans_lines": len(trans), "n_img_lines": len(img), **al}
        # control checks
        if onion == 57 and img:
            rec["p57_line0_red_prefix"] = sum(1 for rf in img[al.get("off", 0)] if rf >= 0.30) if al.get("ok") else None
            rec["p57_expect"] = "first 7 of line 0 red"
        if onion == 56 and img:
            rec["p56_line0_red_prefix"] = None
            if al.get("ok"):
                rec["p56_line0_red_prefix"] = 0
                for rf in img[al["off"]]:
                    if rf >= 0.30:
                        rec["p56_line0_red_prefix"] += 1
                    else:
                        break
        reports.append(rec)
        print(
            f"{onion:2d} align={al.get('ok')} match={al.get('match')} "
            f"t={al.get('tlen')} i_n={len(img)} i0={img[0][:8] if img else None}..."
        )
        if al.get("ok"):
            h = heading_from_alignment(trans, img, al["off"])
            if h:
                body = [x for ln in trans for x in ln][len(h) :]
                hits = attack(h, body)
                rec["heading_n"] = len(h)
                rec["heading_latin_direct"] = GP.latin_stream(h)
                if hits:
                    all_hits.append({"onion": onion, "hits": hits})
                    print("  hits", hits)

    (OUT / "align.json").write_text(json.dumps(reports, indent=2) + "\n", encoding="utf-8")
    (OUT / "hits.json").write_text(json.dumps(all_hits, indent=2) + "\n", encoding="utf-8")
    print("done", "hits_pages", len(all_hits))


if __name__ == "__main__":
    main()
