#!/usr/bin/env python3
"""Skip-aware SHA-256-CTR on corpus-local seeds only tested rigidly before.

JPEG SHA (page-local), AN END hex, ICC/DQT hashes, solved-page plains, warning body.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from cicada.liber_primus.gematria import Gematria  # noqa: E402
from cicada.paths import ROOT as CICADA_ROOT  # noqa: E402
from cicada.scoring import score_candidate  # noqa: E402
from exp_anend_hash_and_p56 import EXPECTED_P56, HASH_HEX  # noqa: E402
from exp_skipaware_sha_ctr import beam_decode, keep, sha256_ctr  # noqa: E402

GP = Gematria()
PAGE_DIR = CICADA_ROOT / "corpus/normalized/rtkd_pages"
TRIAGE = CICADA_ROOT / "reports/candidates/image_triage.json"
FIXT = CICADA_ROOT / "tests/liber_primus/replay_fixtures.json"
OUT = CICADA_ROOT / "experiments" / "EXP-LP-SKIPAWARE-CORPUS-SEEDS-001"


def idxs_of(s: int) -> list[int]:
    return GP.rune_indices((PAGE_DIR / f"split_{s:03d}.txt").read_text(encoding="utf-8"))


def prefix(n: int = 400) -> list[int]:
    out: list[int] = []
    for s in range(15, 71):
        out.extend(idxs_of(s))
        if len(out) >= n:
            break
    return out[:n]


def onion_shas() -> dict[int, str]:
    rows = json.loads(TRIAGE.read_text(encoding="utf-8"))
    out = {}
    for r in rows:
        m = re.search(r"/(\d+)\.jpg$", r.get("url") or "")
        if not m or "unsolved" not in (r.get("url") or ""):
            continue
        out[int(m.group(1))] = r["sha256"]
    return out


def try_seed(label: str, seed: bytes, ct: list[int], span: str, hits: list) -> dict:
    ks = sha256_ctr(seed, len(ct) * 4)
    pt = beam_decode(ct, ks)
    lat = GP.latin_stream(pt)
    sc = score_candidate(pt, lat)
    rec = {"span": span, "seed": label, "head": lat[:80], **sc}
    if keep(sc, len(pt)):
        hits.append(rec)
        print("KEEP", label, span, lat[:48], flush=True)
    return rec


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    hits: list[dict] = []
    tested = 0
    sample = []
    p400 = prefix(400)
    p15 = idxs_of(15)

    global_seeds: list[tuple[str, bytes]] = [
        ("anend_hex", HASH_HEX.encode()),
        ("anend_raw", bytes.fromhex(HASH_HEX) if len(HASH_HEX) % 2 == 0 else bytes.fromhex(HASH_HEX + "0")),
        ("p56_plain", EXPECTED_P56.encode()),
        ("icc_sha", bytes.fromhex("942e0f66212eb8ad252706559da5007d893d7350652704f8d115d5e6074479d0")),
        ("dqt_sha", bytes.fromhex("0f81986f36a37e1309c4d4d18e2c4c6966ad7c49385ef79cbcc0bbef3ccb7a2e")),
        ("icc_hex", b"942e0f66212eb8ad252706559da5007d893d7350652704f8d115d5e6074479d0"),
        ("beware", b"Beware false paths. Always verify PGP signature from 7A35090F."),
        ("jpg15", bytes.fromhex("5543cfce96493b86eece3195b3f5ea6e779ff41551676600b0c2479fc18c0ec5")),
        ("rtkd_master", bytes.fromhex("e21743ccd9a07f3845d52a329c61b9fa69e9ca6a44ee3ba0db8f28a0d7065004")),
    ]
    for fx in json.loads(FIXT.read_text(encoding="utf-8")):
        lat = fx.get("expected_latin_normalized")
        if lat:
            global_seeds.append((fx["stage_id"], lat.encode()))

    for label, seed in global_seeds:
        for span, ct in (("prefix400", p400), ("split015", p15)):
            tested += 1
            rec = try_seed(label, seed, ct, span, hits)
            if label == "anend_hex" and span == "prefix400":
                print(f"beam {span} {label} tri={rec['trigram_per_100']:.2f} ioc={rec['ioc']:.3f} {rec['head'][:40]}", flush=True)
                sample.append(rec)

    shas = onion_shas()
    print("onion jpegs", len(shas), flush=True)
    for onion, sha in sorted(shas.items()):
        if onion > 55:
            continue
        split = 15 + onion
        path = PAGE_DIR / f"split_{split:03d}.txt"
        if not path.exists():
            continue
        ct = idxs_of(split)
        if len(ct) < 80:
            continue
        tested += 1
        rec = try_seed(f"jpg{onion}_raw", bytes.fromhex(sha), ct, f"split{split:03d}", hits)
        if onion == 0:
            print(f"beam split{split:03d} jpg0 tri={rec['trigram_per_100']:.2f} {rec['head'][:40]}", flush=True)
            sample.append(rec)

    print("tested", tested, "keeps", len(hits), flush=True)
    (OUT / "result.json").write_text(
        json.dumps({"tested": tested, "keeps": hits, "sample": sample, "n_jpeg": len(shas)}, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
