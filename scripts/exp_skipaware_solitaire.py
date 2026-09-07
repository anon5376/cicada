#!/usr/bin/env python3
"""Skip-aware Solitaire/Pontifex keystream (unused). Plant-and-recover."""
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
from exp_skipaware_sha_ctr import beam_decode, encrypt_reject, keep  # noqa: E402

GP = Gematria()
Q = 29
JA, JB = 53, 54
OUT = CICADA_ROOT / "experiments" / "EXP-LP-SKIPAWARE-SOLITAIRE-001"
PASSES = (
    "CICADA3301",
    "DIVINITY",
    "FIRFUMFERENFE",
    "AN END",
    "LIBERPRIMUS",
    "THELOSSOFDIVINITY",
    "WELCOME",
    "INSTAR",
    "3301",
)


def _move(deck: list[int], card: int, n: int) -> None:
    i = deck.index(card)
    deck.pop(i)
    j = (i + n) % len(deck)
    deck.insert(j, card)


def _step(deck: list[int]) -> None:
    _move(deck, JA, 1)
    _move(deck, JB, 2)
    a, b = deck.index(JA), deck.index(JB)
    if a > b:
        a, b = b, a
    deck[:] = deck[b + 1 :] + deck[a : b + 1] + deck[:a]
    cut = 53 if deck[-1] >= 53 else deck[-1]
    deck[:] = deck[cut:-1] + deck[:cut] + [deck[-1]]


def _out(deck: list[int]) -> int | None:
    top = 53 if deck[0] >= 53 else deck[0]
    card = deck[top]
    if card >= 53:
        return None
    return card


def key_deck(phrase: str) -> list[int]:
    deck = list(range(1, 55))
    letters = [ord(c) - 64 for c in phrase.upper() if "A" <= c <= "Z"]
    if not letters:
        letters = [3, 3, 0, 1]
        letters = [x if x else 26 for x in letters]
    for v in letters:
        _step(deck)
        n = v
        deck[:] = deck[n:-1] + deck[:n] + [deck[-1]]
    return deck


def stream(phrase: str, n: int) -> list[int]:
    deck = key_deck(phrase)
    out: list[int] = []
    guard = 0
    while len(out) < n and guard < n * 40:
        guard += 1
        _step(deck)
        v = _out(deck)
        if v is None:
            continue
        out.append(v % Q)
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    plant_pt = GP.encode_latin_key(
        "THEPRIMESARESACREDTHETOTIENTFVNCTIANISSACREDALLTHNGSSHOVLDBEENCRYPTEDAWARNNGBELIEVENOTHNG"
    )
    ks = stream("CICADA3301", len(plant_pt) * 4)
    rec = beam_decode(encrypt_reject(plant_pt, ks)[0], ks)
    agree = sum(a == b for a, b in zip(rec, plant_pt)) / len(plant_pt) if rec else 0.0
    plant = {"agree": round(agree, 4), "ok": agree >= 0.95, "kslen": len(ks)}
    print("plant", plant, flush=True)

    targets = [("prefix400", prefix(400)), ("split015", idxs_of(15))]
    hits = []
    tested = 0
    samples = []
    for pw in PASSES:
        hay = stream(pw, 2000)
        for span, ct in targets:
            tested += 1
            pt = beam_decode(ct, hay[: len(ct) * 4])
            lat = GP.latin_stream(pt)
            sc = score_candidate(pt, lat)
            row = {"pass": pw, "span": span, "head": lat[:80], **sc}
            if tested <= 3:
                print(f"beam {pw} {span} tri={sc['trigram_per_100']:.2f} {lat[:28]}", flush=True)
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
