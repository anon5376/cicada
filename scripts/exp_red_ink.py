#!/usr/bin/env python3
"""Measure red-ink regions on retrieved LP2 JPEGs (heading / rubric channel)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cicada.paths import ROOT as CICADA_ROOT  # noqa: E402

OUT = CICADA_ROOT / "experiments" / "EXP-LP-RED-INK-001"
TRIAGE = CICADA_ROOT / "reports/candidates/image_triage.json"


def object_path(sha: str) -> Path:
    return CICADA_ROOT / "corpus/objects/sha256" / sha[:2] / sha


def red_mask(arr: np.ndarray) -> np.ndarray:
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    # artwaste: bimodal, red-through vs no red
    return (r.astype(np.int16) - np.maximum(g, b).astype(np.int16)) > 40


def analyze(path: Path) -> dict:
    im = Image.open(path).convert("RGB")
    arr = np.asarray(im)
    h, w = arr.shape[:2]
    m = red_mask(arr)
    ys, xs = np.where(m)
    rec = {
        "path": str(path),
        "w": w,
        "h": h,
        "red_px": int(m.sum()),
        "red_frac": float(m.mean()),
    }
    if len(xs) == 0:
        rec["bbox"] = None
        return rec
    rec["bbox"] = [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]
    # row occupancy: which vertical bands have red
    row_frac = m.mean(axis=1)
    red_rows = np.where(row_frac > 0.002)[0]
    rec["red_row_span"] = [int(red_rows[0]), int(red_rows[-1])] if len(red_rows) else None
    rec["n_red_rows"] = int(len(red_rows))
    return rec


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    triage = json.loads(TRIAGE.read_text(encoding="utf-8"))
    rows = []
    for item in triage:
        url = item["url"]
        if "liber-primus__images--unsolved" not in url:
            continue
        name = url.rsplit("/", 1)[-1]
        sha = item["sha256"]
        p = object_path(sha)
        if not p.exists():
            rows.append({"name": name, "sha256": sha, "status": "MISSING"})
            continue
        rec = analyze(p)
        rec.update({"name": name, "sha256": sha, "status": "OK"})
        rows.append(rec)
        print(f"{name:8s} red_px={rec.get('red_px', 0):7d} frac={rec.get('red_frac', 0):.4f} bbox={rec.get('bbox')} span={rec.get('red_row_span')}")
    (OUT / "red_map.json").write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    present = [r for r in rows if r["status"] == "OK"]
    missing = [r["name"] for r in rows if r["status"] == "MISSING"]
    print("analyzed", len(present), "missing", len(missing))


if __name__ == "__main__":
    main()
