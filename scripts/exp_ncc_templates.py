#!/usr/bin/env python3
"""NCC template-match isolated runes. Templates from page 57's clean 115px line.

Control: onion 56 → ~85 glyphs, first 5 red; onion 57 → ~95, first 7 red.
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

GP = Gematria()
PAGE_DIR = CICADA_ROOT / "corpus/normalized/rtkd_pages"
OUT = CICADA_ROOT / "experiments" / "EXP-LP-NCC-TEMPLATE-001"
TRIAGE = CICADA_ROOT / "reports/candidates/image_triage.json"
TH, TW = 40, 32  # template size


def object_path(sha: str) -> Path:
    return CICADA_ROOT / "corpus/objects/sha256" / sha[:2] / sha


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


def load(path: Path):
    arr = np.asarray(Image.open(path).convert("RGB"))
    r, g, b = [arr[:, :, i].astype(np.int16) for i in range(3)]
    ink = (r + g + b) < 400
    red = (r - np.maximum(g, b)) > 40
    return ink, red


def norm_patch(sl: np.ndarray) -> np.ndarray:
    # sl bool → float TH x TW, zero-mean unit
    ys = sl.any(axis=1)
    if not ys.any():
        return np.zeros((TH, TW), dtype=np.float32)
    y0, y1 = int(np.argmax(ys)), TH
    # crop ink bbox then resize via simple stride
    xs = sl.any(axis=0)
    x0, x1 = int(np.argmax(xs)), int(len(xs) - np.argmax(xs[::-1]))
    crop = sl[int(np.argmax(ys)) : int(len(ys) - np.argmax(ys[::-1])), x0:x1]
    if crop.size == 0:
        return np.zeros((TH, TW), dtype=np.float32)
    im = Image.fromarray((crop.astype(np.uint8) * 255))
    im = im.resize((TW, TH), Image.BILINEAR)
    p = np.asarray(im).astype(np.float32) / 255.0
    p = p - p.mean()
    n = float(np.sqrt((p * p).sum()) + 1e-6)
    return (p / n).astype(np.float32)


def ncc(a: np.ndarray, b: np.ndarray) -> float:
    return float((a * b).sum())


def extract_templates(ink: np.ndarray, y0: int, y1: int, x0: int, x1: int) -> list[np.ndarray]:
    col = ink[y0:y1, x0:x1].mean(axis=0) > 0.08
    tpls = []
    for a, b in _runs(col, min_len=10):
        if b - a <= 18:
            continue
        sl = ink[y0:y1, x0 + a : x0 + b]
        if sl.sum() < 120:
            continue
        tpls.append(norm_patch(sl))
    return tpls


def match_line(ink, red, y0, y1, x0, x1, templates, thr: float) -> list[dict]:
    """Greedy left-to-right: at each x take best template NCC over a window."""
    h = y1 - y0
    width = x1 - x0
    hits = []
    x = 0
    while x < width - 12:
        # skip empty columns
        if ink[y0:y1, x0 + x].mean() < 0.04:
            x += 1
            continue
        best, best_w, best_rf = -1.0, 28, 0.0
        for w in (24, 32, 40, 48, 56, 72):
            if x + w > width:
                continue
            sl = ink[y0:y1, x0 + x : x0 + x + w]
            if sl.sum() < 80:
                continue
            patch = norm_patch(sl)
            score = max(ncc(patch, t) for t in templates)
            if score > best:
                rd = red[y0:y1, x0 + x : x0 + x + w]
                n = int(sl.sum()) or 1
                best = score
                best_w = w
                best_rf = float((rd & sl).sum() / n)
        if best >= thr:
            hits.append({"x": x0 + x, "w": best_w, "ncc": round(best, 3), "is_red": best_rf >= 0.25, "rf": round(best_rf, 3)})
            x += max(best_w - 4, 16)  # slight overlap then jump; 13px gap ≈ don't merge
        else:
            x += 2
    return hits


def page_lines(ink) -> list[tuple[int, int, int, int, str]]:
    """Return (y0,y1,x0,x1,kind) rune-line boxes."""
    col0, col1 = 400, 1850
    row = ink[:, col0:col1].mean(axis=1) > 0.015
    out = []
    for y0, y1 in _runs(row, min_len=40):
        h = y1 - y0
        if 50 <= h <= 85:
            continue
        if h < 90:
            continue
        if h > 200:
            sub = ink[y0:y1, 850:col1].mean(axis=1) > 0.02
            for sy0, sy1 in _runs(sub, min_len=70):
                if 95 <= (sy1 - sy0) <= 140:
                    out.append((y0 + sy0, y0 + sy1, 850, col1, "body"))
            # drop-cap box
            out.insert(0, (y0, min(y0 + 200, y1), col0, 850, "drop"))
        else:
            out.append((y0, y1, col0, col1, "line"))
    return out


def segment(path: Path, templates: list[np.ndarray], thr: float) -> dict:
    ink, red = load(path)
    glyphs = []
    line_counts = []
    for y0, y1, x0, x1, kind in page_lines(ink):
        if kind == "drop":
            sl = ink[y0:y1, x0:x1]
            if sl.mean() < 0.01:
                continue
            n = int(sl.sum()) or 1
            rf = float((red[y0:y1, x0:x1] & sl).sum() / n)
            glyphs.append({"x": x0, "w": x1 - x0, "ncc": 1.0, "is_red": rf >= 0.25, "rf": rf, "kind": "drop"})
            continue
        hits = match_line(ink, red, y0, y1, x0, x1, templates, thr)
        glyphs.extend(hits)
        if hits:
            line_counts.append(len(hits))
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
    return {"n": len(glyphs), "n_red": sum(1 for g in glyphs if g["is_red"]), "red_runs": red_runs, "line_counts": line_counts}


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
)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    triage = {x["url"].rsplit("/", 1)[-1]: x for x in json.loads(TRIAGE.read_text()) if "unsolved" in x["url"]}
    ink57, _ = load(object_path(triage["57.jpg"]["sha256"]))
    # clean line measured earlier
    templates = extract_templates(ink57, 1537, 1652, 600, 1750)
    print("templates", len(templates))
    if len(templates) < 6:
        # fallback second clean line
        templates += extract_templates(ink57, 1725, 1840, 600, 1750)
        print("templates after line2", len(templates))

    best = None
    for thr in (0.35, 0.42, 0.50, 0.58):
        s56 = segment(object_path(triage["56.jpg"]["sha256"]), templates, thr)
        s57 = segment(object_path(triage["57.jpg"]["sha256"]), templates, thr)
        rec = {
            "thr": thr,
            "p56_n": s56["n"],
            "p56_fr": (s56["red_runs"] or [{"len": 0}])[0]["len"],
            "p57_n": s57["n"],
            "p57_fr": (s57["red_runs"] or [{"len": 0}])[0]["len"],
            "p56_lines": s56["line_counts"],
            "p57_lines": s57["line_counts"],
        }
        rec["ok"] = abs(rec["p56_n"] - 85) <= 3 and rec["p56_fr"] == 5 and abs(rec["p57_n"] - 95) <= 3 and rec["p57_fr"] == 7
        print("thr", rec)
        if rec["ok"] and best is None:
            best = thr

    # if a threshold passed, extract headings on red pages
    heading_hits = []
    overlays = []
    use_thr = best if best is not None else 0.42
    targets = [0, 3, 8, 15, 23, 27, 40, 53, 54, 56, 57]
    if best is not None:
        for onion in targets:
            seg = segment(object_path(triage[f"{onion}.jpg"]["sha256"]), templates, use_thr)
            n_trans = 85 if onion == 56 else 95 if onion == 57 else len(
                GP.rune_indices((PAGE_DIR / f"split_{15 + onion:03d}.txt").read_text())
            )
            overlays.append({"onion": onion, "trans": n_trans, **{k: seg[k] for k in ("n", "n_red", "red_runs", "line_counts")}})
            print(f"apply {onion} n={seg['n']} trans={n_trans} fr={(seg['red_runs'] or [{'len':0}])[0]['len']}")
            if onion <= 55:
                for run in seg["red_runs"]:
                    if 3 <= run["len"] <= 34 and run["start"] <= 1:
                        ix = GP.rune_indices((PAGE_DIR / f"split_{15 + onion:03d}.txt").read_text())
                        ct = ix[: run["len"]]
                        for name, pt in [("direct", ct), ("atbash", atbash(ct))] + [
                            (f"c{s}", caesar(ct, s)) for s in range(29)
                        ]:
                            latin = GP.latin_stream(pt if name != "direct" else ct)
                            if name.startswith("c"):
                                latin = GP.latin_stream(caesar(ct, int(name[1:])))
                            elif name == "atbash":
                                latin = GP.latin_stream(atbash(ct))
                            if any(latin == v or latin.startswith(v) for v in HEADING_VOCAB):
                                heading_hits.append({"onion": onion, "n": run["len"], "method": name, "latin": latin})

    (OUT / "result.json").write_text(
        json.dumps(
            {
                "n_templates": len(templates),
                "best_thr": best,
                "heading_hits": heading_hits,
                "overlays": overlays,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print("best_thr", best, "heading_hits", heading_hits)


if __name__ == "__main__":
    main()
