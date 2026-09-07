#!/usr/bin/env python3
"""NIST SP 800-90A Hash_DRBG (SHA-256) marked-seed keystreams.

HMAC-DRBG and HKDF-SHA256 are closed. This is the Hash_DRBG generate
path: V, C from seed; output Hash(V); V += Hash(0x03||V) + C + reseed_ctr.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from cicada.liber_primus.gematria import Gematria  # noqa: E402
from cicada.paths import ROOT as CICADA_ROOT  # noqa: E402
from cicada.scoring import score_candidate  # noqa: E402
from exp_skipaware_sha_ctr import beam_decode, encrypt_reject, idxs_of, keep, prefix  # noqa: E402

GP = Gematria()
Q = 29
MASK32 = 0xFFFFFFFF
OUT = CICADA_ROOT / "experiments" / "EXP-LP-HASH-DRBG-001"
N = 32  # SHA-256 seedlen bytes
MOD = 1 << (8 * N)


def _int(b: bytes) -> int:
    return int.from_bytes(b, "big")


def _bytes(x: int) -> bytes:
    return (x % MOD).to_bytes(N, "big")


def hash_df(seed: bytes, n: int = N) -> bytes:
    """SP 800-90A Hash_df with SHA-256, no extra extra_bits."""
    out = b""
    counter = 1
    while len(out) < n:
        out += hashlib.sha256(bytes([counter]) + (n * 8).to_bytes(4, "big") + seed).digest()
        counter += 1
    return out[:n]


def instantiate(seed: int) -> tuple[bytes, bytes]:
    mat = seed.to_bytes(8, "big")
    V = hash_df(mat, N)
    C = hash_df(b"\x00" + V, N)
    return V, C


def hash_drbg(seed: int, n: int, hi5: bool = False) -> list[int]:
    V, C = instantiate(seed)
    reseed = 1
    out: list[int] = []
    while len(out) < n:
        w = hashlib.sha256(V).digest()
        for b in w:
            out.append((b >> 3) % Q if hi5 else b % Q)
            if len(out) >= n:
                break
        H = hashlib.sha256(b"\x03" + V).digest()
        V = _bytes(_int(V) + _int(H) + _int(C) + reseed)
        reseed += 1
    return out


def marked_seeds():
    out = []
    for n in (
        1, 15, 56, 57, 3301, 2012, 2013, 2014, 2017, 1295, 1033,
        0x7A35090F, 0x57A35090, 0x6D854CD7, 0x181F01E5, 0x845145127 & MASK32,
    ):
        out.append((f"int:{n}", n & MASK32))
    for word in (b"CICADA3301", b"3301", b"DIVINITY", b"AN END", b"LIBERPRIMUS", b"TOTIENT"):
        h = hashlib.sha256(word).digest()
        out.append((f"sha32:{word.decode()}", int.from_bytes(h[:4], "big")))
    seen, uniq = set(), []
    for label, seed in out:
        if seed in seen or seed == 0:
            continue
        seen.add(seed)
        uniq.append((label, seed))
    return uniq


def apply_p(c, k, rel):
    if rel == "sub":
        return (c - k) % Q
    if rel == "add":
        return (c + k) % Q
    return (k - c) % Q


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    pt = GP.encode_latin_key(
        "THEPRIMESARESACREDTHETOTIENTFVNCTIANISSACREDALLTHNGSSHOVLDBEENCRYPTEDAWARNNGBELIEVENOTHNG"
    )
    gens = [
        ("hash_drbg", lambda s, n: hash_drbg(s, n, False)),
        ("hash_drbg_hi5", lambda s, n: hash_drbg(s, n, True)),
    ]
    plants = {}
    a = hash_drbg(3301, 32, False)
    plants["det"] = a == hash_drbg(3301, 32, False)
    plants["ne_hi"] = a != hash_drbg(3301, 32, True)
    for name, gen in gens:
        ks = gen(3301, len(pt) * 4)
        rec = [(p + ks[i]) % Q for i, p in enumerate(pt)]
        plants[f"{name}_rigid"] = [apply_p(c, ks[i], "sub") for i, c in enumerate(rec)] == pt
        ct, _ = encrypt_reject(pt, ks)
        recb = beam_decode(ct, ks)
        agree = sum(x == y for x, y in zip(recb, pt)) / len(pt) if recb else 0.0
        plants[f"{name}_beam"] = {"agree": round(agree, 4), "ok": agree >= 0.89}
        wrong = gen(2014, len(pt))
        plants[f"{name}_wrong"] = [apply_p((p + ks[i]) % Q, wrong[i], "sub") for i, p in enumerate(pt)] != pt
    plants["ok"] = all(
        (v is True) or (isinstance(v, dict) and v.get("ok"))
        for k, v in plants.items() if k != "ok"
    )
    print("plant", plants, flush=True)
    if not plants["ok"]:
        (OUT / "result.json").write_text(json.dumps({
            "experiment": "EXP-LP-HASH-DRBG-001", "plant": plants,
            "verified_new_unsolved_runes": 0, "aborted": "plant failed",
        }, indent=2) + "\n")
        return

    seeds = marked_seeds()
    pages = [(f"split{s:03d}", idxs_of(s)) for s in range(15, 71) if len(idxs_of(s)) >= 80]
    compact = [("prefix400", prefix(400))] + [
        (n, t) for n, t in pages if n in ("split015", "split017", "split040", "split063")
    ]
    hits, tested_r, tested_b, best = [], 0, 0, None

    for slabel, seed in seeds:
        for tname, ct in ([("prefix400", prefix(400))] + pages):
            ks = hash_drbg(seed, len(ct), False)
            for rel in ("sub", "add", "beau"):
                tested_r += 1
                rec = [apply_p(c, ks[i], rel) for i, c in enumerate(ct)]
                lat = GP.latin_stream(rec)
                sc = score_candidate(rec, lat)
                row = {"pass": "rigid", "gen": "hash_drbg", "seed": slabel, "span": tname,
                       "rel": rel, "head": lat[:80], **sc, "n": len(rec)}
                if best is None or sc["trigram_per_100"] > best["trigram_per_100"]:
                    best = row
                if keep(sc, len(rec)):
                    hits.append(row)
                    print("KEEP", slabel, tname, rel, sc["trigram_per_100"], lat[:40], flush=True)
        for tname, ct in compact:
            ks = hash_drbg(seed, len(ct), True)
            for rel in ("sub", "add", "beau"):
                tested_r += 1
                rec = [apply_p(c, ks[i], rel) for i, c in enumerate(ct)]
                lat = GP.latin_stream(rec)
                sc = score_candidate(rec, lat)
                row = {"pass": "rigid", "gen": "hash_drbg_hi5", "seed": slabel, "span": tname,
                       "rel": rel, "head": lat[:80], **sc, "n": len(rec)}
                if best is None or sc["trigram_per_100"] > best["trigram_per_100"]:
                    best = row
                if keep(sc, len(rec)):
                    hits.append(row)

    for slabel, seed in seeds:
        for tname, ct in (("prefix400", prefix(400)), ("split015", idxs_of(15))):
            tested_b += 1
            ks = hash_drbg(seed, len(ct) * 4, False)
            rec = beam_decode(ct, ks)
            lat = GP.latin_stream(rec)
            sc = score_candidate(rec, lat)
            row = {"pass": "beam", "gen": "hash_drbg", "seed": slabel, "span": tname,
                   "rel": "sub", "head": lat[:80], **sc, "n": len(rec)}
            if best is None or sc["trigram_per_100"] > best["trigram_per_100"]:
                best = row
            if keep(sc, len(rec)):
                hits.append(row)
                print("KEEP beam", slabel, tname, sc["trigram_per_100"], lat[:40], flush=True)

    result = {
        "experiment": "EXP-LP-HASH-DRBG-001",
        "family": "NIST Hash_DRBG SHA-256 (`%29` + hi5); rigid + skip-aware beam",
        "plant": plants,
        "n_seeds": len(seeds),
        "tested_rigid": tested_r,
        "tested_beam": tested_b,
        "tested": tested_r + tested_b,
        "keep_bar_hits": len(hits),
        "keeps": hits[:16],
        "best": {k: best[k] for k in ("pass", "gen", "seed", "span", "rel", "head", "trigram_per_100", "ioc")} if best else None,
        "skeptic_review": {"verdict": "null" if not hits else "keep-bar needs human English", "english": False},
        "verified_new_unsolved_runes": 0,
        "boundary": "HMAC-DRBG and HKDF already closed; not a 2^256 grind",
    }
    (OUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print("tested_r", tested_r, "tested_b", tested_b, "keeps", len(hits),
          "best", None if not best else (best["trigram_per_100"], best["gen"], best["head"][:40]))


if __name__ == "__main__":
    main()
