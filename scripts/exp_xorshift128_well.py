#!/usr/bin/env python3
"""Marked-seed xorshift128+ and WELL512a (unused siblings of closed xorshift32 / xoroshiro).

Also skip-aware Vigenere on heading words that SKIPAWARE-VIGENERE-001 omitted
(INTUS, ANINSTRUCTION, FORALLISSACRED, AKOAN, BELIEVENOTHNG).
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
MASK64 = 0xFFFFFFFFFFFFFFFF
OUT = CICADA_ROOT / "experiments" / "EXP-LP-XORSHIFT128-WELL-001"

EXTRA_TITLES = (
    "INTUS", "ANINSTRUCTION", "FORALLISSACRED", "AKOAN", "BELIEVENOTHNG",
    "WITHIN", "DEEPWEB", "SEEKWITHIN",
)


def xorshift128p(seed: int, n: int) -> list[int]:
    """Vigna xorshift128+ (2016)."""
    s0 = (seed & MASK64) or 1
    s1 = (int.from_bytes(hashlib.sha256(seed.to_bytes(8, "big")).digest()[:8], "little") or 1)
    out: list[int] = []
    for _ in range(n):
        a, b = s0, s1
        result = (b + a) & MASK64
        out.append(result % Q)
        s0 = b
        a ^= (a << 23) & MASK64
        s1 = a ^ b ^ (a >> 18) ^ (b >> 5)
        s1 &= MASK64
    return out


def xorshift128p_hi5(seed: int, n: int) -> list[int]:
    s0 = (seed & MASK64) or 1
    s1 = (int.from_bytes(hashlib.sha256(seed.to_bytes(8, "big")).digest()[:8], "little") or 1)
    out: list[int] = []
    for _ in range(n):
        a, b = s0, s1
        result = (b + a) & MASK64
        out.append((result >> 59) % Q)
        s0 = b
        a ^= (a << 23) & MASK64
        s1 = (a ^ b ^ (a >> 18) ^ (b >> 5)) & MASK64
    return out


# WELL512a (Panneton/L'Ecuyer). 16×32-bit state.
def well512a(seed: int, n: int) -> list[int]:
    st = []
    x = seed & MASK32 or 1
    for i in range(16):
        x = (1664525 * x + 1013904223 + i) & MASK32
        st.append(x or 1)
    idx = 0
    out: list[int] = []
    for _ in range(n):
        a = st[idx]
        c = st[(idx + 13) & 15]
        b = a ^ c ^ ((a << 16) & MASK32) ^ ((c << 15) & MASK32)
        c = st[(idx + 9) & 15]
        c ^= c >> 11
        a = st[idx] = b ^ c
        d = a ^ (((a << 5) & MASK32) & 0xDA442D24)
        idx = (idx + 15) & 15
        a = st[idx]
        st[idx] = a ^ b ^ d ^ ((a << 2) & MASK32) ^ ((b << 18) & MASK32) ^ ((c << 28) & MASK32)
        out.append(st[idx] % Q)
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


def tile(key, n):
    return [key[i % len(key)] for i in range(n)]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    gens = [
        ("xorshift128p", xorshift128p),
        ("xorshift128p_hi5", xorshift128p_hi5),
        ("well512a", well512a),
    ]
    pt = GP.encode_latin_key(
        "THEPRIMESARESACREDTHETOTIENTFVNCTIANISSACREDALLTHNGSSHOVLDBEENCRYPTEDAWARNNGBELIEVENOTHNG"
    )
    plants = {}
    for name, gen in gens:
        ks = gen(3301, len(pt) * 4)
        rec = [(p + ks[i]) % Q for i, p in enumerate(pt)]
        plants[f"{name}_rigid"] = [apply_p(c, ks[i], "sub") for i, c in enumerate(rec)] == pt
        ct, _ = encrypt_reject(pt, ks)
        recb = beam_decode(ct, ks)
        agree = sum(a == b for a, b in zip(recb, pt)) / len(pt) if recb else 0.0
        plants[f"{name}_beam"] = {"agree": round(agree, 4), "ok": agree >= 0.89}
        wrong = gen(2014, len(pt))
        plants[f"{name}_wrong"] = [apply_p((p + ks[i]) % Q, wrong[i], "sub") for i, p in enumerate(pt)] != pt
    # extra titles plant
    k0 = GP.encode_latin_key("INTUS")
    pks = tile(k0, len(pt) * 4)
    ct, _ = encrypt_reject(pt, pks)
    recb = beam_decode(ct, pks)
    agree = sum(a == b for a, b in zip(recb, pt)) / len(pt) if recb else 0.0
    plants["intus_beam"] = {"agree": round(agree, 4), "ok": agree >= 0.89}
    plants["ok"] = all(
        (v is True) or (isinstance(v, dict) and v.get("ok"))
        for k, v in plants.items() if k != "ok"
    )
    print("plant", plants, flush=True)
    if not plants["ok"]:
        (OUT / "result.json").write_text(json.dumps({
            "experiment": "EXP-LP-XORSHIFT128-WELL-001", "plant": plants,
            "verified_new_unsolved_runes": 0, "aborted": "plant failed",
        }, indent=2) + "\n")
        return

    seeds = marked_seeds()
    pages = [(f"split{s:03d}", idxs_of(s)) for s in range(15, 71) if len(idxs_of(s)) >= 80]
    compact = [("prefix400", prefix(400))] + [
        (n, t) for n, t in pages if n in ("split015", "split017", "split040", "split063")
    ]
    hits, tested_r, tested_b, best = [], 0, 0, None
    primary = [g for g in gens if g[0] in ("xorshift128p", "well512a")]

    for gname, gen in primary:
        for slabel, seed in seeds:
            for tname, ct in ([("prefix400", prefix(400))] + pages if gname == "xorshift128p" else compact):
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

    for slabel, seed in seeds:
        for tname, ct in compact:
            ks = xorshift128p_hi5(seed, len(ct))
            for rel in ("sub", "add", "beau"):
                tested_r += 1
                rec = [apply_p(c, ks[i], rel) for i, c in enumerate(ct)]
                lat = GP.latin_stream(rec)
                sc = score_candidate(rec, lat)
                row = {"pass": "rigid", "gen": "xorshift128p_hi5", "seed": slabel, "span": tname,
                       "rel": rel, "head": lat[:80], **sc, "n": len(rec)}
                if best is None or sc["trigram_per_100"] > best["trigram_per_100"]:
                    best = row
                if keep(sc, len(rec)):
                    hits.append(row)

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

    for word in EXTRA_TITLES:
        try:
            key = GP.encode_latin_key(word)
        except ValueError:
            continue
        for tname, ct in (("prefix400", prefix(400)), ("split015", idxs_of(15))):
            tested_b += 1
            ks = tile(key, len(ct) * 4)
            rec = beam_decode(ct, ks)
            lat = GP.latin_stream(rec)
            sc = score_candidate(rec, lat)
            row = {"pass": "beam", "gen": f"title:{word}", "seed": word, "span": tname,
                   "rel": "sub", "head": lat[:80], **sc, "n": len(rec)}
            if best is None or sc["trigram_per_100"] > best["trigram_per_100"]:
                best = row
            if keep(sc, len(rec)):
                hits.append(row)
                print("KEEP title", word, tname, sc["trigram_per_100"], lat[:40], flush=True)

    result = {
        "experiment": "EXP-LP-XORSHIFT128-WELL-001",
        "family": "xorshift128+ / WELL512a + skip-aware omitted heading titles",
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
    }
    (OUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print("tested_r", tested_r, "tested_b", tested_b, "keeps", len(hits),
          "best", None if not best else (best["trigram_per_100"], best["gen"], best["head"][:40]))


if __name__ == "__main__":
    main()
