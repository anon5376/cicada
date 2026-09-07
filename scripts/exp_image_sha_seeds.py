#!/usr/bin/env python3
"""SHA-256 of each LP2 JPEG (and of the 15.jpg / 56.jpg bytes) as CTR seeds.

Page-local: decrypt that page only. Book-wide: 15.jpg hash, xor of all page
hashes, and the 56.jpg hash against the unsolved concat prefix.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cicada.liber_primus.gematria import Gematria  # noqa: E402
from cicada.paths import ROOT as CICADA_ROOT  # noqa: E402
from cicada.scoring import score_candidate  # noqa: E402

GP = Gematria()
PAGE_DIR = CICADA_ROOT / "corpus/normalized/rtkd_pages"
OUT = CICADA_ROOT / "experiments" / "EXP-LP-IMAGE-SHA-SEED-001"
TRIAGE = CICADA_ROOT / "reports/candidates/image_triage.json"


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


def object_path(sha: str) -> Path:
    return CICADA_ROOT / "corpus/objects/sha256" / sha[:2] / sha


def idxs_of(s: int) -> list[int]:
    return GP.rune_indices((PAGE_DIR / f"split_{s:03d}.txt").read_text(encoding="utf-8"))


def score_out(ct: list[int], ks: list[int], rel: str) -> dict:
    if rel == "sub":
        out = [(ct[i] - ks[i]) % 29 for i in range(len(ct))]
    elif rel == "add":
        out = [(ct[i] + ks[i]) % 29 for i in range(len(ct))]
    else:
        out = [(ks[i] - ct[i]) % 29 for i in range(len(ct))]
    latin = GP.latin_stream(out)
    sc = score_candidate(out, latin)
    sc["head"] = latin[:80]
    sc["rel"] = rel
    return sc


def keep(sc: dict, n: int) -> bool:
    return n >= 40 and sc["trigram_per_100"] >= 3.5 and 0.28 <= sc["vowelish_ratio"] <= 0.55 and sc["ioc"] >= 0.045


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    triage = [x for x in json.loads(TRIAGE.read_text()) if "unsolved" in x["url"]]
    by_name = {x["url"].rsplit("/", 1)[-1]: x for x in triage}

    hits = []
    tested = 0
    page_hashes = []
    for onion in range(58):
        item = by_name[f"{onion}.jpg"]
        digest = bytes.fromhex(item["sha256"])
        page_hashes.append(digest)
        if onion > 55:
            continue
        ix = idxs_of(15 + onion)
        if len(ix) < 30:
            continue
        # also hash of raw file bytes (same as listed sha if CAS matches)
        p = object_path(item["sha256"])
        raw = p.read_bytes() if p.exists() else digest
        file_sha = hashlib.sha256(raw).digest()
        for seed_name, seed in (("listed_sha", digest), ("file_sha", file_sha), ("name+sha", f"{onion}.jpg".encode() + digest)):
            ks = sha256_ctr(seed, len(ix))
            for rel in ("sub", "add", "beau"):
                tested += 1
                sc = score_out(ix, ks, rel)
                if keep(sc, len(ix)):
                    hits.append({"onion": onion, "seed": seed_name, **sc})
                    print("PAGE", onion, seed_name, rel, sc["trigram_per_100"], sc["head"][:60])

    concat = []
    for s in range(15, 71):
        concat.extend(idxs_of(s))
    prefix = concat[:900]
    acc = bytearray(32)
    for h in page_hashes[:56]:
        for i, b in enumerate(h):
            acc[i] ^= b
    seeds = {
        "jpg15": bytes.fromhex(by_name["15.jpg"]["sha256"]),
        "jpg56": bytes.fromhex(by_name["56.jpg"]["sha256"]),
        "jpg0": bytes.fromhex(by_name["0.jpg"]["sha256"]),
        "xor0_55": bytes(acc),
        "jpg15_bytes": hashlib.sha256(object_path(by_name["15.jpg"]["sha256"]).read_bytes()).digest(),
    }
    # printed C-grid ascii
    grid = "3258-3222-3152-3038\n3278-3299-3298-2838\n3288-3294-3296-2472\n4516-1206-708-1820"
    seeds["grid_ascii"] = hashlib.sha256(grid.encode()).digest()
    seeds["grid_nosep"] = hashlib.sha256(b"325832223152303832783299329828383288329432962472451612067081820").digest()

    for name, seed in seeds.items():
        ks = sha256_ctr(seed, len(prefix))
        for rel in ("sub", "add", "beau"):
            tested += 1
            sc = score_out(prefix, ks, rel)
            print(f"BOOK {name:16s} {rel:4s} tri={sc['trigram_per_100']:5.2f} ioc={sc['ioc']:.3f} {sc['head'][:50]}")
            if keep(sc, len(prefix)) or sc["trigram_per_100"] >= 3.2:
                hits.append({"onion": "prefix900", "seed": name, **sc})

    (OUT / "result.json").write_text(
        json.dumps({"tested": tested, "hits": hits, "n_hits": len(hits)}, indent=2) + "\n",
        encoding="utf-8",
    )
    print("tested", tested, "hits", len(hits))


if __name__ == "__main__":
    main()
