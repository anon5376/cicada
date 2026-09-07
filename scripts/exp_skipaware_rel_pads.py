#!/usr/bin/env python3
"""Add/Beaufort skip-aware on motivated pads previously beamed subtract-only."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from cicada.liber_primus.fixtures import load_fixtures, replay_fixture  # noqa: E402
from cicada.liber_primus.gematria import Gematria  # noqa: E402
from cicada.paths import ROOT as CICADA_ROOT  # noqa: E402
from cicada.scoring import score_candidate  # noqa: E402
from cicada.store import get_bytes, object_path  # noqa: E402
from exp_skipaware_marsaglia import idxs_of, prefix  # noqa: E402
from exp_skipaware_rel_inverses import beam_rel, encrypt_reject  # noqa: E402
from exp_skipaware_sha_ctr import keep, sha256_ctr  # noqa: E402

GP = Gematria()
Q = 29
OUT = CICADA_ROOT / "experiments" / "EXP-LP-SKIPAWARE-REL-PADS-001"
PADS = {
    "kjv": "a681fbe6e2fc77d72d8d9cdb72ec81133cbdc17ecfd1f9449fb6d9310093f42b",
    "shakespeare": "7c87c9da9ad1c94545cd5db555ca1fc7ce982182ad9e1723dfa4f9670e0f40c4",
    "cicada_wiki": "ade52e6f3e1849089803d46269731b7302f0fe651783c02152aca92c219f371e",
    "how_solved_wb": "ca92a05a645c",  # prefix; resolve
    "bits01": "32d18ec597c9bbc40791a039d1a217a0cd5db322db400b095f9e85c708e479f7",
    "gall1": "4a5771c209e09e0fc41259189885ed6ed5d1d3f59d4d6be22c3d463fc73a5755",
}


def encode_stream(text: str) -> list[int]:
    compact = "".join(ch for ch in text.upper() if ch.isascii() and ch.isalpha() and ch != "Q")
    return GP.encode_latin_key(compact) if compact else []


def resolve(pref: str) -> bytes | None:
    if len(pref) == 64 and object_path(pref).exists():
        return get_bytes(pref)
    cas = CICADA_ROOT / "corpus/objects/sha256" / pref[:2]
    if not cas.exists():
        return None
    xs = list(cas.glob(pref + "*"))
    return xs[0].read_bytes() if xs else None


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    streams = {}
    for name, sha in PADS.items():
        raw = resolve(sha)
        if raw is None:
            print("miss", name, flush=True)
            continue
        if name == "bits01":
            streams[name] = [b % Q for b in raw[:8000]]
        else:
            ix = encode_stream(raw.decode("utf-8", "replace"))
            if len(ix) >= 400:
                streams[name] = ix[:8000]
                print("pad", name, len(ix), flush=True)
    for fx in load_fixtures():
        lat = replay_fixture(fx).get("got_normalized") or ""
        if lat:
            streams["plain:" + fx["stage_id"]] = GP.encode_latin_key(lat)

    plant_pt = GP.encode_latin_key(
        "THEPRIMESARESACREDTHETOTIENTFVNCTIANISSACREDALLTHNGSSHOVLDBEENCRYPTEDAWARNNGBELIEVENOTHNG"
    )
    ks = sha256_ctr(b"CICADA3301", len(plant_pt) * 4)
    plants = {}
    for rel in ("add", "beau"):
        rec = beam_rel(encrypt_reject(plant_pt, ks, rel), ks, rel)
        agree = sum(a == b for a, b in zip(rec, plant_pt)) / len(plant_pt) if rec else 0.0
        plants[rel] = {"agree": round(agree, 4), "ok": agree >= 0.95}
        print("plant", rel, plants[rel], flush=True)

    targets = [("prefix400", prefix(400)), ("split015", idxs_of(15))]
    hits = []
    tested = 0
    samples = []
    for sname, hay in streams.items():
        for rel in ("add", "beau"):
            for span, ct in targets:
                need = len(ct) * 4
                ks = (hay * (need // max(1, len(hay)) + 1))[:need]
                tested += 1
                pt = beam_rel(ct, ks, rel)
                lat = GP.latin_stream(pt)
                sc = score_candidate(pt, lat)
                row = {"pad": sname, "rel": rel, "span": span, "head": lat[:80], **sc}
                if tested <= 3:
                    print(f"beam {sname} {rel} {span} tri={sc['trigram_per_100']:.2f} {lat[:32]}", flush=True)
                    samples.append(row)
                if keep(sc, len(pt)):
                    hits.append(row)
                    print("KEEP", row, flush=True)

    print("tested", tested, "keeps", len(hits), "pads", list(streams), flush=True)
    (OUT / "result.json").write_text(
        json.dumps(
            {"plants": plants, "tested": tested, "keeps": hits, "samples": samples, "pads": list(streams)},
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
