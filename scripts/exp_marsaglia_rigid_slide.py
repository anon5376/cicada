#!/usr/bin/env python3
"""Rigid OTP slide of retrieved Marsaglia files across every byte offset.

Skip-aware beam cannot sweep 10 MB. This tests the simpler claim: unsolved
runes are (ct ± pad[offset:]) mod 29 with no rejection filter.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from cicada.liber_primus.gematria import Gematria  # noqa: E402
from cicada.paths import ROOT as CICADA_ROOT  # noqa: E402
from cicada.scoring import score_candidate  # noqa: E402
from cicada.store import get_bytes  # noqa: E402
from exp_skipaware_sha_ctr import keep  # noqa: E402
from exp_skipaware_marsaglia import idxs_of, prefix  # noqa: E402

GP = Gematria()
Q = 29
OUT = CICADA_ROOT / "experiments" / "EXP-LP-MARSAGLIA-RIGID-SLIDE-001"
PREV = CICADA_ROOT / "experiments" / "EXP-LP-SKIPAWARE-MARSAGLIA-001" / "result.json"

# TH=2, E=18 → latin THE; A=24 N=9 D=23; I=10 N=9 G=6
TH, E, A, N, D, I, G = 2, 18, 24, 9, 23, 10, 6
CHUNK = 250_000
WIN = 120


def slide_hits(ct: np.ndarray, pad: np.ndarray, op: str) -> list[tuple[int, int, int, int]]:
    n = len(ct)
    limit = len(pad) - n
    out: list[tuple[int, int, int, int]] = []
    for start in range(0, limit, CHUNK):
        end = min(start + CHUNK, limit)
        windows = np.lib.stride_tricks.sliding_window_view(pad[start : end + n - 1], n)
        if op == "sub":
            pt = (ct - windows) % Q
        elif op == "add":
            pt = (ct + windows) % Q
        else:
            pt = (windows - ct) % Q
        the = ((pt[:, :-1] == TH) & (pt[:, 1:] == E)).sum(axis=1)
        ands = ((pt[:, :-2] == A) & (pt[:, 1:-1] == N) & (pt[:, 2:] == D)).sum(axis=1)
        ings = ((pt[:, :-2] == I) & (pt[:, 1:-1] == N) & (pt[:, 2:] == G)).sum(axis=1)
        sel = np.where((the >= 3) | ((the >= 2) & (ands + ings >= 1)))[0]
        for i in sel:
            out.append((int(start + i), int(the[i]), int(ands[i]), int(ings[i])))
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    prev = json.loads(PREV.read_text(encoding="utf-8"))
    p400 = prefix(400)
    ct = np.array(p400[:WIN], dtype=np.int16)
    plant_lat = (
        "THEPRIMESARESACREDTHETOTIENTFVNCTIANISSACREDALLTHNGSSHOVLDBEENCRYPTEDAWARNNGBELIEVENOTHNG"
    )
    plant_pt = np.array(GP.encode_latin_key(plant_lat), dtype=np.int16)
    first = get_bytes(prev["fetched"][0]["sha256"])
    pad0 = np.frombuffer(first, dtype=np.uint8).astype(np.int16) % Q
    plant_ct = (plant_pt + pad0[: len(plant_pt)]) % Q
    plant_found = slide_hits(plant_ct, pad0, "sub")
    plant = {
        "file": prev["fetched"][0]["name"],
        "found_offset0": any(off == 0 for off, *_ in plant_found),
        "n_hits": len(plant_found),
        "head_hits": plant_found[:8],
        "ok": any(off == 0 for off, *_ in plant_found),
    }
    print("plant", plant, flush=True)

    candidates = []
    keeps = []
    scanned = 0
    for rec in prev["fetched"]:
        data = get_bytes(rec["sha256"])
        pad = np.frombuffer(data, dtype=np.uint8).astype(np.int16) % Q
        for op in ("sub", "add", "beau"):
            hits = slide_hits(ct, pad, op)
            scanned += max(0, len(pad) - WIN)
            print(f"{rec['name']} {op} hits={len(hits)}", flush=True)
            for off, the, ands, ings in hits:
                full_ct = p400
                ks = [int(pad[(off + i) % len(pad)]) for i in range(len(full_ct))]
                if op == "sub":
                    pt = [(full_ct[i] - ks[i]) % Q for i in range(len(full_ct))]
                elif op == "add":
                    pt = [(full_ct[i] + ks[i]) % Q for i in range(len(full_ct))]
                else:
                    pt = [(ks[i] - full_ct[i]) % Q for i in range(len(full_ct))]
                lat = GP.latin_stream(pt)
                sc = score_candidate(pt, lat)
                row = {
                    "file": rec["name"],
                    "op": op,
                    "offset": off,
                    "the": the,
                    "and": ands,
                    "ing": ings,
                    "head": lat[:80],
                    **sc,
                }
                candidates.append(row)
                print("CAND", rec["name"], op, off, lat[:48], sc["trigram_per_100"], flush=True)
                if keep(sc, len(pt)):
                    keeps.append(row)
                    print("KEEP", row, flush=True)

    out = {
        "plant": plant,
        "window": WIN,
        "offsets_scanned": scanned,
        "candidates": candidates,
        "keeps": keeps,
        "threshold": "THE-pairs>=3 or (THE>=2 and AND+ING>=1) on first 120 runes, then full prefix400 score",
    }
    (OUT / "result.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("scanned", scanned, "cands", len(candidates), "keeps", len(keeps), flush=True)


if __name__ == "__main__":
    main()
