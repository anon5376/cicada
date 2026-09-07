#!/usr/bin/env python3
"""Chaocipher on the 29-rune alphabet (unused family). Plant-and-recover."""
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
from exp_skipaware_marsaglia import idxs_of, prefix  # noqa: E402
from exp_skipaware_sha_ctr import keep  # noqa: E402

GP = Gematria()
Q = 29
NADIR = 13  # 0-index of 14th cell (classic nadir)
OUT = CICADA_ROOT / "experiments" / "EXP-LP-CHAOCIPHER-29-001"
ORDER = list(range(Q))
KEYS = (
    "DIVINITY",
    "CICADA3301",
    "FIRFUMFERENFE",
    "ANEND",
    "LIBERPRIMUS",
    "THELOSSOFDIVINITY",
    "WELCOME",
    "INSTAR",
)


def keyed(text: str) -> list[int]:
    compact = "".join(ch for ch in text.upper() if ch.isascii() and ch.isalpha() and ch != "Q")
    seen: list[int] = []
    for i in GP.encode_latin_key(compact):
        if i not in seen:
            seen.append(i)
    return seen + [i for i in ORDER if i not in seen]


def _extract_insert(alpha: list[int], take: int, put: int) -> list[int]:
    ch = alpha[take]
    tmp = alpha[:take] + alpha[take + 1 :]
    dest = put if put < take else put - 1
    dest = max(0, min(dest, len(tmp)))
    return tmp[:dest] + [ch] + tmp[dest:]


def rot(alpha: list[int], ch: int) -> list[int]:
    i = alpha.index(ch)
    return alpha[i:] + alpha[:i]


def perm_left(left: list[int], c: int) -> list[int]:
    left = rot(left, c)
    return _extract_insert(left, 1, NADIR)


def perm_right(right: list[int], p: int) -> list[int]:
    right = rot(right, p)
    right = right[1:] + right[:1]
    return _extract_insert(right, 2, NADIR)


def encrypt(pt: list[int], left0: list[int], right0: list[int]) -> list[int]:
    left, right = list(left0), list(right0)
    ct = []
    for p in pt:
        i = right.index(p)
        c = left[i]
        ct.append(c)
        left = perm_left(left, c)
        right = perm_right(right, p)
    return ct


def decrypt(ct: list[int], left0: list[int], right0: list[int]) -> list[int]:
    left, right = list(left0), list(right0)
    pt = []
    for c in ct:
        i = left.index(c)
        p = right[i]
        pt.append(p)
        left = perm_left(left, c)
        right = perm_right(right, p)
    return pt


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    plant_pt = GP.encode_latin_key(
        "THEPRIMESARESACREDTHETOTIENTFVNCTIANISSACREDALLTHNGSSHOVLDBEENCRYPTEDAWARNNGBELIEVENOTHNG"
    )
    L, R = keyed("DIVINITY"), keyed("CICADA3301")
    rec = decrypt(encrypt(plant_pt, L, R), L, R)
    agree = sum(a == b for a, b in zip(rec, plant_pt)) / len(plant_pt)
    plant = {"agree": round(agree, 4), "ok": agree >= 0.99}
    print("plant", plant, flush=True)

    pairs = [("id", ORDER, ORDER), ("rev", ORDER, list(reversed(ORDER)))]
    for k in KEYS:
        pairs.append((f"keyL:{k}", keyed(k), ORDER))
        pairs.append((f"keyR:{k}", ORDER, keyed(k)))
        pairs.append((f"keyLR:{k}", keyed(k), keyed(k[::-1])))

    targets = [("prefix400", prefix(400)), ("split015", idxs_of(15))]
    hits = []
    tested = 0
    samples = []
    for name, left, right in pairs:
        for span, ct in targets:
            tested += 1
            pt = decrypt(ct, left, right)
            lat = GP.latin_stream(pt)
            sc = score_candidate(pt, lat)
            row = {"pair": name, "span": span, "head": lat[:80], **sc}
            if tested <= 4:
                print(f"dec {name} {span} tri={sc['trigram_per_100']:.2f} ioc={sc['ioc']:.4f} {lat[:28]}", flush=True)
                samples.append(row)
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
