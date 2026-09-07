#!/usr/bin/env python3
"""Skip-aware beam on CAS books that were only rigid-slid as Vigenere pads.

Rigid running-key slides of a filtered key score as noise. Offset 0 and a
short marked-offset ladder through the plant-validated beam is the unused test.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from cicada.liber_primus.gematria import Gematria  # noqa: E402
from cicada.paths import ROOT as CICADA_ROOT  # noqa: E402
from cicada.scoring import score_candidate  # noqa: E402
from cicada.store import get_bytes, object_path  # noqa: E402
from exp_skipaware_marsaglia import idxs_of, prefix  # noqa: E402
from exp_skipaware_sha_ctr import beam_decode, encrypt_reject, keep  # noqa: E402

GP = Gematria()
Q = 29
OUT = CICADA_ROOT / "experiments" / "EXP-LP-SKIPAWARE-CAS-RUNKEYS-001"
OFFSETS = (0, 15, 56, 3301, 2012, 2014)
BOOKS = {
    "kjv": "a681fbe6e2fc77d72d8d9cdb72ec81133cbdc17ecfd1f9449fb6d9310093f42b",
    "shakespeare": "7c87c9da9ad1c94545cd5db555ca1fc7ce982182ad9e1723dfa4f9670e0f40c4",
    "quixote": "69ef241e632ef4fba882bde06ad31ecb395d865b11028cc046c4d253f4cf118e",
    "moby": "f17ab08e0ad8c6e43d1e85e3cdae4e1b617ae35069cee7db8dcd457c87b1ec76",
    "ulysses": "d432d18d2535a28e1d448d9a91d25a167acf82ce19ea4fec9dc57d4949a8e169",
    "canterbury": "433661fd210e035153a0121e2cc3bc8ac467f94ab8cbebe42054cf56220ab4ed",
    "faust": "29fcc1c9ac6816c456ea8365629f9c87e45c4fb9776f15406c9d4a91afe91cb2",
    "alice": "0f9ea0b148d553177962a25edd2f56d36342c22576a3253a127b4fbeffa5687d",
    "inferno": "be0cbb09f8090dc9f182a7f2f834f3d6068fced67d11271045edcc7a1149d66c",
    "plost": "93ec3b4c8ca9ef0ae0438823fc5ec6105029afdf4303c97779123fd80954492c",
    "kafka": "c9f7245e700dc729a652166b69eab4b8cba02006c14baf5e081b039507aa7853",
}


def encode_stream(text: str) -> list[int]:
    compact = "".join(ch for ch in text.upper() if ch.isascii() and ch.isalpha() and ch != "Q")
    return GP.encode_latin_key(compact) if compact else []


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    hays = {}
    missing = []
    for name, sha in BOOKS.items():
        path = object_path(sha)
        if not path.exists():
            missing.append(name)
            continue
        raw = get_bytes(sha).decode("utf-8", "replace")
        ix = encode_stream(raw)
        if len(ix) < 400:
            missing.append(f"{name}:only{len(ix)}")
            continue
        hays[name] = ix
        print("hay", name, len(ix), flush=True)

    first = next(iter(hays.values()))
    plant_pt = GP.encode_latin_key(
        "THEPRIMESARESACREDTHETOTIENTFVNCTIANISSACREDALLTHNGSSHOVLDBEENCRYPTEDAWARNNGBELIEVENOTHNG"
    )
    pks = first[: len(plant_pt) * 4]
    plant_ct, _ = encrypt_reject(plant_pt, pks)
    rec = beam_decode(plant_ct, pks)
    agree = sum(a == b for a, b in zip(rec, plant_pt)) / len(plant_pt) if rec else 0.0
    plant = {"agree": round(agree, 4), "ok": agree >= 0.90, "books": sorted(hays)}
    print("plant", plant, flush=True)

    targets = [("prefix400", prefix(400)), ("split015", idxs_of(15))]
    hits = []
    tested = 0
    samples = []
    for name, hay in hays.items():
        for off in OFFSETS:
            if off >= len(hay):
                continue
            stream = hay[off:]
            for span, ct in targets:
                need = len(ct) * 4
                if len(stream) < need:
                    continue
                tested += 1
                pt = beam_decode(ct, stream[:need])
                lat = GP.latin_stream(pt)
                sc = score_candidate(pt, lat)
                row = {"book": name, "offset": off, "span": span, "head": lat[:80], **sc}
                if tested <= 3 or (name == "kjv" and off == 0 and span == "prefix400"):
                    print(f"beam {name} @{off} {span} tri={sc['trigram_per_100']:.2f} {lat[:36]}", flush=True)
                    samples.append(row)
                if keep(sc, len(pt)):
                    hits.append(row)
                    print("KEEP", row, flush=True)

    print("tested", tested, "keeps", len(hits), "books", len(hays), "missing", missing, flush=True)
    (OUT / "result.json").write_text(
        json.dumps(
            {
                "plant": plant,
                "tested": tested,
                "keeps": hits,
                "samples": samples,
                "missing": missing,
                "offsets": list(OFFSETS),
                "n_books": len(hays),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
