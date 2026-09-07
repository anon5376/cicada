#!/usr/bin/env python3
"""Totient stream meshed with attested Vigenere/Beaufort/Porta keys."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from cicada.liber_primus.ciphers import totient_prime_stream, vigenere_decrypt  # noqa: E402
from cicada.liber_primus.gematria import Gematria  # noqa: E402
from cicada.paths import ROOT as CICADA_ROOT  # noqa: E402
from cicada.scoring import score_candidate  # noqa: E402
from exp_autokey_porta_skel import beaufort, porta29  # noqa: E402

GP = Gematria()
Q = 29
PAGE_DIR = CICADA_ROOT / "corpus/normalized/rtkd_pages"
OUT = CICADA_ROOT / "experiments" / "EXP-LP-TOTIENT-VIG-MESH-001"

KEYS = [
    "DIVINITY",
    "FIRFUMFERENFE",
    "INSTAR",
    "CIRCUMFERENCE",
    "PILGRIM",
    "PRIMES",
    "CICADA",
    "ANEND",
    "PARABLE",
    "WELCOME",
    "KOAN",
    "TOTIENT",
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


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    keys = []
    for w in KEYS:
        try:
            enc = GP.encode_latin_key(w)
        except ValueError:
            continue
        if enc:
            keys.append((w, enc))

    streams = [("prefix900", prefix(900)), ("sec0-2", idxs_of(15) + idxs_of(16) + idxs_of(17))]
    streams += [(f"split{s:03d}", idxs_of(s)) for s in range(15, 71) if len(idxs_of(s)) >= 80]

    hits = []
    tested = 0
    for tname, ct in streams:
        tot = totient_prime_stream(ct)
        for start in (0, 1):
            if start:
                tot = totient_prime_stream(ct)  # same; vary by rotating tot
                tot = tot[1:] + tot[:1]
            for kn, key in keys:
                for name, fn in (
                    ("vig_after_tot", lambda s, k: vigenere_decrypt(s, k)),
                    ("beau_after_tot", beaufort),
                    ("porta_after_tot", porta29),
                    ("tot_after_vig", None),
                ):
                    tested += 1
                    if name == "tot_after_vig":
                        pt = totient_prime_stream(vigenere_decrypt(ct, key))
                    else:
                        pt = fn(tot, key)
                    latin = GP.latin_stream(pt)
                    sc = score_candidate(pt, latin)
                    if kn == "DIVINITY" and name == "vig_after_tot" and tname == "prefix900" and start == 0:
                        print(f"mesh {name} {tname} {kn} tri={sc['trigram_per_100']:.2f} ioc={sc['ioc']:.3f} {latin[:40]}")
                    if keep(sc, len(pt)):
                        rec = {"cipher": name, "span": tname, "key": kn, "start": start, "head": latin[:80], **sc}
                        hits.append(rec)
                        print("KEEP", rec)
    print("tested", tested, "keeps", len(hits))
    (OUT / "result.json").write_text(
        json.dumps({"tested": tested, "keeps": hits}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
