#!/usr/bin/env python3
"""Skip-aware SHA-256-CTR: plant-and-recover, then seed dictionary on unsolved runes.

Rigid CTR was already null (EXP-LP-UNKNOWN-NEXT-001). Dukotah notes a rejection
filter desynchronizes the key pointer; the correct seed then scores as noise
unless you beam over consume-1/2/3.
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
Q = 29
PAGE_DIR = CICADA_ROOT / "corpus/normalized/rtkd_pages"
OUT = CICADA_ROOT / "experiments" / "EXP-LP-SKIPAWARE-SHA-CTR-001"

SEEDS = [
    b"CICADA3301",
    b"3301",
    b"DIVINITY",
    b"CICADA",
    b"AN END",
    b"ANEND",
    b"liber primus",
    b"LIBERPRIMUS",
    b"THELOSSOFDIVINITY",
    b"FIRFUMFERENFE",
    b"INSTAR",
    b"CIRCUMFERENCE",
    b"PILGRIM",
    b"PRIMES",
    b"WELCOME",
    b"KOAN",
    b"TOTIENT",
    b"6D854CD7933322A601C3286D181F01E57A35090F",
    b"7A35090F",
    b"gy3hoy2zizvuzvdb",
    b"wisdom",
    b"folly",
    b"parable",
    b"deep web",
    b"seek within",
]


def sha256_ctr(seed: bytes, n: int, start: int = 0) -> list[int]:
    out: list[int] = []
    i = start
    while len(out) < n:
        d = hashlib.sha256(seed + i.to_bytes(4, "big")).digest()
        for b in d:
            out.append(b % Q)
            if len(out) >= n:
                break
        i += 1
    return out


def encrypt_reject(pt: list[int], ks: list[int]) -> tuple[list[int], list[int]]:
    """Hard reject when tentative CT repeats previous. Returns (ct, consumed_js)."""
    ct: list[int] = []
    used: list[int] = []
    j = 0
    prev = None
    for p in pt:
        while True:
            if j >= len(ks):
                raise RuntimeError("keystream exhausted")
            c = (p + ks[j]) % Q
            j += 1
            if prev is None or c != prev:
                ct.append(c)
                used.append(j - 1)
                prev = c
                break
    return ct, used


def beam_decode(ct: list[int], ks: list[int], max_skip: int = 3, beam: int = 48) -> list[int]:
    """Search consume lengths 1..max_skip. Score = English trigram hits (greedy keep)."""
    grams = (
        "THE", "AND", "ING", "ENT", "ION", "HER", "FOR", "THA", "NTH", "INT",
        "TED", "RED", "ARE", "ERE", "ENC", "WAS", "HIS", "HAT", "ETH", "DTH",
        "OTH", "ITH", "VER", "ALL", "THN", "NCR", "YPT", "WAR", "NOT", "BEL",
    )
    # state: (j, pt_so_far_tuple_tail, score)
    # keep tail of 4 indices for trigram latin
    beams: list[tuple[int, tuple, float, list]] = [(0, (), 0.0, [])]
    for i, c in enumerate(ct):
        prev = ct[i - 1] if i else None
        nxt: list[tuple[int, tuple, float, list]] = []
        for j, tail, sc, pt in beams:
            for s in range(1, max_skip + 1):
                j_acc = j + s - 1
                if j_acc >= len(ks):
                    continue
                p = (c - ks[j_acc]) % Q
                if s > 1:
                    if prev is None:
                        continue
                    need = (prev - c + ks[j_acc]) % Q
                    if any(ks[j + t] != need for t in range(s - 1)):
                        continue
                if prev is not None and c == prev and s != 1:
                    continue
                new_pt = pt + [p]
                lat_tail = GP.latin_stream(list(tail) + [p])
                add = sum(lat_tail.count(g) for g in grams) - sum(
                    GP.latin_stream(list(tail)).count(g) for g in grams
                )
                compact = "".join(ch for ch in lat_tail if ch.isalpha())
                if compact:
                    add += 0.08 * sum(compact[-1] in "AEIOUY" for _ in (0,))
                new_tail = (list(tail) + [p])[-4:]
                nxt.append((j_acc + 1, tuple(new_tail), sc + add, new_pt))
        if not nxt:
            # fall back to rigid consume-1
            for j, tail, sc, pt in beams:
                if j < len(ks):
                    p = (c - ks[j]) % Q
                    nxt.append((j + 1, (p,), sc, pt + [p]))
        nxt.sort(key=lambda x: -x[2])
        beams = nxt[:beam]
    return beams[0][3] if beams else []


def idxs_of(split: int) -> list[int]:
    return GP.rune_indices((PAGE_DIR / f"split_{split:03d}.txt").read_text(encoding="utf-8"))


def prefix(n: int = 400) -> list[int]:
    out: list[int] = []
    for s in range(15, 71):
        out.extend(idxs_of(s))
        if len(out) >= n:
            break
    return out[:n]


def keep(sc: dict, n: int) -> bool:
    return (
        n >= 80
        and sc["trigram_per_100"] >= 3.5
        and 0.28 <= sc["vowelish_ratio"] <= 0.55
        and sc["ioc"] >= 0.045
    )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    # plant-and-recover
    plant_lat = "THEPRIMESARESACREDTHETOTIENTFVNCTIANISSACREDALLTHNGSSHOVLDBEENCRYPTEDAWARNNGBELIEVENOTHNG"
    plant_pt = GP.encode_latin_key(plant_lat)
    pks = sha256_ctr(b"CICADA3301", len(plant_pt) * 4)
    plant_ct, used = encrypt_reject(plant_pt, pks)
    skips = sum(1 for a, b in zip([0] + used, used) if b - a > 1)
    known = [(plant_ct[i] - pks[used[i]]) % Q for i in range(len(plant_ct))]
    known_ok = known == plant_pt
    rec = beam_decode(plant_ct, pks)
    rec_lat = GP.latin_stream(rec)
    agree = sum(a == b for a, b in zip(rec, plant_pt)) / len(plant_pt) if rec else 0.0
    plant = {
        "n": len(plant_pt),
        "ct_n": len(plant_ct),
        "extra_skips": skips,
        "known_js_ok": known_ok,
        "agree": round(agree, 4),
        "recovered_head": rec_lat[:80],
        "ok": known_ok and agree >= 0.95,
    }
    print("plant", plant)

    hits = []
    tested = 0
    sample = []
    targets = [("prefix400", prefix(400)), ("split015", idxs_of(15))]
    targets += [(f"split{s:03d}", idxs_of(s)) for s in (17, 23, 40, 56, 63, 68) if len(idxs_of(s)) >= 80]
    for tname, ct in targets:
        for seed in SEEDS:
            tested += 1
            ks = sha256_ctr(seed, len(ct) * 4)
            rigid = [(ct[i] - ks[i]) % Q for i in range(len(ct))]
            pt = beam_decode(ct, ks)
            for label, seq in (("beam", pt), ("rigid", rigid)):
                lat = GP.latin_stream(seq)
                sc = score_candidate(seq, lat)
                rec = {
                    "span": tname,
                    "seed": seed.decode("ascii", "replace"),
                    "mode": label,
                    "head": lat[:80],
                    **sc,
                }
                if seed == b"CICADA3301" and tname == "prefix400" and label == "beam":
                    print(f"beam {tname} CICADA3301 tri={sc['trigram_per_100']:.2f} ioc={sc['ioc']:.3f} {lat[:44]}")
                    sample.append(rec)
                if keep(sc, len(seq)) and label == "beam":
                    hits.append(rec)
                    print("KEEP", rec)
    print("tested", tested, "keeps", len(hits), "plant_ok", plant["ok"])
    (OUT / "result.json").write_text(
        json.dumps({"plant": plant, "tested": tested, "keeps": hits, "sample": sample}, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
