#!/usr/bin/env python3
"""NIST SP 800-90A CTR_DRBG (AES-128 / AES-256) marked-seed keystreams.

HMAC-DRBG and Hash_DRBG are closed. This is the AES block-cipher DRBG:
Key||V from Update(seed); generate increments V and encrypts; Update after.
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

from Crypto.Cipher import AES  # noqa: E402

GP = Gematria()
Q = 29
MASK32 = 0xFFFFFFFF
OUT = CICADA_ROOT / "experiments" / "EXP-LP-CTR-DRBG-001"


def _inc(v: bytes) -> bytes:
    x = (int.from_bytes(v, "big") + 1) % (1 << (8 * len(v)))
    return x.to_bytes(len(v), "big")


def _xor(a: bytes, b: bytes) -> bytes:
    return bytes(x ^ y for x, y in zip(a, b))


def _aes(key: bytes, block: bytes) -> bytes:
    return AES.new(key, AES.MODE_ECB).encrypt(block)


def update(key: bytes, v: bytes, provided: bytes) -> tuple[bytes, bytes]:
    seedlen = len(key) + len(v)
    temp = b""
    while len(temp) < seedlen:
        v = _inc(v)
        temp += _aes(key, v)
    temp = temp[:seedlen]
    if provided:
        provided = provided.ljust(seedlen, b"\x00")[:seedlen]
        temp = _xor(temp, provided)
    return temp[: len(key)], temp[len(key) :]


def instantiate(seed: int, keylen: int) -> tuple[bytes, bytes]:
    key = b"\x00" * keylen
    v = b"\x00" * 16
    mat = hashlib.sha256(seed.to_bytes(8, "big")).digest()
    if keylen == 32:
        mat = mat + hashlib.sha256(mat).digest()[:16]
    return update(key, v, mat)


def ctr_drbg(seed: int, n: int, *, keylen: int = 16, hi5: bool = False) -> list[int]:
    key, v = instantiate(seed, keylen)
    raw = b""
    while len(raw) < n:
        v = _inc(v)
        raw += _aes(key, v)
    key, v = update(key, v, b"")
    out = []
    for b in raw:
        out.append((b >> 3) % Q if hi5 else b % Q)
        if len(out) >= n:
            break
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
        ("ctr_aes128", lambda s, n: ctr_drbg(s, n, keylen=16, hi5=False)),
        ("ctr_aes256", lambda s, n: ctr_drbg(s, n, keylen=32, hi5=False)),
        ("ctr_aes128_hi5", lambda s, n: ctr_drbg(s, n, keylen=16, hi5=True)),
    ]
    plants = {}
    a = ctr_drbg(3301, 32, keylen=16)
    plants["det"] = a == ctr_drbg(3301, 32, keylen=16)
    plants["ne_256"] = a != ctr_drbg(3301, 32, keylen=32)
    plants["ne_hi"] = a != ctr_drbg(3301, 32, keylen=16, hi5=True)
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
            "experiment": "EXP-LP-CTR-DRBG-001", "plant": plants,
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
            for gname, gen in (("ctr_aes128", gens[0][1]), ("ctr_aes256", gens[1][1])):
                ks = gen(seed, len(ct))
                for rel in ("sub", "add", "beau"):
                    tested_r += 1
                    rec = [apply_p(c, ks[i], rel) for i, c in enumerate(ct)]
                    lat = GP.latin_stream(rec)
                    sc = score_candidate(rec, lat)
                    row = {"pass": "rigid", "gen": gname, "seed": slabel, "span": tname,
                           "rel": rel, "head": lat[:80], **sc, "n": len(rec)}
                    if best is None or sc["trigram_per_100"] > best["trigram_per_100"]:
                        best = row
                    if keep(sc, len(rec)):
                        hits.append(row)
                        print("KEEP", gname, slabel, tname, rel, sc["trigram_per_100"], lat[:40], flush=True)
        for tname, ct in compact:
            ks = gens[2][1](seed, len(ct))
            for rel in ("sub", "add", "beau"):
                tested_r += 1
                rec = [apply_p(c, ks[i], rel) for i, c in enumerate(ct)]
                lat = GP.latin_stream(rec)
                sc = score_candidate(rec, lat)
                row = {"pass": "rigid", "gen": "ctr_aes128_hi5", "seed": slabel, "span": tname,
                       "rel": rel, "head": lat[:80], **sc, "n": len(rec)}
                if best is None or sc["trigram_per_100"] > best["trigram_per_100"]:
                    best = row
                if keep(sc, len(rec)):
                    hits.append(row)

    for slabel, seed in seeds:
        for tname, ct in (("prefix400", prefix(400)), ("split015", idxs_of(15))):
            for gname, gen in (("ctr_aes128", gens[0][1]), ("ctr_aes256", gens[1][1])):
                tested_b += 1
                ks = gen(seed, len(ct) * 4)
                rec = beam_decode(ct, ks)
                lat = GP.latin_stream(rec)
                sc = score_candidate(rec, lat)
                row = {"pass": "beam", "gen": gname, "seed": slabel, "span": tname,
                       "rel": "sub", "head": lat[:80], **sc, "n": len(rec)}
                if best is None or sc["trigram_per_100"] > best["trigram_per_100"]:
                    best = row
                if keep(sc, len(rec)):
                    hits.append(row)
                    print("KEEP beam", gname, slabel, tname, sc["trigram_per_100"], lat[:40], flush=True)

    result = {
        "experiment": "EXP-LP-CTR-DRBG-001",
        "family": "NIST CTR_DRBG AES-128/256 (`%29` + hi5); rigid + skip-aware beam",
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
        "boundary": "HMAC-DRBG and Hash_DRBG already closed; AES-CTR password keys already closed; not a 2^128 grind",
    }
    (OUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print("tested_r", tested_r, "tested_b", tested_b, "keeps", len(hits),
          "best", None if not best else (best["trigram_per_100"], best["gen"], best["head"][:40]))


if __name__ == "__main__":
    main()
