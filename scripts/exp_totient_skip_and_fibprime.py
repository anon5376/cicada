#!/usr/bin/env python3
"""Page-56 skip rule on unsolved pages + Fibonacci–prime mesh keystreams."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cicada.liber_primus.ciphers import (  # noqa: E402
    totient_prime_stream,
    totient_skip_ciphertext_f_ordinal,
    vigenere_decrypt,
)
from cicada.liber_primus.gematria import Gematria, first_n_primes  # noqa: E402
from cicada.paths import ROOT as CICADA_ROOT  # noqa: E402
from cicada.scoring import score_candidate  # noqa: E402

GP = Gematria()
PAGE_DIR = CICADA_ROOT / "corpus/normalized/rtkd_pages"
OUT = CICADA_ROOT / "experiments" / "EXP-LP-TOTIENT-SKIP-FIB-001"


def idxs_of(s: int) -> list[int]:
    return GP.rune_indices((PAGE_DIR / f"split_{s:03d}.txt").read_text(encoding="utf-8"))


def keep(sc: dict, n: int) -> bool:
    if n < 30:
        return False
    return sc["trigram_per_100"] >= 4.0 and 0.28 <= sc["vowelish_ratio"] <= 0.55 and sc["ioc"] >= 0.045


def fib_upto_count(n: int) -> list[int]:
    out = [0, 1]
    while len(out) < n:
        out.append(out[-1] + out[-2])
    return out[:n]


def mesh_streams(n: int) -> dict[str, list[int]]:
    primes = first_n_primes(max(n + 50, 800))
    # 3301 is the 464th prime (1-based)
    assert primes[463] == 3301, primes[463]
    fib = fib_upto_count(n + 5)
    streams = {}
    # p-1 totient already tested; mesh variants:
    streams["p_minus_fib"] = [(primes[i] - fib[i]) % 29 for i in range(n)]
    streams["fib_mod29"] = [fib[i] % 29 for i in range(n)]
    streams["abs_3301_p"] = [abs(3301 - primes[i]) % 29 for i in range(n)]
    # 2016-style: start at 464, subtract successive fib, use as 1-based prime index
    idx = 464
    seq = []
    for i in range(n):
        idx = 464 - sum(fib[1 : i + 2])  # cumulative fib from 1
        if idx < 1:
            idx = ((idx - 1) % 500) + 1
        seq.append((primes[idx - 1] - 1) % 29)
    streams["from464_cumfib_prime"] = seq
    # C-square extended: generate more |3301-prime(fib)| 
    A = [0, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 987]
    while len(A) < n:
        A.append(A[-1] + A[-2])
    ext = []
    for a in A[:n]:
        # (a+1)th prime, 1-based; a=0 -> 1st prime
        pi = a if a < len(primes) else (a % (len(primes) - 1))
        ext.append(abs(3301 - primes[pi]) % 29)
    streams["C_extended"] = ext
    return streams


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    hits = []
    tested = 0
    # totient + skip Nth F on each unsolved page and on the concat stream
    pages = {s: idxs_of(s) for s in range(15, 71)}
    concat = []
    for s in range(15, 71):
        concat.extend(pages[s])

    for s, ix in pages.items():
        if len(ix) < 30:
            continue
        for ord_ in range(1, 7):
            tested += 1
            out = totient_skip_ciphertext_f_ordinal(ix, ord_)
            latin = GP.latin_stream(out)
            sc = score_candidate(out, latin)
            if keep(sc, len(ix)) or latin.startswith(("ANEND", "WELCOME", "AWARNING", "PARABLE", "ITISTHE")):
                hits.append({"where": f"split{s:03d}", "kind": f"skip_F#{ord_}", "head": latin[:90], **sc})
        tested += 1
        out = totient_prime_stream(ix)
        latin = GP.latin_stream(out)
        sc = score_candidate(out, latin)
        if keep(sc, len(ix)):
            hits.append({"where": f"split{s:03d}", "kind": "totient", "head": latin[:90], **sc})

    for ord_ in (4,):
        tested += 1
        out = totient_skip_ciphertext_f_ordinal(concat, ord_)
        latin = GP.latin_stream(out[:400])
        sc = score_candidate(out[:400], latin)
        print("concat skip4", sc["trigram_per_100"], sc["ioc"], latin[:80])
        if keep(sc, 400) or sc["trigram_per_100"] >= 3.5:
            hits.append({"where": "concat400", "kind": "skip_F#4", "head": latin[:90], **sc})

    streams = mesh_streams(len(concat))
    (OUT / "stream_heads.json").write_text(
        json.dumps({k: v[:24] for k, v in streams.items()}, indent=2) + "\n",
        encoding="utf-8",
    )
    for name, ks in streams.items():
        for label, sl in (("concat900", concat[:900]),):
            tested += 1
            out = [(sl[i] - ks[i]) % 29 for i in range(len(sl))]
            latin = GP.latin_stream(out)
            sc = score_candidate(out, latin)
            print(f"mesh {name:24s} tri={sc['trigram_per_100']:5.2f} ioc={sc['ioc']:.3f} {latin[:60]}")
            if keep(sc, len(sl)) or sc["trigram_per_100"] >= 3.2:
                hits.append({"where": sl and label, "kind": name, "rel": "sub", "head": latin[:90], **sc})
        # also first three unsolved pages
        for s in (15, 16, 17, 30, 68):
            ix = pages[s]
            if len(ix) < 30:
                continue
            tested += 1
            out = vigenere_decrypt(ix, ks[: max(len(ix), 16)])
            # wait: vigenere repeats; for aperiodic use prefix
            out = [(ix[i] - ks[i]) % 29 for i in range(len(ix))]
            latin = GP.latin_stream(out)
            sc = score_candidate(out, latin)
            if keep(sc, len(ix)):
                hits.append({"where": f"split{s:03d}", "kind": name, "head": latin[:90], **sc})

    summary = {"tested": tested, "hits": hits, "n_hits": len(hits)}
    (OUT / "result.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print("tested", tested, "hits", len(hits))
    for h in hits[:15]:
        print(" HIT", h.get("where"), h.get("kind"), h.get("trigram_per_100"), h.get("head", "")[:70])


if __name__ == "__main__":
    main()
