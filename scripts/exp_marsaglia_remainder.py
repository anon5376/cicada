#!/usr/bin/env python3
"""Remaining Marsaglia bits.* + germany.bit: skip-aware at 0 / SHA, rigid all offsets."""
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
from exp_marsaglia_rigid_slide import slide_hits, WIN  # noqa: E402
from exp_skipaware_marsaglia import (  # noqa: E402
    WAYBACK_ALT,
    fetch_one,
    idxs_of,
    pad_5bit,
    pad_bytes,
    prefix,
)
from exp_skipaware_sha_ctr import beam_decode, encrypt_reject, keep, sha256_ctr  # noqa: E402

GP = Gematria()
Q = 29
OUT = CICADA_ROOT / "experiments" / "EXP-LP-MARSAGLIA-REMAINDER-001"
DONE = {"bits.01", "bits.15", "bits.33", "bits.56", "canada.bit", "calif.bit"}
FILES = [f"bits.{i:02d}" for i in range(1, 61) if f"bits.{i:02d}" not in DONE] + ["germany.bit"]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        if name.startswith("bits."):
            WAYBACK_ALT.setdefault(name, "bit." + name.split(".", 1)[1])

    fetched, fetch_errors = [], []
    for name in FILES:
        try:
            fetched.append(fetch_one(name))
        except Exception as exc:  # noqa: BLE001
            fetch_errors.append({"name": name, "error": str(exc)})
            print("FAIL", name, exc, flush=True)
    print("fetched", len(fetched), "errors", len(fetch_errors), flush=True)
    if not fetched:
        raise SystemExit(f"no files: {fetch_errors}")

    plant_pt = GP.encode_latin_key(
        "THEPRIMESARESACREDTHETOTIENTFVNCTIANISSACREDALLTHNGSSHOVLDBEENCRYPTEDAWARNNGBELIEVENOTHNG"
    )
    first = get_bytes(fetched[0]["sha256"])
    pks = pad_bytes(first, 0, len(plant_pt) * 4)
    plant_ct, _ = encrypt_reject(plant_pt, pks)
    rec = beam_decode(plant_ct, pks)
    agree = sum(a == b for a, b in zip(rec, plant_pt)) / len(plant_pt) if rec else 0.0
    plant = {"source": fetched[0]["name"], "agree": round(agree, 4), "ok": agree >= 0.95}
    print("plant", plant, flush=True)

    p400 = prefix(400)
    p15 = idxs_of(15)
    ct_np = np.array(p400[:WIN], dtype=np.int16)
    beam_keeps, slide_keeps = [], []
    beam_tested = 0
    scanned = 0
    sieve_hits = 0
    top_cands = []

    for rec in fetched:
        data = get_bytes(rec["sha256"])
        for span, ct in (("prefix400", p400), ("split015", p15)):
            need = len(ct) * 4
            for mode, ks in (
                ("byte29@0", pad_bytes(data, 0, need)),
                ("bit5@0", pad_5bit(data, 0, need)),
                ("sha256_ctr", sha256_ctr(bytes.fromhex(rec["sha256"]), need)),
            ):
                beam_tested += 1
                pt = beam_decode(ct, ks)
                lat = GP.latin_stream(pt)
                sc = score_candidate(pt, lat)
                if keep(sc, len(pt)):
                    row = {"file": rec["name"], "span": span, "mode": mode, "head": lat[:80], **sc}
                    beam_keeps.append(row)
                    print("KEEP-BEAM", rec["name"], span, mode, lat[:40], flush=True)
        pad = np.frombuffer(data, dtype=np.uint8).astype(np.int16) % Q
        for op in ("sub", "add", "beau"):
            hits = slide_hits(ct_np, pad, op)
            scanned += max(0, len(pad) - WIN)
            sieve_hits += len(hits)
            print(f"{rec['name']} {op} sieve={len(hits)}", flush=True)
            for off, the, ands, ings in hits:
                ks = [int(pad[(off + i) % len(pad)]) for i in range(len(p400))]
                if op == "sub":
                    pt = [(p400[i] - ks[i]) % Q for i in range(len(p400))]
                elif op == "add":
                    pt = [(p400[i] + ks[i]) % Q for i in range(len(p400))]
                else:
                    pt = [(ks[i] - p400[i]) % Q for i in range(len(p400))]
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
                top_cands.append(row)
                if keep(sc, len(pt)):
                    slide_keeps.append(row)
                    print("KEEP-SLIDE", rec["name"], op, off, lat[:40], flush=True)

    top_cands.sort(key=lambda r: -r["trigram_per_100"])
    out = {
        "plant": plant,
        "fetched": [
            {"name": r["name"], "sha256": r["sha256"], "byte_length": r["byte_length"], "url": r.get("url")}
            for r in fetched
        ],
        "fetch_errors": fetch_errors,
        "beam_tested": beam_tested,
        "beam_keeps": beam_keeps,
        "offsets_scanned": scanned,
        "sieve_hits": sieve_hits,
        "slide_keeps": slide_keeps,
        "top_cands": top_cands[:15],
    }
    (OUT / "result.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        "beam", beam_tested, "beam_keeps", len(beam_keeps),
        "scanned", scanned, "sieve", sieve_hits, "slide_keeps", len(slide_keeps),
        flush=True,
    )


if __name__ == "__main__":
    main()
