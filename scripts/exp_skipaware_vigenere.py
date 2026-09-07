#!/usr/bin/env python3
"""Skip-aware repeating Vigenere: attested keys + reject filter."""
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
from exp_skipaware_sha_ctr import beam_decode, encrypt_reject, keep  # noqa: E402

GP = Gematria()
Q = 29
PAGE_DIR = CICADA_ROOT / "corpus/normalized/rtkd_pages"
OUT = CICADA_ROOT / "experiments" / "EXP-LP-SKIPAWARE-VIGENERE-001"
WORDS = [
    "DIVINITY",
    "FIRFUMFERENFE",
    "INSTAR",
    "CIRCUMFERENCE",
    "PILGRIM",
    "PRIMES",
    "CICADA",
    "ANEND",
    "WELCOME",
    "KOAN",
    "PARABLE",
    "PRESERVATION",
    "CONSUMPTION",
    "ADHERENCE",
    "THELOSSOFDIVINITY",
    "AWARNING",
    "SOMEWISDOM",
    "KNOWTHIS",
]


def idxs_of(s: int) -> list[int]:
    return GP.rune_indices((PAGE_DIR / f"split_{s:03d}.txt").read_text(encoding="utf-8"))


def prefix(n: int = 400) -> list[int]:
    out: list[int] = []
    for s in range(15, 71):
        out.extend(idxs_of(s))
        if len(out) >= n:
            break
    return out[:n]


def tile(key: list[int], n: int) -> list[int]:
    return [key[i % len(key)] for i in range(n)]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    keys = []
    for w in WORDS:
        try:
            enc = GP.encode_latin_key(w)
        except ValueError:
            continue
        if enc:
            keys.append((w, enc))
    plant_pt = GP.encode_latin_key(
        "THEPRIMESARESACREDTHETOTIENTFVNCTIANISSACREDALLTHNGSSHOVLDBEENCRYPTEDAWARNNGBELIEVENOTHNG"
    )
    pks = tile(keys[0][1], len(plant_pt) * 4)
    ct, used = encrypt_reject(plant_pt, pks)
    rec = beam_decode(ct, pks)
    agree = sum(a == b for a, b in zip(rec, plant_pt)) / len(plant_pt)
    plant = {"key": keys[0][0], "agree": round(agree, 4), "ok": agree >= 0.9, "head": GP.latin_stream(rec)[:64]}
    print("plant", plant)

    targets = [("prefix400", prefix(400)), ("split015", idxs_of(15))]
    targets += [(f"split{s:03d}", idxs_of(s)) for s in range(15, 71) if len(idxs_of(s)) >= 80]
    hits = []
    tested = 0
    for tname, ct in targets:
        for kn, key in keys:
            tested += 1
            ks = tile(key, len(ct) * 4)
            pt = beam_decode(ct, ks)
            lat = GP.latin_stream(pt)
            sc = score_candidate(pt, lat)
            if kn == "DIVINITY" and tname == "prefix400":
                print(f"beam {tname} {kn} tri={sc['trigram_per_100']:.2f} ioc={sc['ioc']:.3f} {lat[:40]}")
            if keep(sc, len(pt)):
                hits.append({"span": tname, "key": kn, "head": lat[:80], **sc})
                print("KEEP", kn, tname, lat[:48])
    print("tested", tested, "keeps", len(hits))
    (OUT / "result.json").write_text(
        json.dumps({"plant": plant, "tested": tested, "keeps": hits}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
