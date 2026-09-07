#!/usr/bin/env python3
"""Skip-aware beam under Beaufort and add inverses (prior beams were subtract-only)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from cicada.liber_primus.gematria import Gematria  # noqa: E402
from cicada.liber_primus.gematria import first_n_primes  # noqa: E402
from cicada.paths import ROOT as CICADA_ROOT  # noqa: E402
from cicada.scoring import score_candidate  # noqa: E402
from exp_grid_icc_headings import decode60, parse_rtkd_grid  # noqa: E402
from exp_skipaware_marsaglia import idxs_of, prefix  # noqa: E402
from exp_skipaware_sha_ctr import keep, sha256_ctr  # noqa: E402

GP = Gematria()
Q = 29
OUT = CICADA_ROOT / "experiments" / "EXP-LP-SKIPAWARE-REL-INVERSES-001"
GRAMS = (
    "THE", "AND", "ING", "ENT", "ION", "HER", "FOR", "THA", "NTH", "INT",
    "TED", "RED", "ARE", "ERE", "ENC", "WAS", "HIS", "HAT", "ETH", "DTH",
)
SEEDS = [
    b"CICADA3301",
    b"3301",
    b"DIVINITY",
    b"AN END",
    b"LIBERPRIMUS",
    b"THELOSSOFDIVINITY",
    b"FIRFUMFERENFE",
    bytes.fromhex("6D854CD7933322A601C3286D181F01E57A35090F"),
]


def apply_c(p: int, k: int, rel: str) -> int:
    if rel == "sub":
        return (p + k) % Q
    if rel == "add":
        return (p - k) % Q
    return (k - p) % Q


def apply_p(c: int, k: int, rel: str) -> int:
    if rel == "sub":
        return (c - k) % Q
    if rel == "add":
        return (c + k) % Q
    return (k - c) % Q


def skip_need(prev: int, c: int, k_used: int, rel: str) -> int:
    if rel == "add":
        return (c - prev + k_used) % Q
    return (prev - c + k_used) % Q


def encrypt_reject(pt: list[int], ks: list[int], rel: str) -> list[int]:
    ct: list[int] = []
    j = 0
    prev = None
    for p in pt:
        while True:
            c = apply_c(p, ks[j], rel)
            j += 1
            if prev is None or c != prev:
                ct.append(c)
                prev = c
                break
    return ct


def beam_rel(ct: list[int], ks: list[int], rel: str, max_skip: int = 3, beam: int = 48) -> list[int]:
    beams: list[tuple[int, tuple, float, list]] = [(0, (), 0.0, [])]
    for i, c in enumerate(ct):
        prev = ct[i - 1] if i else None
        nxt: list[tuple[int, tuple, float, list]] = []
        for j, tail, sc, pt in beams:
            for s in range(1, max_skip + 1):
                j_acc = j + s - 1
                if j_acc >= len(ks):
                    continue
                p = apply_p(c, ks[j_acc], rel)
                if s > 1:
                    if prev is None:
                        continue
                    need = skip_need(prev, c, ks[j_acc], rel)
                    if any(ks[j + t] != need for t in range(s - 1)):
                        continue
                if prev is not None and c == prev and s != 1:
                    continue
                new_pt = pt + [p]
                lat_tail = GP.latin_stream(list(tail) + [p])
                add = sum(lat_tail.count(g) for g in GRAMS) - sum(
                    GP.latin_stream(list(tail)).count(g) for g in GRAMS
                )
                new_tail = (list(tail) + [p])[-4:]
                nxt.append((j_acc + 1, tuple(new_tail), sc + add, new_pt))
        if not nxt:
            for j, tail, sc, pt in beams:
                if j < len(ks):
                    nxt.append((j + 1, (apply_p(c, ks[j], rel),), sc, pt + [apply_p(c, ks[j], rel)]))
        nxt.sort(key=lambda x: -x[2])
        beams = nxt[:beam]
    return beams[0][3] if beams else []


def totient_ks(n: int) -> list[int]:
    primes = first_n_primes(n + 8)
    return [(p - 1) % Q for p in primes[:n]]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    plant_pt = GP.encode_latin_key(
        "THEPRIMESARESACREDTHETOTIENTFVNCTIANISSACREDALLTHNGSSHOVLDBEENCRYPTEDAWARNNGBELIEVENOTHNG"
    )
    plants = {}
    for rel in ("sub", "add", "beau"):
        ks = sha256_ctr(b"CICADA3301", len(plant_pt) * 4)
        rec = beam_rel(encrypt_reject(plant_pt, ks, rel), ks, rel)
        agree = sum(a == b for a, b in zip(rec, plant_pt)) / len(plant_pt) if rec else 0.0
        plants[rel] = {"agree": round(agree, 4), "ok": agree >= 0.95}
        print("plant", rel, plants[rel], flush=True)

    payload = bytes(decode60(parse_rtkd_grid()))
    streams = [("sha:" + (s.decode("ascii", "replace") if s.isascii() else s.hex()[:12]), sha256_ctr(s, 2000)) for s in SEEDS]
    streams.append(("totient", totient_ks(2000)))
    streams.append(("payload_mod29", [b % Q for b in payload] * 8))

    targets = [("prefix400", prefix(400)), ("split015", idxs_of(15))]
    hits = []
    tested = 0
    samples = []
    for sname, ks0 in streams:
        for rel in ("add", "beau"):
            for span, ct in targets:
                tested += 1
                pt = beam_rel(ct, ks0[: len(ct) * 4], rel)
                lat = GP.latin_stream(pt)
                sc = score_candidate(pt, lat)
                row = {"stream": sname, "rel": rel, "span": span, "head": lat[:80], **sc}
                if tested <= 4:
                    print(f"beam {sname} {rel} {span} tri={sc['trigram_per_100']:.2f} {lat[:32]}", flush=True)
                    samples.append(row)
                if keep(sc, len(pt)):
                    hits.append(row)
                    print("KEEP", row, flush=True)

    print("tested", tested, "keeps", len(hits), flush=True)
    (OUT / "result.json").write_text(
        json.dumps({"plants": plants, "tested": tested, "keeps": hits, "samples": samples}, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
