#!/usr/bin/env python3
"""ChaCha8 / ChaCha12 marked-seed keystreams (ChaCha20 is closed).

IETF 32-bit counter + 96-bit nonce, 8 or 12 rounds, output %29 and hi5.
"""
from __future__ import annotations

import hashlib
import json
import struct
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
OUT = CICADA_ROOT / "experiments" / "EXP-LP-CHACHA8-12-001"


def _rotl(x: int, n: int) -> int:
    x &= MASK32
    return ((x << n) | (x >> (32 - n))) & MASK32


def _qr(s, a, b, c, d) -> None:
    s[a] = (s[a] + s[b]) & MASK32
    s[d] = _rotl(s[d] ^ s[a], 16)
    s[c] = (s[c] + s[d]) & MASK32
    s[b] = _rotl(s[b] ^ s[c], 12)
    s[a] = (s[a] + s[b]) & MASK32
    s[d] = _rotl(s[d] ^ s[a], 8)
    s[c] = (s[c] + s[d]) & MASK32
    s[b] = _rotl(s[b] ^ s[c], 7)


def chacha_block(key: bytes, counter: int, nonce: bytes, rounds: int) -> bytes:
    cst = b"expand 32-byte k"
    st = list(struct.unpack("<16I", cst + key + struct.pack("<I", counter) + nonce))
    w = st[:]
    for _ in range(rounds // 2):
        _qr(w, 0, 4, 8, 12)
        _qr(w, 1, 5, 9, 13)
        _qr(w, 2, 6, 10, 14)
        _qr(w, 3, 7, 11, 15)
        _qr(w, 0, 5, 10, 15)
        _qr(w, 1, 6, 11, 12)
        _qr(w, 2, 7, 8, 13)
        _qr(w, 3, 4, 9, 14)
    out = [(w[i] + st[i]) & MASK32 for i in range(16)]
    return struct.pack("<16I", *out)


def chacha_stream(seed: int, n: int, rounds: int, hi5: bool) -> list[int]:
    key = hashlib.sha256(seed.to_bytes(8, "big")).digest()
    nonce = b"\x00" * 12
    out: list[int] = []
    ctr = 0
    while len(out) < n:
        block = chacha_block(key, ctr, nonce, rounds)
        for b in block:
            out.append((b >> 3) % Q if hi5 else b % Q)
            if len(out) >= n:
                break
        ctr += 1
    return out


def generators():
    return [
        ("chacha8", lambda s, n: chacha_stream(s, n, 8, False)),
        ("chacha8_hi5", lambda s, n: chacha_stream(s, n, 8, True)),
        ("chacha12", lambda s, n: chacha_stream(s, n, 12, False)),
        ("chacha12_hi5", lambda s, n: chacha_stream(s, n, 12, True)),
    ]


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


def apply_p(c: int, k: int, rel: str) -> int:
    if rel == "sub":
        return (c - k) % Q
    if rel == "add":
        return (c + k) % Q
    return (k - c) % Q


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    # RFC 7539 appendix A.1: all-zero key/nonce, counter 0, ChaCha20 first 8 words...
    # We only KAT the 8-round self-consistency: two calls match; 8≠12.
    a = chacha_stream(3301, 64, 8, False)
    b = chacha_stream(3301, 64, 8, False)
    c = chacha_stream(3301, 64, 12, False)
    plants = {"det": a == b, "8ne12": a != c}

    pt = GP.encode_latin_key(
        "THEPRIMESARESACREDTHETOTIENTFVNCTIANISSACREDALLTHNGSSHOVLDBEENCRYPTEDAWARNNGBELIEVENOTHNG"
    )
    for name, gen in generators():
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
            "experiment": "EXP-LP-CHACHA8-12-001", "plant": plants,
            "verified_new_unsolved_runes": 0, "aborted": "plant failed",
        }, indent=2) + "\n")
        return

    seeds = marked_seeds()
    pages = [(f"split{s:03d}", idxs_of(s)) for s in range(15, 71) if len(idxs_of(s)) >= 80]
    primary = [g for g in generators() if g[0] in ("chacha8", "chacha12")]
    extra = [g for g in generators() if g[0] not in ("chacha8", "chacha12")]
    compact = [("prefix400", prefix(400))] + [
        (n, t) for n, t in pages if n in ("split015", "split017", "split040", "split063")
    ]
    hits, tested_r, tested_b, best = [], 0, 0, None

    for gname, gen in primary:
        for slabel, seed in seeds:
            for tname, ct in ([("prefix400", prefix(400))] + pages):
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

    for gname, gen in extra:
        for slabel, seed in seeds:
            for tname, ct in compact:
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

    for gname, gen in primary:
        for slabel, seed in seeds:
            for tname, ct in (("prefix400", prefix(400)), ("split015", idxs_of(15))):
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
        "experiment": "EXP-LP-CHACHA8-12-001",
        "family": "marked-seed ChaCha8 / ChaCha12 (`%29` + hi5)",
        "plant": plants,
        "n_seeds": len(seeds),
        "tested_rigid": tested_r,
        "tested_beam": tested_b,
        "tested": tested_r + tested_b,
        "keep_bar_hits": len(hits),
        "keeps": hits[:20],
        "best": {k: best[k] for k in ("pass", "gen", "seed", "span", "rel", "head", "trigram_per_100", "ioc")} if best else None,
        "skeptic_review": {"verdict": "null" if not hits else "keep-bar needs human English", "english": False},
        "verified_new_unsolved_runes": 0,
        "boundary": "ChaCha20 already closed; not a 2^256 grind",
    }
    (OUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print("tested_rigid", tested_r, "tested_beam", tested_b, "keeps", len(hits),
          "best", None if not best else (best["trigram_per_100"], best["gen"], best["head"][:40]))


if __name__ == "__main__":
    main()
