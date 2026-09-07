#!/usr/bin/env python3
"""Skip-aware beam on unused arithmetic streams (μ, ω, Ω, λ, σ). φ already tested."""
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
OUT = CICADA_ROOT / "experiments" / "EXP-LP-SKIPAWARE-ARITH-001"
NMAX = 12000


def factor_sieve(n: int) -> list[list[int]]:
    fac: list[list[int]] = [[] for _ in range(n)]
    for p in range(2, n):
        if fac[p]:
            continue
        for m in range(p, n, p):
            fac[m].append(p)
    return fac


def streams(fac: list[list[int]]) -> dict[str, list[int]]:
    n = len(fac)
    mu = [0] * n
    omega = [0] * n
    Omega = [0] * n
    lam = [0] * n
    sigma = [0] * n
    sopfr = [0] * n
    for i in range(1, n):
        ps = fac[i]
        omega[i] = len(ps)
        # Ω and μ need full multiplicity
        x, omg, sq = i, 0, False
        for p in ps:
            c = 0
            while x % p == 0:
                x //= p
                c += 1
            omg += c
            if c > 1:
                sq = True
        Omega[i] = omg
        mu[i] = 0 if sq else (1 if omg % 2 == 0 else -1)
        if i == 1:
            mu[i] = 1
            Omega[i] = 0
            omega[i] = 0
        lam[i] = 1 if Omega[i] % 2 == 0 else -1
        # σ(n) via primes
        x, s = i, 1
        for p in ps:
            pk, acc = p, 1
            while x % p == 0:
                x //= p
                acc += pk
                pk *= p
            s *= acc
        sigma[i] = s
    for i in range(1, n):
        x, sm = i, 0
        for p in fac[i]:
            while x % p == 0:
                x //= p
                sm += p
        sopfr[i] = sm
    return {
        "mu_plus1": [(mu[i] + 1) % Q for i in range(1, n)],
        "mu_abs": [abs(mu[i]) % Q for i in range(1, n)],
        "omega": [omega[i] % Q for i in range(1, n)],
        "Omega": [Omega[i] % Q for i in range(1, n)],
        "lambda_plus1": [(lam[i] + 1) % Q for i in range(1, n)],
        "sigma": [sigma[i] % Q for i in range(1, n)],
        "sopfr": [sopfr[i] % Q for i in range(1, n)],
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fac = factor_sieve(NMAX)
    stm = streams(fac)
    plant_pt = GP.encode_latin_key(
        "THEPRIMESARESACREDTHETOTIENTFVNCTIANISSACREDALLTHNGSSHOVLDBEENCRYPTEDAWARNNGBELIEVENOTHNG"
    )
    ks = stm["sigma"][: len(plant_pt) * 4]
    rec = beam_decode(encrypt_reject(plant_pt, ks)[0], ks)
    agree = sum(a == b for a, b in zip(rec, plant_pt)) / len(plant_pt)
    plant = {"agree": round(agree, 4), "ok": agree >= 0.9}
    print("plant", plant, flush=True)

    targets = [("prefix400", prefix(400)), ("split015", idxs_of(15))]
    starts = (0, 1, 3301)
    hits = []
    tested = 0
    samples = []
    for name, seq in stm.items():
        for off in starts:
            hay = seq[off:] + seq[:off]
            if len(hay) < 2000:
                continue
            for span, ct in targets:
                tested += 1
                pt = beam_decode(ct, hay[: len(ct) * 4])
                lat = GP.latin_stream(pt)
                sc = score_candidate(pt, lat)
                row = {"stream": name, "offset": off, "span": span, "head": lat[:80], **sc}
                if tested <= 3:
                    print(f"beam {name}@{off} {span} tri={sc['trigram_per_100']:.2f} {lat[:28]}", flush=True)
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
