#!/usr/bin/env python3
"""Gromark-like running adders + Quagmire I/III mixed alphabets on attested keys."""
from __future__ import annotations

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
OUT = CICADA_ROOT / "experiments" / "EXP-LP-GROMARK-QUAGMIRE-001"

KEY_WORDS = [
    "DIVINITY",
    "FIRFUMFERENFE",
    "INSTAR",
    "CIRCUMFERENCE",
    "PILGRIM",
    "PRIMES",
    "CICADA",
    "LIBERPRIMUS",
    "ANEND",
    "PARABLE",
    "WELCOME",
    "AWARNING",
    "SOMEWISDOM",
    "KNOWTHIS",
    "THELOSSOFDIVINITY",
    "PRESERVATION",
    "KOAN",
    "TOTIENT",
    "PHI",
]


def idxs_of(split: int) -> list[int]:
    return GP.rune_indices((PAGE_DIR / f"split_{split:03d}.txt").read_text(encoding="utf-8"))


def prefix(n: int = 900) -> list[int]:
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


def running_adder(primer: list[int], n: int, modulus: int) -> list[int]:
    if len(primer) < 2:
        raise ValueError("primer")
    out = list(primer)
    i = 0
    while len(out) < n:
        out.append((out[i] + out[i + 1]) % modulus)
        i += 1
    return out[:n]


def gromark_dec(ct: list[int], primer: list[int], mixed: list[int] | None = None) -> list[int]:
    """Numeric running-adder keystream, optional mixed-alphabet invert after subtract."""
    ks = running_adder(primer, len(ct), Q)
    raw = [(x - k) % Q for x, k in zip(ct, ks)]
    if mixed is None:
        return raw
    inv = {v: i for i, v in enumerate(mixed)}
    return [inv.get(x, x) for x in raw]


def keyed_alpha(key: list[int]) -> list[int]:
    seen = set()
    out: list[int] = []
    for x in key:
        x %= Q
        if x not in seen:
            seen.add(x)
            out.append(x)
    for x in range(Q):
        if x not in seen:
            out.append(x)
    return out


def quagmire3(ct: list[int], mixer: list[int], indicator: list[int]) -> list[int]:
    alpha = keyed_alpha(mixer)
    pos = {v: i for i, v in enumerate(alpha)}
    out: list[int] = []
    for i, x in enumerate(ct):
        k = indicator[i % len(indicator)] % Q
        shift = pos[k]
        out.append(alpha[(pos[x % Q] - shift) % Q])
    return out


def quagmire1(ct: list[int], mixer: list[int], indicator: list[int]) -> list[int]:
    """Straight plain, mixed cipher (QI): recover column in mixed row, read identity."""
    alpha = keyed_alpha(mixer)
    pos = {v: i for i, v in enumerate(alpha)}
    out: list[int] = []
    for i, x in enumerate(ct):
        k = indicator[i % len(indicator)] % Q
        shift = pos[k]
        # cipher symbol x sits at identity-column (pos_id - shift) in mixed row
        # column j where alpha[(j + shift) % Q] == x → j = pos[x] - shift
        out.append((pos[x % Q] - shift) % Q)
    return out


def consider(hits: list, cipher: str, span: str, key: str, pt: list[int]) -> None:
    latin = GP.latin_stream(pt)
    sc = score_candidate(pt, latin)
    if keep(sc, len(pt)):
        hits.append({"cipher": cipher, "span": span, "key": key, "head": latin[:80], **sc})
        print(f"KEEP {cipher:10s} {span:10s} {key:20s} tri={sc['trigram_per_100']:.2f} {latin[:48]}")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    keys: list[tuple[str, list[int]]] = []
    for w in KEY_WORDS:
        try:
            enc = GP.encode_latin_key(w)
        except ValueError:
            continue
        if enc:
            keys.append((w, enc))

    primers = {
        "3301": [3, 3, 0, 1],
        "33010": [3, 3, 0, 1, 0],
        "08451": [0, 8, 4, 5, 1],
        "84514": [8, 4, 5, 1, 4],
        "2013": [2, 0, 1, 3],
        "2014": [2, 0, 1, 4],
        "2012": [2, 0, 1, 2],
        "56": [5, 6],
        "57": [5, 7],
        "12956": [1, 2, 9, 5, 6],
        "fib": [1, 1, 2, 3, 5],
        "primes": [2, 3, 5, 7, 11],
    }

    streams = [
        ("prefix900", prefix(900)),
        ("sec0-2", idxs_of(15) + idxs_of(16) + idxs_of(17)),
    ]
    pages = {s: idxs_of(s) for s in range(15, 71)}
    streams += [(f"split{s:03d}", ix) for s, ix in pages.items() if len(ix) >= 80]

    hits: list[dict] = []
    tested = 0

    for tname, ct in streams:
        for pn, primer in primers.items():
            tested += 1
            consider(hits, "gromark", tname, pn, gromark_dec(ct, primer))
            for kn, key in keys[:8]:
                tested += 1
                consider(hits, "gromark_mix", tname, f"{pn}+{kn}", gromark_dec(ct, primer, keyed_alpha(key)))

    # page-local gromark primers from onion index / split index
    for s, ix in pages.items():
        if len(ix) < 80:
            continue
        onion = s - 15
        for pn, primer in (
            (f"onion{onion}", [onion % Q, (onion * 3) % Q, 3, 3, 0, 1][:4]),
            (f"split{s}", [s % Q, (s // 10) % Q, 3, 3]),
        ):
            tested += 1
            consider(hits, "gromark_local", f"split{s:03d}", pn, gromark_dec(ix, primer))

    # Quagmire: mixers × indicators (same list; include seq)
    qkeys = keys + [("seq", list(range(Q)))]
    qtargets = [("prefix900", prefix(900)), ("sec0-2", idxs_of(15) + idxs_of(16) + idxs_of(17))]
    qtargets += [(f"split{s:03d}", ix) for s, ix in pages.items() if len(ix) >= 80]
    for tname, ct in qtargets:
        for mn, mixer in qkeys:
            for inn, ind in qkeys:
                if mn != inn and mn not in {"DIVINITY", "INSTAR", "CICADA", "ANEND", "seq"}:
                    continue  # bound: full cross only when mixer is a short attested word
                tested += 1
                consider(hits, "qiii", tname, f"{mn}/{inn}", quagmire3(ct, mixer, ind))
                tested += 1
                consider(hits, "qi", tname, f"{mn}/{inn}", quagmire1(ct, mixer, ind))
            if mn == "DIVINITY" and tname == "prefix900":
                pt = quagmire3(ct, mixer, mixer)
                lat = GP.latin_stream(pt)
                sc = score_candidate(pt, lat)
                print(f"qiii sample {tname} {mn} tri={sc['trigram_per_100']:.2f} ioc={sc['ioc']:.3f} {lat[:40]}")

    print("tested", tested, "keeps", len(hits))
    (OUT / "result.json").write_text(
        json.dumps({"tested": tested, "keeps": hits}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print("wrote", OUT / "result.json")


if __name__ == "__main__":
    main()
