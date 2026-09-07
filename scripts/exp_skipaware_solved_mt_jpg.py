#!/usr/bin/env python3
"""Skip-aware: solved-page plains as pads; classic MT19937 init; raw JPEG bytes.

Solved plains were Porta/Nicodemus only. JPEG SHAs were CTR seeds, not raw pads.
Python3 random.Random was tested; this is C/Py2-style init_genrand / init_by_array.
"""
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
from exp_skipaware_sha_ctr import beam_decode, encrypt_reject, keep, sha256_ctr  # noqa: E402

GP = Gematria()
Q = 29
OUT = CICADA_ROOT / "experiments" / "EXP-LP-SKIPAWARE-SOLVED-MT-JPG-001"
N, M = 624, 397
MAG = 0x9908B0DF
UPPER, LOWER = 0x80000000, 0x7FFFFFFF
JPG = {
    "jpg0": "197e1e153958b9a2736b09c10eea7d8bb00e0632fd22a8d9606840becc79942e",
    "jpg15": "5543cfce96493b86eece3195b3f5ea6e779ff41551676600b0c2479fc18c0ec5",
    "jpg56": "a4c1c9ae1246c3197fc1d7bd0155cbc97f60d4bba84a104d45f180feab1814dc",
    "jpg57": "1dabc100ddbf1fc49715219636984eb6ad96a2bd8035e196c12e66db77a1077b",
}
MT_SEEDS = (0, 1, 15, 56, 57, 3301, 2012, 2013, 2014, 2017, 1295, 1033, 0x7A35090F)


def mt_init_genrand(seed: int) -> list[int]:
    mt = [0] * N
    mt[0] = seed & 0xFFFFFFFF
    for i in range(1, N):
        mt[i] = (1812433253 * (mt[i - 1] ^ (mt[i - 1] >> 30)) + i) & 0xFFFFFFFF
    return mt


def mt_extract(mt: list[int], idx: list[int]) -> int:
    i = idx[0]
    if i >= N:
        for k in range(N):
            y = (mt[k] & UPPER) | (mt[(k + 1) % N] & LOWER)
            mt[k] = mt[(k + M) % N] ^ (y >> 1) ^ (MAG if y & 1 else 0)
        i = 0
    y = mt[i]
    idx[0] = i + 1
    y ^= y >> 11
    y ^= (y << 7) & 0x9D2C5680
    y ^= (y << 15) & 0xEFC60000
    y ^= y >> 18
    return y & 0xFFFFFFFF


def mt_stream(seed: int, n: int) -> list[int]:
    mt = mt_init_genrand(seed)
    idx = [N]
    return [mt_extract(mt, idx) % Q for _ in range(n)]


def pad_repeat(ix: list[int], n: int) -> list[int]:
    if not ix:
        return []
    return (ix * (n // len(ix) + 1))[:n]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    plant_pt = GP.encode_latin_key(
        "THEPRIMESARESACREDTHETOTIENTFVNCTIANISSACREDALLTHNGSSHOVLDBEENCRYPTEDAWARNNGBELIEVENOTHNG"
    )
    pks = mt_stream(3301, len(plant_pt) * 4)
    rec = beam_decode(encrypt_reject(plant_pt, pks)[0], pks)
    agree = sum(a == b for a, b in zip(rec, plant_pt)) / len(plant_pt) if rec else 0.0
    plant = {"agree": round(agree, 4), "ok": agree >= 0.95, "family": "mt_init_genrand"}
    print("plant", plant, flush=True)

    plains = []
    concat: list[int] = []
    for fx in load_fixtures():
        replay = replay_fixture(fx)
        lat = replay.get("got_normalized") or fx.get("expected_latin_normalized") or ""
        if not lat:
            continue
        ix = GP.encode_latin_key(lat)
        plains.append((fx["stage_id"], ix))
        concat.extend(ix)
    plains.append(("solved_concat", concat))
    print("plains", [(n, len(ix)) for n, ix in plains], flush=True)

    targets = [("prefix400", prefix(400)), ("split015", idxs_of(15))]
    hits = []
    tested = 0
    samples = []

    for pname, ix in plains:
        for span, ct in targets:
            need = len(ct) * 4
            for mode, ks in (
                ("repeat_pad", pad_repeat(ix, need)),
                ("sha256_ctr", sha256_ctr(pname.encode(), need)),
            ):
                tested += 1
                pt = beam_decode(ct, ks)
                lat = GP.latin_stream(pt)
                sc = score_candidate(pt, lat)
                row = {"src": pname, "span": span, "mode": mode, "head": lat[:80], **sc}
                if tested <= 3:
                    print(f"beam {pname} {span} {mode} tri={sc['trigram_per_100']:.2f} {lat[:36]}", flush=True)
                    samples.append(row)
                if keep(sc, len(pt)):
                    hits.append(row)
                    print("KEEP", row, flush=True)

    for seed in MT_SEEDS:
        for span, ct in targets:
            tested += 1
            pt = beam_decode(ct, mt_stream(seed, len(ct) * 4))
            lat = GP.latin_stream(pt)
            sc = score_candidate(pt, lat)
            row = {"src": f"mt:{seed}", "span": span, "mode": "init_genrand", "head": lat[:80], **sc}
            if seed == 3301 and span == "prefix400":
                print(f"beam mt:3301 {span} tri={sc['trigram_per_100']:.2f} {lat[:36]}", flush=True)
                samples.append(row)
            if keep(sc, len(pt)):
                hits.append(row)
                print("KEEP", row, flush=True)

    for label, sha in JPG.items():
        if not object_path(sha).exists():
            print("missing", label, flush=True)
            continue
        data = get_bytes(sha)
        ks0 = [b % Q for b in data[: max(len(prefix(400)), len(idxs_of(15))) * 4]]
        for span, ct in targets:
            tested += 1
            pt = beam_decode(ct, ks0[: len(ct) * 4])
            lat = GP.latin_stream(pt)
            sc = score_candidate(pt, lat)
            row = {"src": label, "span": span, "mode": "raw_jpeg_mod29", "head": lat[:80], **sc}
            if keep(sc, len(pt)):
                hits.append(row)
                print("KEEP", row, flush=True)

    print("tested", tested, "keeps", len(hits), flush=True)
    (OUT / "result.json").write_text(
        json.dumps({"plant": plant, "tested": tested, "keeps": hits, "samples": samples}, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
