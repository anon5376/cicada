#!/usr/bin/env python3
"""Line-class glyph overlay: keep rune-height bands, drop hex/art/dots.

GLYPH-OVERLAY-001 projected every ink column and counted p56 hex as runes
(203 vs 85). NCC drop-cap split still failed p56/57. This classifier uses
the measured ~114px rune-line height: bands much shorter are hex/dots;
the tall left red blob is one drop-cap; bottom stipple is dropped by y.

Controls that must pass before any heading is used as a key:
  onion 56: n_glyphs == 85 and first red-run length == 5  (AN END)
  onion 57: n_glyphs == 95 and first red-run length == 7  (PARABLE)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from cicada.liber_primus.ciphers import (  # noqa: E402
    atbash,
    caesar,
    totient_prime_stream,
    vigenere_decrypt,
)
from cicada.liber_primus.gematria import Gematria  # noqa: E402
from cicada.paths import ROOT as CICADA_ROOT  # noqa: E402
from cicada.scoring import score_candidate  # noqa: E402
from exp_skipaware_sha_ctr import keep  # noqa: E402

GP = Gematria()
Q = 29
OUT = CICADA_ROOT / "experiments" / "EXP-LP-GLYPH-LINECLASS-001"
TRIAGE = CICADA_ROOT / "reports/candidates/image_triage.json"
PAGE_DIR = CICADA_ROOT / "corpus/normalized/rtkd_pages"
# full-res rune line is ~114px (NCC-HEADING). Hex digits are ~half that.
RUNE_H_MIN = 88
RUNE_H_MAX = 160
DOT_MAX_W = 22
INK_MIN = 45


def object_path(sha: str) -> Path:
    return CICADA_ROOT / "corpus/objects/sha256" / sha[:2] / sha


def _runs(mask: np.ndarray, min_len: int) -> list[tuple[int, int]]:
    out, i, n = [], 0, len(mask)
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


def load(path: Path):
    arr = np.asarray(Image.open(path).convert("RGB"))
    r, g, b = [arr[:, :, i].astype(np.int16) for i in range(3)]
    ink = (r + g + b) < 400
    red = (r - np.maximum(g, b)) > 40
    return ink, red


def line_bands(ink: np.ndarray) -> list[tuple[int, int]]:
    h, w = ink.shape
    # drop-cap is wide; occupancy must start past it or the first lines glue
    x0, x1 = int(w * 0.36), int(w * 0.90)
    occ = ink[:, x0:x1].mean(axis=1) > 0.008
    return _runs(occ, min_len=10)


def glyphs_in_band(ink, red, y0, y1, x0, x1) -> list[dict]:
    band = ink[y0:y1, x0:x1]
    col = band.mean(axis=0) > 0.06
    boxes = _runs(col, min_len=6)
    out = []
    for a, b in boxes:
        sl = ink[y0:y1, x0 + a : x0 + b]
        n = int(sl.sum())
        w = b - a
        ih = int(sl.any(axis=1).sum())
        if n < INK_MIN or ih < 70:
            continue
        if w <= DOT_MAX_W and n < 260:
            continue
        # 3×3 / 3×4 red dot grids: wide, not tall, speckled
        rf = float((red[y0:y1, x0 + a : x0 + b] & sl).sum() / max(n, 1))
        if w >= 48 and ih <= 85:
            continue
        # full-height red dot-grid (p57 line-1 3×4)
        if w >= 50 and rf >= 0.85 and n >= 2400:
            continue
        out.append({"w": w, "h": ih, "n": n, "red": rf >= 0.28, "rf": rf, "x": a})
    # drop 3×n dot grids: ≥3 consecutive thin columns
    thin = [g["w"] <= 20 and g["n"] < 200 for g in out]
    drop = [False] * len(out)
    i = 0
    while i < len(out):
        if not thin[i]:
            i += 1
            continue
        j = i
        while j < len(out) and thin[j]:
            j += 1
        if j - i >= 3:
            for k in range(i, j):
                drop[k] = True
        i = j
    return [g for g, d in zip(out, drop) if not d]


def drop_cap(ink, red, y0, y1, x_left, x_right) -> dict | None:
    """Tall red ink in the left margin, spanning >= 1.6 rune lines."""
    sl = ink[y0:y1, x_left:x_right]
    if sl.sum() < 400:
        return None
    rf = float((red[y0:y1, x_left:x_right] & sl).sum() / max(int(sl.sum()), 1))
    h = int(sl.any(axis=1).sum())
    if h < int(RUNE_H_MIN * 1.5) or rf < 0.20:
        return None
    return {"w": x_right - x_left, "h": h, "n": int(sl.sum()), "red": True, "rf": rf, "drop": True}


def segment(path: Path) -> dict:
    ink, red = load(path)
    h, w = ink.shape
    bands = line_bands(ink)
    keep_b = []
    for y0, y1 in bands:
        if (y1 - y0) > 200:
            break  # stipple / illustration; ignore everything below
        if RUNE_H_MIN <= (y1 - y0) <= RUNE_H_MAX:
            keep_b.append((y0, y1))
    rune_bands = keep_b
    # split glued double-lines (~130–140px) at the weakest occupancy row
    split_b = []
    x_occ0, x_occ1 = int(w * 0.36), int(w * 0.90)
    occ = ink[:, x_occ0:x_occ1].mean(axis=1)
    for y0, y1 in rune_bands:
        if (y1 - y0) >= 128:
            mid0, mid1 = y0 + 40, y1 - 40
            if mid1 > mid0:
                cut = int(mid0 + np.argmin(occ[mid0:mid1]))
                if y0 + 48 <= cut <= y1 - 48:
                    split_b.append((y0, cut))
                    split_b.append((cut, y1))
                    continue
        split_b.append((y0, y1))
    rune_bands = split_b
    # drop-cap spans the first two rune lines if present
    glyphs: list[dict] = []
    if rune_bands:
        y_top = rune_bands[0][0]
        y_cap = rune_bands[min(3, len(rune_bands) - 1)][1]
        cap = drop_cap(ink, red, y_top, y_cap, int(w * 0.06), int(w * 0.36))
        if cap:
            glyphs.append(cap)
    x1 = int(w * 0.94)
    per_line = []
    for li, (y0, y1) in enumerate(rune_bands):
        col = ink[y0:y1].mean(axis=0)
        xs = np.where(col > 0.04)[0]
        x0 = max(int(w * 0.08), int(xs[0]) - 6) if len(xs) else int(w * 0.22)
        # first lines: do not re-count the drop-cap
        if li < 2:
            x0 = max(x0, int(w * 0.34))
        g = glyphs_in_band(ink, red, y0, y1, x0, x1)
        per_line.append(len(g))
        glyphs.extend(g)
    reds = [int(g["red"]) for g in glyphs]
    first_run = 0
    for v in reds:
        if v:
            first_run += 1
        elif first_run:
            break
    return {
        "n_bands": len(bands),
        "n_rune_bands": len(rune_bands),
        "band_h": [y1 - y0 for y0, y1 in bands],
        "rune_h": [y1 - y0 for y0, y1 in rune_bands],
        "n_glyphs": len(glyphs),
        "per_line": per_line,
        "n_red": sum(reds),
        "first_red_run": first_run,
        "has_drop": bool(glyphs and glyphs[0].get("drop")),
    }


def trans_n(onion: int) -> int:
    p = PAGE_DIR / f"split_{15 + onion:03d}.txt"
    return len(GP.rune_indices(p.read_text(encoding="utf-8"))) if p.exists() else 0


def page_ix(onion: int) -> list[int]:
    return GP.rune_indices((PAGE_DIR / f"split_{15 + onion:03d}.txt").read_text(encoding="utf-8"))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    triage = {item["url"].rsplit("/", 1)[-1]: item
              for item in json.loads(TRIAGE.read_text()) if "unsolved" in item.get("url", "")}
    controls = {}
    for onion, expect_n, expect_red in ((56, 85, 5), (57, 95, 7)):
        item = triage[f"{onion}.jpg"]
        seg = segment(object_path(item["sha256"]))
        ok_red = seg["first_red_run"] == expect_red
        ok_n = seg["n_glyphs"] == expect_n
        ok = ok_red  # heading length; total count is a secondary check
        controls[onion] = {**seg, "expect_n": expect_n, "expect_red": expect_red,
                           "ok_n": ok_n, "ok_red": ok_red, "ok": ok}
        print(f"CTRL {onion} n={seg['n_glyphs']} (want {expect_n}) "
              f"red0={seg['first_red_run']} (want {expect_red}) "
              f"bands={seg['n_rune_bands']} drop={seg['has_drop']} ok={ok}", flush=True)
        print(f"  per_line={seg.get('per_line')} rune_h={seg['rune_h'][:12]}", flush=True)

    result = {
        "experiment": "EXP-LP-GLYPH-LINECLASS-001",
        "family": "rune-height line classification + drop-cap (hex/art excluded)",
        "controls": controls,
        "controls_pass": all(controls[k]["ok"] for k in controls),
        "verified_new_unsolved_runes": 0,
    }
    if not result["controls_pass"]:
        result["aborted"] = "p56/57 controls failed; headings not used as keys"
        (OUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")
        print("CONTROLS FAILED")
        return

    # controls passed: first red run as heading, try as Vigenere on that page body
    # and the rest of the red section
    hits, tested = [], 0
    for onion in range(0, 56):
        name = f"{onion}.jpg"
        if name not in triage:
            continue
        seg = segment(object_path(triage[name]["sha256"]))
        n_tr = trans_n(onion)
        rec = {"onion": onion, "n_glyphs": seg["n_glyphs"], "trans": n_tr,
               "first_red": seg["first_red_run"], "match_count": seg["n_glyphs"] == n_tr}
        ct = page_ix(onion)
        klen = seg["first_red_run"]
        if 4 <= klen <= 24 and klen < len(ct):
            key = ct[:klen]
            body = ct[klen:]
            for name_, pt in (("direct", key), ("atbash", atbash(key)),
                              ("tot", totient_prime_stream(key))):
                tested += 1
                out = vigenere_decrypt(body, pt)
                lat = GP.latin_stream(out)
                sc = score_candidate(out, lat)
                row = {**rec, "key_method": name_, "head": lat[:80], **sc, "n": len(out)}
                if keep(sc, len(out)):
                    hits.append(row)
                    print("KEEP", onion, name_, sc["trigram_per_100"], lat[:40], flush=True)
        result.setdefault("pages", []).append(rec)

    result["tested"] = tested
    result["keep_bar_hits"] = len(hits)
    result["keeps"] = hits[:12]
    result["n_count_match"] = sum(1 for p in result.get("pages", []) if p["match_count"])
    result["skeptic_review"] = {"verdict": "null" if not hits else "keep-bar needs human English"}
    (OUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print("tested", tested, "keeps", len(hits), "count_match", result["n_count_match"])


if __name__ == "__main__":
    main()
