#!/usr/bin/env python3
"""Skip-aware beam on MT19937 keystreams from historically marked seeds.

Dukotah parked a 2^32 Python-2.7 MT grind. This is not that grind. It tests
whether a short, puzzle-attested seed of the same family decrypts unknown pages.
"""
from __future__ import annotations

import hashlib
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from cicada.liber_primus.gematria import Gematria  # noqa: E402
from cicada.paths import ROOT as CICADA_ROOT  # noqa: E402
from cicada.scoring import score_candidate  # noqa: E402
from exp_skipaware_marsaglia import idxs_of, prefix  # noqa: E402
from exp_skipaware_sha_ctr import beam_decode, encrypt_reject, keep  # noqa: E402

GP = Gematria()
Q = 29
OUT = CICADA_ROOT / "experiments" / "EXP-LP-SKIPAWARE-MT19937-001"


def mt_stream(seed: int, n: int) -> list[int]:
    rng = random.Random(seed)
    return [rng.randrange(Q) for _ in range(n)]


def seeds() -> list[tuple[str, int]]:
    out: list[tuple[str, int]] = []
    for n in (
        0,
        1,
        15,
        56,
        57,
        3301,
        2012,
        2013,
        2014,
        2017,
        1295,
        1033,
        0x7A35090F,
        0x57A35090,
        0x6D854CD7,
        0x181F01E5,
    ):
        out.append((f"int:{n}", n & 0xFFFFFFFF))
    for s in range(15, 71):
        out.append((f"split:{s}", s))
    for onion in range(0, 56):
        out.append((f"onion:{onion}", onion))
        out.append((f"onion+15:{onion}", onion + 15))
    for word in (b"CICADA3301", b"3301", b"DIVINITY", b"AN END", b"LIBERPRIMUS"):
        h = hashlib.sha256(word).digest()
        out.append((f"sha32:{word.decode()}", int.from_bytes(h[:4], "big")))
        out.append((f"sha32le:{word.decode()}", int.from_bytes(h[:4], "little")))
    # unique
    seen = set()
    uniq = []
    for label, seed in out:
        if seed in seen:
            continue
        seen.add(seed)
        uniq.append((label, seed))
    return uniq


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    plant_pt = GP.encode_latin_key(
        "THEPRIMESARESACREDTHETOTIENTFVNCTIANISSACREDALLTHNGSSHOVLDBEENCRYPTEDAWARNNGBELIEVENOTHNG"
    )
    pks = mt_stream(3301, len(plant_pt) * 4)
    plant_ct, _ = encrypt_reject(plant_pt, pks)
    rec = beam_decode(plant_ct, pks)
    agree = sum(a == b for a, b in zip(rec, plant_pt)) / len(plant_pt) if rec else 0.0
    plant = {"agree": round(agree, 4), "ok": agree >= 0.95, "head": GP.latin_stream(rec)[:80]}
    print("plant", plant, flush=True)

    targets = [("prefix400", prefix(400)), ("split015", idxs_of(15))]
    seed_list = seeds()
    hits = []
    tested = 0
    samples = []
    for label, seed in seed_list:
        for span, ct in targets:
            tested += 1
            pt = beam_decode(ct, mt_stream(seed, len(ct) * 4))
            lat = GP.latin_stream(pt)
            sc = score_candidate(pt, lat)
            row = {"seed": label, "value": seed, "span": span, "head": lat[:80], **sc}
            if tested <= 3 or (label == "int:3301" and span == "prefix400"):
                print(f"beam {span} {label} tri={sc['trigram_per_100']:.2f} {lat[:36]}", flush=True)
                samples.append(row)
            if keep(sc, len(pt)):
                hits.append(row)
                print("KEEP", row, flush=True)
    print("tested", tested, "keeps", len(hits), "seeds", len(seed_list), flush=True)
    (OUT / "result.json").write_text(
        json.dumps(
            {"plant": plant, "tested": tested, "keeps": hits, "n_seeds": len(seed_list), "samples": samples},
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
