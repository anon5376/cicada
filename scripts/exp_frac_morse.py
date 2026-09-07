#!/usr/bin/env python3
"""Fractionated Morse (Morse + X, group-of-3 keyed 27-table).

Trifid-27 already closed (fixed 3-trit per rune). This is the variable-length
Morse expansion of each rune's Latin, X-separated, then period-3 lookup.
"""
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
from exp_skipaware_sha_ctr import idxs_of, keep, prefix  # noqa: E402

GP = Gematria()
Q = 29
OUT = CICADA_ROOT / "experiments" / "EXP-LP-FRAC-MORSE-001"
WORDS = ("DIVINITY", "CICADA3301", "FIRFUMFERENFE", "ANEND", "LIBERPRIMUS", "TOTIENT")

MORSE = {
    "A": ".-", "B": "-...", "C": "-.-.", "D": "-..", "E": ".", "F": "..-.",
    "G": "--.", "H": "....", "I": "..", "J": ".---", "K": "-.-", "L": ".-..",
    "M": "--", "N": "-.", "O": "---", "P": ".--.", "Q": "--.-", "R": ".-.",
    "S": "...", "T": "-", "U": "..-", "V": "...-", "W": ".--", "X": "-..-",
    "Y": "-.--", "Z": "--..",
}
INV_MORSE = {v: k for k, v in MORSE.items()}
SYMS = ".-x"
TRIPLES = [a + b + c for a in SYMS for b in SYMS for c in SYMS]  # 27


def key_idxs(word: str) -> list[int]:
    return GP.encode_latin_key(word)


def mixed27(key: list[int]) -> list[int]:
    seen: set[int] = set()
    out: list[int] = []
    for x in key:
        x %= 27
        if x not in seen:
            seen.add(x)
            out.append(x)
    for x in range(27):
        if x not in seen:
            out.append(x)
    return out


def tables(key: list[int]) -> tuple[dict[str, int], dict[int, str]]:
    order = mixed27(key)
    enc = {TRIPLES[i]: order[i] for i in range(27)}
    dec = {order[i]: TRIPLES[i] for i in range(27)}
    return enc, dec


def to_morse(indices: list[int]) -> str:
    parts: list[str] = []
    for i in indices:
        for ch in GP.latin_of_index(i).upper():
            if ch in MORSE:
                parts.append(MORSE[ch])
                parts.append("x")
    return "".join(parts)


def from_morse(stream: str) -> str:
    letters: list[str] = []
    for chunk in stream.split("x"):
        if not chunk:
            continue
        if chunk in INV_MORSE:
            letters.append(INV_MORSE[chunk])
    return "".join(letters)


def fm_enc(pt: list[int], key: list[int]) -> list[int]:
    enc, _ = tables(key)
    s = to_morse(pt)
    while len(s) % 3:
        s += "x"
    return [enc[s[i:i + 3]] for i in range(0, len(s), 3)]


def fm_dec_latin(ct: list[int], key: list[int]) -> str:
    _, dec = tables(key)
    parts: list[str] = []
    for c in ct:
        if 0 <= c < 27:
            parts.append(dec[c])
        # runes 27–28 dropped (not in the 27-table)
    return from_morse("".join(parts))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    pt = GP.encode_latin_key(
        "THEPRIMESARESACREDTHETOTIENTFVNCTIANISSACREDALLTHNGSSHOVLDBEENCRYPTEDAWARNNGBELIEVENOTHNG"
    )
    k0 = key_idxs("DIVINITY")
    want = from_morse(to_morse(pt))
    got = fm_dec_latin(fm_enc(pt, k0), k0)
    plants = {
        "roundtrip": got == want,
        "wrong": fm_dec_latin(fm_enc(pt, k0), key_idxs("TOTIENT")) != want,
        "want_head": want[:40],
        "got_head": got[:40],
    }
    plants["ok"] = bool(plants["roundtrip"] and plants["wrong"])
    print("plant", plants, flush=True)
    if not plants["ok"]:
        (OUT / "result.json").write_text(json.dumps({
            "experiment": "EXP-LP-FRAC-MORSE-001", "plant": plants,
            "verified_new_unsolved_runes": 0, "aborted": "plant failed",
        }, indent=2) + "\n")
        return

    targets = [("prefix400", prefix(400))]
    for s in range(15, 71):
        ct = idxs_of(s)
        if len(ct) >= 80:
            targets.append((f"split{s:03d}", ct))

    hits, tested, best = [], 0, None
    for word in WORDS:
        key = key_idxs(word)
        for tname, ct in targets:
            tested += 1
            lat = fm_dec_latin(ct, key)
            if len(lat) < 40:
                continue
            safe = lat.replace("Q", "C").replace("Z", "S")
            rec = GP.encode_latin_key(safe)
            if len(rec) < 40:
                continue
            scored = GP.latin_stream(rec)
            sc = score_candidate(rec, scored)
            row = {"key": word, "span": tname, "head": lat[:80], **sc, "n": len(rec)}
            if best is None or sc["trigram_per_100"] > best["trigram_per_100"]:
                best = row
            if keep(sc, len(rec)):
                hits.append(row)
                print("KEEP", word, tname, sc["trigram_per_100"], lat[:40], flush=True)

    result = {
        "experiment": "EXP-LP-FRAC-MORSE-001",
        "family": "fractionated Morse (variable Latin Morse + X, keyed 27-table)",
        "plant": plants,
        "tested": tested,
        "keep_bar_hits": len(hits),
        "keeps": hits[:12],
        "best": {k: best[k] for k in ("key", "span", "head", "trigram_per_100", "ioc")} if best else None,
        "skeptic_review": {
            "verdict": "null" if not hits else "keep-bar needs human English",
            "english": False,
        },
        "verified_new_unsolved_runes": 0,
        "note": "Distinct from Trifid-27 (fixed 3-trit). Runes 27–28 dropped on decrypt.",
    }
    (OUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print("tested", tested, "keeps", len(hits),
          "best", None if not best else (best["trigram_per_100"], best["head"][:40]))


if __name__ == "__main__":
    main()
