#!/usr/bin/env python3
"""Totient (and prime) streams through the validated skip-aware beam.

Hypothesis: unsolved pages use the page-56 generator plus the anti-repeat
filter. Rigid totient would desync and look like chance.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from cicada.liber_primus.gematria import Gematria, first_n_primes  # noqa: E402
from cicada.paths import ROOT as CICADA_ROOT  # noqa: E402
from cicada.scoring import score_candidate  # noqa: E402
from exp_skipaware_sha_ctr import beam_decode, encrypt_reject, keep  # noqa: E402

GP = Gematria()
Q = 29
PAGE_DIR = CICADA_ROOT / "corpus/normalized/rtkd_pages"
OUT = CICADA_ROOT / "experiments" / "EXP-LP-SKIPAWARE-TOTIENT-001"


def idxs_of(split: int) -> list[int]:
    return GP.rune_indices((PAGE_DIR / f"split_{split:03d}.txt").read_text(encoding="utf-8"))


def prefix(n: int = 400) -> list[int]:
    out: list[int] = []
    for s in range(15, 71):
        out.extend(idxs_of(s))
        if len(out) >= n:
            break
    return out[:n]


def totient_ks(n: int, start: int = 0) -> list[int]:
    pr = first_n_primes(n + start + 8)
    return [(pr[i + start] - 1) % Q for i in range(n)]


def prime_ks(n: int, start: int = 0) -> list[int]:
    pr = first_n_primes(n + start + 8)
    return [pr[i + start] % Q for i in range(n)]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    plant_lat = (
        "THEPRIMESARESACREDTHETOTIENTFVNCTIANISSACREDALLTHNGSSHOVLDBEENCRYPTED"
        "AWARNNGBELIEVENOTHNGFROMTHISBOOC"
    )
    plant_pt = GP.encode_latin_key(plant_lat)
    pks = totient_ks(len(plant_pt) * 4)
    plant_ct, used = encrypt_reject(plant_pt, pks)
    known = [(plant_ct[i] - pks[used[i]]) % Q for i in range(len(plant_ct))]
    rec = beam_decode(plant_ct, pks)
    agree = sum(a == b for a, b in zip(rec, plant_pt)) / len(plant_pt) if rec else 0.0
    plant = {
        "known_ok": known == plant_pt,
        "agree": round(agree, 4),
        "skips": sum(1 for a, b in zip([0] + used, used) if b - a > 1),
        "ok": known == plant_pt and agree >= 0.95,
        "head": GP.latin_stream(rec)[:72],
    }
    print("plant", plant)

    streams = {
        "tot0": lambda n: totient_ks(n, 0),
        "tot1": lambda n: totient_ks(n, 1),
        "tot2": lambda n: totient_ks(n, 2),
        "prime0": lambda n: prime_ks(n, 0),
        "fib": lambda n: _fib_ks(n),
    }
    targets = [("prefix400", prefix(400)), ("unsolved_h800", prefix(800)), ("split015", idxs_of(15))]
    for s in range(15, 71):
        ix = idxs_of(s)
        if len(ix) >= 80:
            targets.append((f"split{s:03d}", ix))

    hits = []
    tested = 0
    for tname, ct in targets:
        for sn, fn in streams.items():
            tested += 1
            ks = fn(len(ct) * 4)
            pt = beam_decode(ct, ks)
            lat = GP.latin_stream(pt)
            sc = score_candidate(pt, lat)
            if tname in {"prefix400", "split015"} and sn == "tot0":
                print(f"beam {tname:12s} {sn:7s} tri={sc['trigram_per_100']:.2f} ioc={sc['ioc']:.3f} {lat[:44]}")
            if keep(sc, len(pt)):
                rec = {"span": tname, "stream": sn, "head": lat[:80], **sc}
                hits.append(rec)
                print("KEEP", rec)
            # local totient start = onion index
            if sn == "tot0" and tname.startswith("split"):
                onion = int(tname[5:]) - 15
                tested += 1
                pt = beam_decode(ct, totient_ks(len(ct) * 4, onion))
                lat = GP.latin_stream(pt)
                sc = score_candidate(pt, lat)
                if keep(sc, len(pt)):
                    hits.append({"span": tname, "stream": f"tot_onion{onion}", "head": lat[:80], **sc})
                    print("KEEP onion", tname, lat[:48])

    print("tested", tested, "keeps", len(hits), "plant_ok", plant["ok"])
    (OUT / "result.json").write_text(
        json.dumps({"plant": plant, "tested": tested, "keeps": hits}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _fib_ks(n: int) -> list[int]:
    a, b = 1, 1
    out = []
    for _ in range(n):
        out.append(a % Q)
        a, b = b, a + b
    return out


if __name__ == "__main__":
    main()
