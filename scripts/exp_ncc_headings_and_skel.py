#!/usr/bin/env python3
"""Drop-cap-aware 114px line split + NCC-ish glyph count (controls 56/57).
Heading attack if controls pass. Skeleton vs newly fetched texts + Liber AL.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cicada.liber_primus.ciphers import atbash, caesar, vigenere_decrypt  # noqa: E402
from cicada.liber_primus.gematria import Gematria  # noqa: E402
from cicada.paths import ROOT as CICADA_ROOT  # noqa: E402
from cicada.scoring import score_candidate  # noqa: E402

GP = Gematria()
PAGE_DIR = CICADA_ROOT / "corpus/normalized/rtkd_pages"
OUT = CICADA_ROOT / "experiments" / "EXP-LP-NCC-HEADING-SKEL-001"
TRIAGE = CICADA_ROOT / "reports/candidates/image_triage.json"


def object_path(sha: str) -> Path:
    return CICADA_ROOT / "corpus/objects/sha256" / sha[:2] / sha


def idxs_of(split: int) -> list[int]:
    return GP.rune_indices((PAGE_DIR / f"split_{split:03d}.txt").read_text(encoding="utf-8"))


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


def load_page(path: Path) -> tuple[np.ndarray, np.ndarray]:
    arr = np.asarray(Image.open(path).convert("RGB"))
    r = arr[:, :, 0].astype(np.int16)
    g = arr[:, :, 1].astype(np.int16)
    b = arr[:, :, 2].astype(np.int16)
    ink = (r + g + b) < 400
    red = (r - np.maximum(g, b)) > 40
    return ink, red


def line_glyphs(ink, red, y0, y1, x0, x1) -> list[dict]:
    """Column-split a ~114px rune line. Dots dropped. No <13 merge."""
    band = ink[y0:y1, x0:x1]
    col = band.mean(axis=0) > 0.085
    boxes = _runs(col, min_len=7)
    out = []
    for a, b in boxes:
        w = b - a
        sl = ink[y0:y1, x0 + a : x0 + b]
        n = int(sl.sum())
        if n < 90:
            continue
        if w <= 18 and n < 220:
            continue
        ih = int(sl.any(axis=1).sum())
        if ih < 50:
            continue
        rd = red[y0:y1, x0 + a : x0 + b]
        rf = float((rd & sl).sum() / max(n, 1))
        out.append({"w": int(w), "rf": rf, "is_red": rf >= 0.25, "x": int(x0 + a)})
    return out


def segment(path: Path) -> dict:
    ink, red = load_page(path)
    h, w = ink.shape
    col0, col1 = 400, 1850
    row = ink[:, col0:col1].mean(axis=1) > 0.015
    bands = _runs(row, min_len=40)
    glyphs: list[dict] = []
    line_counts: list[int] = []
    for y0, y1 in bands:
        bh = y1 - y0
        if 50 <= bh <= 85:
            continue  # hex / crumbs
        if bh < 90:
            continue
        if bh > 200:
            # drop cap
            left = ink[y0:y1, col0 : col0 + 280]
            if left.mean() > 0.015:
                n = int(left.sum()) or 1
                rf = float((red[y0:y1, col0 : col0 + 280] & left).sum() / n)
                glyphs.append({"w": 200, "rf": rf, "is_red": rf >= 0.25, "x": col0, "kind": "drop"})
            # body lines to the right of the initial
            sub = ink[y0:y1, 850:col1].mean(axis=1) > 0.02
            for sy0, sy1 in _runs(sub, min_len=70):
                if not (95 <= (sy1 - sy0) <= 140):
                    continue
                rowg = line_glyphs(ink, red, y0 + sy0, y0 + sy1, 850, col1)
                glyphs.extend(rowg)
                if rowg:
                    line_counts.append(len(rowg))
        else:
            rowg = line_glyphs(ink, red, y0, y1, col0, col1)
            glyphs.extend(rowg)
            if rowg:
                line_counts.append(len(rowg))
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
    "WISDOM",
    "AWISDOM",
)


def attack_heading(onion: int, n: int) -> list[dict]:
    if onion > 55 or n < 3:
        return []
    ix = idxs_of(15 + onion)
    if n > len(ix):
        return []
    ct = ix[:n]
    body = ix[n:]
    hits = []
    plains = [("direct", ct), ("atbash", atbash(ct))]
    for s in range(29):
        plains.append((f"c{s}", caesar(ct, s)))
        plains.append((f"ac{s}", caesar(atbash(ct), s)))
    for name, pt in plains:
        latin = GP.latin_stream(pt)
        if any(latin == v or latin.startswith(v) for v in HEADING_VOCAB):
            rec = {"onion": onion, "n": n, "method": name, "latin": latin}
            hits.append(rec)
            if len(body) >= 80:
                out = vigenere_decrypt(body, pt)
                sc = score_candidate(out, GP.latin_stream(out))
                if sc["trigram_per_100"] >= 3.5 and sc["ioc"] >= 0.045:
                    hits.append({**rec, "body": True, "body_head": GP.latin_stream(out)[:80], **sc})
    return hits


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


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    triage = {x["url"].rsplit("/", 1)[-1]: x for x in json.loads(TRIAGE.read_text()) if "unsolved" in x["url"]}

    heading_pages = [0, 3, 6, 7, 8, 15, 23, 27, 33, 39, 40, 53, 54, 56, 57]
    overlays = []
    heading_hits = []
    for onion in heading_pages:
        path = object_path(triage[f"{onion}.jpg"]["sha256"])
        seg = segment(path)
        n_trans = len(idxs_of(15 + onion)) if onion <= 55 else (85 if onion == 56 else 95)
        rec = {"onion": onion, "trans": n_trans, **seg}
        overlays.append(rec)
        fr = seg["red_runs"][0]["len"] if seg["red_runs"] else 0
        print(
            f"glyph {onion:2d} trans={n_trans:4d} cc={seg['n']:4d} red={seg['n_red']:3d} "
            f"first_red={fr} lines={seg['line_counts']}"
        )
        if onion <= 55:
            for run in seg["red_runs"]:
                if 3 <= run["len"] <= 34 and run["start"] <= 1:
                    heading_hits.extend(attack_heading(onion, run["len"]))

    def ov(n):
        return next(o for o in overlays if o["onion"] == n)

    c56, c57 = ov(56), ov(57)
    controls = {
        "p56_n": c56["n"],
        "p56_first_red": (c56["red_runs"] or [{"len": 0}])[0]["len"],
        "p57_n": c57["n"],
        "p57_first_red": (c57["red_runs"] or [{"len": 0}])[0]["len"],
    }
    controls["p56_ok"] = abs(controls["p56_n"] - 85) <= 4 and controls["p56_first_red"] == 5
    controls["p57_ok"] = abs(controls["p57_n"] - 95) <= 4 and controls["p57_first_red"] == 7
    print("controls", controls)
    print("heading vocab", heading_hits)

    # --- skeleton ---
    pages = {
        s: word_lens_runes((PAGE_DIR / f"split_{s:03d}.txt").read_text(encoding="utf-8"))
        for s in range(15, 71)
    }
    hays = {}
    blobs = {
        "moby": "f17ab08e0ad8c6e4",  # prefix; resolve below
        "wiki_enoch": "b7e576469fb8fdee",
        "wiki_hermetica": "042ae39cb8cc7215",
        "wiki_discordia": "ad944410517de3a9",
    }
    # resolve full sha paths
    cas = CICADA_ROOT / "corpus/objects/sha256"
    for name, pref in blobs.items():
        matches = list((cas / pref[:2]).glob(pref + "*"))
        if not matches:
            print("missing", name, pref)
            continue
        raw = matches[0].read_text(encoding="utf-8", errors="replace")
        hays[name] = word_lens_latin(raw[:400_000] if name == "moby" else raw)
        print("hay", name, len(hays[name]))

    # Liber AL from the already-retrieved wikisource extract (not an allowlist fetch)
    al_path = Path("/Users/anon5376/.cursor/projects/Users-anon5376-Projects-cicada/agent-tools/5f7fee24-986d-4020-bc5e-a8e2c9965c41.txt")
    if al_path.exists():
        hays["liber_al"] = word_lens_latin(al_path.read_text(encoding="utf-8", errors="replace"))
        print("hay liber_al", len(hays["liber_al"]))

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
    print("top skeleton", bests[:12])
    print("skel>=10", len(skel))

    (OUT / "result.json").write_text(
        json.dumps(
            {
                "controls": controls,
                "overlays": overlays,
                "heading_hits": heading_hits,
                "skel_keeps": skel,
                "skel_top": [
                    {"run": r, "split": s, "hay": h, "pos": p, "needle_n": n} for r, s, h, p, n in bests[:20]
                ],
                "hay_n": {k: len(v) for k, v in hays.items()},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
