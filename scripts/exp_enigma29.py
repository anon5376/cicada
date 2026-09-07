#!/usr/bin/env python3
"""3-rotor Enigma on 29 runes (odd n ⇒ reflector has one fixed point). Unused family."""
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
OUT = CICADA_ROOT / "experiments" / "EXP-LP-ENIGMA-29-001"
WORDS = ("DIVINITY", "CICADA3301", "FIRFUMFERENFE", "ANEND", "LIBERPRIMUS", "WELCOME")


def keyed(text: str) -> list[int]:
    compact = "".join(ch for ch in text.upper() if ch.isascii() and ch.isalpha() and ch != "Q")
    seen: list[int] = []
    for i in GP.encode_latin_key(compact):
        if i not in seen:
            seen.append(i)
    return seen + [i for i in range(Q) if i not in seen]


def inv(p: list[int]) -> list[int]:
    out = [0] * Q
    for i, v in enumerate(p):
        out[v] = i
    return out


def atbash_ref() -> list[int]:
    return [(Q - 1 - i) for i in range(Q)]


def pass_forward(x: int, rot: list[int], pos: int) -> int:
    return rot[(x + pos) % Q]


def pass_back(x: int, rinv: list[int], pos: int) -> int:
    return (rinv[x] - pos) % Q


def crypt(data: list[int], rotors: list[list[int]], rinvs: list[list[int]], ref: list[int], start: list[int], notch: int) -> list[int]:
    pos = list(start)
    out = []
    for ch in data:
        pos[0] = (pos[0] + 1) % Q
        if pos[0] == notch:
            pos[1] = (pos[1] + 1) % Q
            if pos[1] == notch:
                pos[2] = (pos[2] + 1) % Q
        x = ch
        for r, p in zip(rotors, pos):
            x = pass_forward(x, r, p)
        x = ref[x]
        for rinv, p in zip(reversed(rinvs), reversed(pos)):
            x = pass_back(x, rinv, p)
        out.append(x)
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rotors = [keyed(w) for w in WORDS[:3]]
    rinvs = [inv(r) for r in rotors]
    ref = atbash_ref()
    plant_pt = GP.encode_latin_key(
        "THEPRIMESARESACREDTHETOTIENTFVNCTIANISSACREDALLTHNGSSHOVLDBEENCRYPTEDAWARNNGBELIEVENOTHNG"
    )
    ct = crypt(plant_pt, rotors, rinvs, ref, [0, 0, 0], 16)
    rec = crypt(ct, rotors, rinvs, ref, [0, 0, 0], 16)
    agree = sum(a == b for a, b in zip(rec, plant_pt)) / len(plant_pt)
    plant = {"agree": round(agree, 4), "ok": agree >= 0.99}
    print("plant", plant, flush=True)

    starts = ([0, 0, 0], [0, 15, 27], [1, 0, 0], [16, 16, 16], [3, 3, 0, 1][:3])
    notches = (0, 16, 28)
    triples = [
        WORDS[:3],
        ("ANEND", "WELCOME", "LIBERPRIMUS"),
        ("DIVINITY", "WELCOME", "ANEND"),
        ("FIRFUMFERENFE", "DIVINITY", "CICADA3301"),
    ]
    targets = [("prefix400", prefix(400)), ("split015", idxs_of(15))]
    hits = []
    tested = 0
    samples = []
    for names in triples:
        rots = [keyed(w) for w in names]
        invs = [inv(r) for r in rots]
        for st in starts:
            for notch in notches:
                for span, data in targets:
                    tested += 1
                    pt = crypt(data, rots, invs, ref, list(st), notch)
                    lat = GP.latin_stream(pt)
                    sc = score_candidate(pt, lat)
                    row = {"rotors": names, "start": st, "notch": notch, "span": span, "head": lat[:80], **sc}
                    if tested <= 3:
                        print(f"dec {names[0]} {st} n{notch} {span} tri={sc['trigram_per_100']:.2f} {lat[:24]}", flush=True)
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
