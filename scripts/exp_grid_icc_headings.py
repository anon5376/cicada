#!/usr/bin/env python3
"""Correct pp49–51 grid from pixel bar-heights; ICC/DQT as unused seeds;
size-filtered 13px-gap glyph counts for heading lengths (controls: 56/57).
"""
from __future__ import annotations

import hashlib
import json
import re
import struct
import sys
from collections import defaultdict
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
OUT = CICADA_ROOT / "experiments" / "EXP-LP-GRID-ICC-HEADING-001"
TRIAGE = CICADA_ROOT / "reports/candidates/image_triage.json"
ALPHA60 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwx"


def object_path(sha: str) -> Path:
    return CICADA_ROOT / "corpus/objects/sha256" / sha[:2] / sha


def idxs_of(split: int) -> list[int]:
    return GP.rune_indices((PAGE_DIR / f"split_{split:03d}.txt").read_text(encoding="utf-8"))


def unsolved_flat() -> list[int]:
    out: list[int] = []
    for s in range(15, 71):
        out.extend(idxs_of(s))
    return out


def keep(sc: dict, n: int) -> bool:
    return (
        n >= 80
        and sc["trigram_per_100"] >= 3.5
        and 0.28 <= sc["vowelish_ratio"] <= 0.55
        and sc["ioc"] >= 0.045
    )


def apply_rel(ct: list[int], ks: list[int], rel: str) -> list[int]:
    n = min(len(ct), len(ks) if rel == "otp" else len(ct))
    if rel == "sub":
        return [(ct[i] - ks[i % len(ks)]) % 29 for i in range(len(ct))]
    if rel == "add":
        return [(ct[i] + ks[i % len(ks)]) % 29 for i in range(len(ct))]
    if rel == "beau":
        return [(ks[i % len(ks)] - ct[i]) % 29 for i in range(len(ct))]
    if rel == "otp":
        return [(ct[i] - ks[i]) % 29 for i in range(n)]
    raise ValueError(rel)


def sha256_ctr(seed: bytes, n: int) -> list[int]:
    out: list[int] = []
    i = 0
    while len(out) < n:
        digest = hashlib.sha256(seed + i.to_bytes(4, "big")).digest()
        for b in digest:
            out.append(b % 29)
            if len(out) >= n:
                break
        i += 1
    return out


def parse_rtkd_grid() -> list[str]:
    toks: list[str] = []
    for s in (64, 65, 66):
        text = (PAGE_DIR / f"split_{s:03d}.txt").read_text(encoding="utf-8")
        for m in re.finditer(r"[0-9A-Za-x]{2}", text):
            # skip rune-adjacent false hits; tokens are isolated XX
            toks.append(m.group(0))
    # 256 expected; rtkd has header runes that might match [A-Za-x]{2}? runes are not ascii
    return toks


def decode60(tokens: list[str]) -> list[int]:
    out = []
    for t in tokens:
        if len(t) != 2 or t[0] not in ALPHA60 or t[1] not in ALPHA60:
            raise ValueError(t)
        out.append(ALPHA60.index(t[0]) * 60 + ALPHA60.index(t[1]))
    return out


def jpeg_segments(data: bytes) -> dict:
    """Collect ICC (APP2), DQT, COM from a JPEG."""
    icc_parts: dict[int, bytes] = {}
    dqts: list[bytes] = []
    comments: list[bytes] = []
    i = 2  # skip SOI
    while i < len(data) - 4:
        if data[i] != 0xFF:
            break
        while i < len(data) and data[i] == 0xFF:
            i += 1
        if i >= len(data):
            break
        marker = data[i]
        i += 1
        if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
            continue
        if marker == 0xDA:
            break
        seglen = struct.unpack(">H", data[i : i + 2])[0]
        payload = data[i + 2 : i + seglen]
        i += seglen
        if marker == 0xDB:
            dqts.append(payload)
        elif marker == 0xFE:
            comments.append(payload)
        elif marker == 0xE2 and payload.startswith(b"ICC_PROFILE\x00"):
            seq, tot = payload[12], payload[13]
            icc_parts[seq] = payload[14:]
    icc = b"".join(icc_parts[k] for k in sorted(icc_parts)) if icc_parts else b""
    return {"icc": icc, "dqt": b"".join(dqts), "com": b"".join(comments)}


def measure_bare_bars(path: Path) -> list[dict]:
    """Measure tall thin ink components (candidate I / l / 1)."""
    im = Image.open(path).convert("RGB")
    arr = np.asarray(im)
    r = arr[:, :, 0].astype(np.int16)
    g = arr[:, :, 1].astype(np.int16)
    b = arr[:, :, 2].astype(np.int16)
    ink = (r + g + b) < 380
    # grid lives in the text column
    ink = ink[500:3100, 500:1900]
    # connected components via scipy if present, else row-scan boxes
    try:
        from scipy import ndimage  # type: ignore

        labeled, nlab = ndimage.label(ink)
        bars = []
        for lab in range(1, nlab + 1):
            ys, xs = np.where(labeled == lab)
            if ys.size < 20:
                continue
            h = int(ys.max() - ys.min() + 1)
            w = int(xs.max() - xs.min() + 1)
            if w <= 12 and 55 <= h <= 85:
                bars.append(
                    {
                        "h": h,
                        "w": w,
                        "y": int(ys.min() + 500),
                        "x": int(xs.min() + 500),
                        "guess": "l" if h >= 71 else ("I" if h >= 62 else "?"),
                    }
                )
        return bars
    except Exception:
        return []


def segment_runes(path: Path) -> dict:
    """Size-filter + ≥13px gap. Returns ordered rune-like glyphs with redness."""
    im = Image.open(path).convert("RGB")
    # work at full res for the 13px claim; crop the text column
    arr = np.asarray(im)
    r = arr[:, :, 0].astype(np.int16)
    g = arr[:, :, 1].astype(np.int16)
    b = arr[:, :, 2].astype(np.int16)
    ink = ((r + g + b) < 420)[:, 520:1780]
    red = ((r - np.maximum(g, b)) > 40)[:, 520:1780]
    row_occ = ink.mean(axis=1) > 0.012
    lines = _runs(row_occ, min_len=18)
    # typical rune line height ~70-110; drop fat illustration bands
    line_hs = [y1 - y0 for y0, y1 in lines]
    if line_hs:
        med_h = float(np.median(line_hs))
        lines = [(y0, y1) for y0, y1 in lines if 0.45 * med_h <= (y1 - y0) <= 1.7 * med_h]
    glyphs = []
    line_counts = []
    for y0, y1 in lines:
        band = ink[y0:y1]
        col_occ = band.mean(axis=0) > 0.05
        raw = _runs(col_occ, min_len=4)
        # enforce ≥13 px separation by merging closer runs first then splitting is wrong:
        # projection already merges touching ink; we only drop micro-gaps by merging <13
        merged: list[tuple[int, int]] = []
        for x0, x1 in raw:
            if merged and x0 - merged[-1][1] < 13:
                merged[-1] = (merged[-1][0], x1)
            else:
                merged.append((x0, x1))
        row = []
        heights = []
        cands = []
        for x0, x1 in merged:
            sl = ink[y0:y1, x0:x1]
            n = int(sl.sum())
            w = x1 - x0
            h = y1 - y0
            if n < 40 or w < 8:
                continue
            # punctuation / dots
            if w <= 14 and n < 80:
                continue
            rf = float((red[y0:y1, x0:x1] & sl).sum() / max(n, 1))
            cands.append((x0, x1, n, rf, w, h))
            heights.append(h if False else int(sl.any(axis=1).sum()))
        if not cands:
            continue
        # drop hex-sized (much shorter than median ink height in this row)
        ink_hs = [int(ink[y0:y1, x0:x1].any(axis=1).sum()) for x0, x1, *_ in cands]
        med = float(np.median(ink_hs)) if ink_hs else 0
        kept = []
        for (x0, x1, n, rf, w, h), ih in zip(cands, ink_hs):
            if med and ih < 0.62 * med:
                continue
            kept.append(
                {
                    "x0": 520 + x0,
                    "y0": int(y0),
                    "x1": 520 + x1,
                    "w": w,
                    "ih": ih,
                    "px": n,
                    "red_frac": rf,
                    "is_red": rf >= 0.28,
                }
            )
        if kept:
            glyphs.extend(kept)
            line_counts.append(len(kept))
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
)


def attack_heading(onion: int, n: int) -> list[dict]:
    if onion > 55:
        return []
    ix = idxs_of(15 + onion)
    if n < 3 or n > len(ix):
        return []
    ct = ix[:n]
    hits = []
    plains = [("direct", ct), ("atbash", atbash(ct)), ("tot", ct)]
    # totient-like: reuse caesar/atbash sweep
    for s in range(29):
        plains.append((f"c{s}", caesar(ct, s)))
        plains.append((f"ac{s}", caesar(atbash(ct), s)))
    for name, pt in plains:
        latin = GP.latin_stream(pt)
        if any(latin.startswith(v) or v == latin for v in HEADING_VOCAB):
            hits.append({"onion": onion, "n": n, "method": name, "latin": latin})
    return hits


def test_bytes_as_key(label: str, blob: bytes, prefix: list[int], hits: list, tested: list) -> None:
    if not blob:
        return
    key29 = [b % 29 for b in blob]
    seeds = {
        "repeat": None,
        "sha": hashlib.sha256(blob).digest(),
    }
    for rel in ("sub", "add", "beau"):
        tested[0] += 1
        out = apply_rel(prefix, key29, rel)
        latin = GP.latin_stream(out)
        sc = score_candidate(out, latin)
        rec = {"src": label, "kind": f"repeat_{rel}", "head": latin[:80], **sc}
        print(f"  {label:22s} {rel:4s} nkey={len(key29):5d} tri={sc['trigram_per_100']:.2f} ioc={sc['ioc']:.3f} {latin[:48]}")
        if keep(sc, len(prefix)):
            hits.append(rec)
    ks = sha256_ctr(hashlib.sha256(blob).digest(), len(prefix))
    tested[0] += 1
    out = apply_rel(prefix, ks, "sub")
    latin = GP.latin_stream(out)
    sc = score_candidate(out, latin)
    print(f"  {label:22s} ctr      tri={sc['trigram_per_100']:.2f} {latin[:48]}")
    if keep(sc, len(prefix)):
        hits.append({"src": label, "kind": "ctr", "head": latin[:80], **sc})
    # 32-byte chunks as successive CTR IVs
    if len(blob) >= 32:
        chunks = [blob[i : i + 32] for i in range(0, len(blob) - 31, 32)]
        if 2 <= len(chunks) <= 16:
            ks = []
            for ch in chunks:
                ks.extend(sha256_ctr(ch, max(80, len(prefix) // len(chunks))))
            ks = ks[: len(prefix)]
            tested[0] += 1
            out = apply_rel(prefix, ks, "sub")
            latin = GP.latin_stream(out)
            sc = score_candidate(out, latin)
            print(f"  {label:22s} chunkctr tri={sc['trigram_per_100']:.2f} {latin[:48]}")
            if keep(sc, len(prefix)):
                hits.append({"src": label, "kind": "chunkctr", "head": latin[:80], **sc})


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    triage = {x["url"].rsplit("/", 1)[-1]: x for x in json.loads(TRIAGE.read_text()) if "unsolved" in x["url"]}

    raw_toks = parse_rtkd_grid()
    print("rtkd grid tokens", len(raw_toks), "head", raw_toks[:8], "tail", raw_toks[-4:])
    # artwaste claimed 4 corrections; apply after independent measure
    corrections = {
        # (page_onion, row0, col0): new_token
    }
    bar_report = {}
    for onion in (49, 50, 51):
        path = object_path(triage[f"{onion}.jpg"]["sha256"])
        bars = measure_bare_bars(path)
        bar_report[str(onion)] = bars
        print(f"onion {onion} bare-bars {len(bars)} heights {[b['h'] for b in bars[:20]]}")

    # Apply artwaste's 4 edits only after we see matching heights in our measure,
    # but always test both raw and the claimed correction (labeled).
    claimed = list(raw_toks)
    # locate tokens
    def replace_nth(seq: list[str], old: str, new: str, n: int) -> bool:
        seen = 0
        for i, t in enumerate(seq):
            if t == old:
                if seen == n:
                    seq[i] = new
                    return True
                seen += 1
        return False

    # p49 rows are first 10*8 = 80 tokens: row5 col5 = index 5*8+5 = 45 = 1L
    # row6 col2 = 6*8+2 = 50 = 0L
    # p50 starts at 80; 13 rows; row10 col5 = 80+10*8+5 = 165 = 0l
    # p51 starts at 80+13*8 = 184; row7 col6 = 184+7*8+6 = 246 = 3i
    claimed_edits = []
    for idx, old, new, tag in (
        (45, "1L", "1l", "p49r5_1L"),
        (50, "0L", "0l", "p49r6_0L"),
        (165, "0l", "0I", "p50r10_0l"),
        (246, "3i", "3I", "p51r7_3i"),
    ):
        if idx < len(claimed) and claimed[idx] == old:
            claimed[idx] = new
            claimed_edits.append({"i": idx, "old": old, "new": new, "tag": tag, "applied": True})
        else:
            claimed_edits.append(
                {
                    "i": idx,
                    "old": old,
                    "new": new,
                    "tag": tag,
                    "applied": False,
                    "actual": claimed[idx] if idx < len(claimed) else None,
                }
            )
    print("claimed edits", claimed_edits)

    prefix = unsolved_flat()[:900]
    hits: list[dict] = []
    tested = [0]
    variants = {"rtkd_raw": raw_toks, "artwaste_4fix": claimed}
    grid_meta = {}
    for name, toks in variants.items():
        try:
            vals = decode60(toks)
        except ValueError as e:
            print("decode fail", name, e)
            continue
        blob = bytes(vals)
        grid_meta[name] = {
            "n": len(vals),
            "min": min(vals),
            "max": max(vals),
            "sha256": hashlib.sha256(blob).hexdigest(),
            "n_unique": len(set(vals)),
        }
        print(name, grid_meta[name])
        test_bytes_as_key(f"grid/{name}", blob, prefix, hits, tested)

    # ICC + DQT from a few pages (should be identical)
    jpeg_meta = {}
    for onion in (0, 15, 49, 56, 57):
        path = object_path(triage[f"{onion}.jpg"]["sha256"])
        data = path.read_bytes()
        segs = jpeg_segments(data)
        jpeg_meta[str(onion)] = {
            "icc_len": len(segs["icc"]),
            "icc_sha": hashlib.sha256(segs["icc"]).hexdigest() if segs["icc"] else None,
            "dqt_len": len(segs["dqt"]),
            "dqt_sha": hashlib.sha256(segs["dqt"]).hexdigest() if segs["dqt"] else None,
            "com_len": len(segs["com"]),
            "icc_ascii_head": segs["icc"][:80].decode("latin-1", "replace") if segs["icc"] else "",
        }
        print("jpeg", onion, jpeg_meta[str(onion)])
    # seeds from page 0 (shared profile)
    path0 = object_path(triage["0.jpg"]["sha256"])
    segs0 = jpeg_segments(path0.read_bytes())
    for label, blob in (("icc", segs0["icc"]), ("dqt", segs0["dqt"])):
        test_bytes_as_key(label, blob, prefix, hits, tested)
        # also try ICC description string only
    if segs0["icc"]:
        # description tag often contains Artifex...
        desc = b"Artifex Software sRGB ICC Profile"
        test_bytes_as_key("icc_desc_ascii", desc, prefix, hits, tested)

    # heading segmentation controls + red pages
    heading_pages = [0, 3, 6, 7, 8, 15, 23, 27, 33, 39, 40, 53, 54, 56, 57]
    overlays = []
    heading_hits = []
    for onion in heading_pages:
        path = object_path(triage[f"{onion}.jpg"]["sha256"])
        seg = segment_runes(path)
        if onion <= 55:
            n_trans = len(idxs_of(15 + onion))
        elif onion == 56:
            n_trans = 85
        else:
            n_trans = 95
        rec = {"onion": onion, "trans": n_trans, **seg}
        overlays.append(rec)
        first_red = seg["red_runs"][0]["len"] if seg["red_runs"] else 0
        print(
            f"glyph {onion:2d} trans={n_trans:4d} cc={seg['n']:4d} red={seg['n_red']:3d} "
            f"first_red={first_red} lines={seg['line_counts'][:10]}"
        )
        if onion <= 55:
            for run in seg["red_runs"]:
                if 3 <= run["len"] <= 34 and run["start"] <= 2:
                    heading_hits.extend(attack_heading(onion, run["len"]))

    controls = {
        "p57_glyphs_ok": any(o["onion"] == 57 and abs(o["n"] - 95) <= 8 for o in overlays),
        "p57_first_red_7": any(o["onion"] == 57 and o["red_runs"] and o["red_runs"][0]["len"] == 7 for o in overlays),
        "p56_glyphs_ok": any(o["onion"] == 56 and abs(o["n"] - 85) <= 8 for o in overlays),
        "p56_first_red_5": any(o["onion"] == 56 and o["red_runs"] and o["red_runs"][0]["len"] == 5 for o in overlays),
    }
    print("controls", controls)
    print("heading vocab hits", heading_hits)
    print("key hits", len(hits), "tested", tested[0])

    (OUT / "result.json").write_text(
        json.dumps(
            {
                "grid_meta": grid_meta,
                "claimed_edits": claimed_edits,
                "bar_counts": {k: len(v) for k, v in bar_report.items()},
                "bar_heights": {k: [b["h"] for b in v] for k, v in bar_report.items()},
                "jpeg_meta": jpeg_meta,
                "tested": tested[0],
                "hits": hits,
                "overlays": overlays,
                "controls": controls,
                "heading_hits": heading_hits,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
