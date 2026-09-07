#!/usr/bin/env python3
"""Page-56 single-F skip replay + AN END hash as key/seed on unsolved runes."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cicada.liber_primus.ciphers import atbash, vigenere_decrypt  # noqa: E402
from cicada.liber_primus.fixtures import load_fixtures  # noqa: E402
from cicada.liber_primus.gematria import Gematria, first_n_primes  # noqa: E402
from cicada.paths import ROOT as CICADA_ROOT  # noqa: E402
from cicada.scoring import score_candidate  # noqa: E402

GP = Gematria()
PAGE_DIR = CICADA_ROOT / "corpus/normalized/rtkd_pages"
OUT = CICADA_ROOT / "experiments" / "EXP-LP-ANEND-HASH-001"

HASH_HEX = (
    "36367763ab73783c7af284446c"
    "59466b4cd653239a311cb7116"
    "d4618dee09a8425893dc7500b"
    "464fdaf1672d7bef5e891c6e227"
    "4568926a49fb4f45132c2a8b4"
)
# wiki lines as printed (may include the extra nibbles that make 128)
HASH_LINES = [
    "36367763ab73783c7af284446c",
    "59466b4cd653239a311cb7116",
    "d4618dee09a8425893dc7500b",
    "464fdaf1672d7bef5e891c6e227",
    "4568926a49fb4f45132c2a8b4",
]
EXPECTED_P56 = (
    "ANENDWITHINTHEDEEPWEBTHEREEXISTSAPAGETHATHASHESTO"
    "ITISTHEDVTYOFEVERYPILGRIMTOSEECOVTTHISPAGE"
)


def totient_skip_indices(idxs: list[int], skip: set[int]) -> list[int]:
    primes = first_n_primes(len(idxs) + 5)
    out = []
    k = 0
    for i, x in enumerate(idxs):
        if i in skip:
            out.append(x % 29)
            continue
        out.append((x - (primes[k] - 1)) % 29)
        k += 1
    return out


def page56() -> dict:
    fix = [f for f in load_fixtures() if f["stage_id"] == "lp2.page56_an_end"][0]
    c56 = GP.rune_indices(fix["ciphertext"])
    fpos = [i for i, x in enumerate(c56) if x == 0]
    variants = {}
    for name, skip in (
        ("none", set()),
        ("all_ct_F", set(fpos)),
        ("fourth_F_i56", {56} if len(c56) > 56 else set()),
        ("fpos3", {fpos[3]} if len(fpos) > 3 else set()),
    ):
        out = totient_skip_indices(c56, skip)
        latin = GP.latin_stream(out)
        variants[name] = {
            "latin": latin,
            "agree_expected": sum(a == b for a, b in zip(latin, EXPECTED_P56)) / len(EXPECTED_P56),
            "eq": latin == EXPECTED_P56,
        }
    # also try skip where plaintext would be F under no-skip (doesn't apply midstream)
    return {"n": len(c56), "fpos": fpos, "variants": variants, "expected": EXPECTED_P56}


def sha256_ctr(seed: bytes, n: int, width: int = 4, endian: str = "big") -> list[int]:
    out: list[int] = []
    i = 0
    while len(out) < n:
        digest = hashlib.sha256(seed + i.to_bytes(width, endian)).digest()
        for b in digest:
            out.append(b % 29)
            if len(out) >= n:
                break
        i += 1
    return out


def flatten_unsolved() -> list[int]:
    flat = []
    for s in range(15, 71):
        flat.extend(GP.rune_indices((PAGE_DIR / f"split_{s:03d}.txt").read_text(encoding="utf-8")))
    return flat


def interesting(sc: dict, n: int) -> bool:
    # calibrated to solved English: warning atbash is ~4.0 trigrams/100
    if n >= 80 and sc["trigram_per_100"] >= 3.5 and 0.28 <= sc["vowelish_ratio"] <= 0.55 and sc["ioc"] >= 0.045:
        return True
    if n >= 200 and sc["trigram_per_100"] >= 2.8 and sc["ioc"] >= 0.05:
        return True
    return False


def hash_attacks(flat: list[int]) -> dict:
    compact = HASH_HEX
    raw = bytes.fromhex(compact) if len(compact) % 2 == 0 else bytes.fromhex(compact[:-1])
    # first-8-of-each-line 160-bit (monokro)
    prefix40 = "".join(line[:8] for line in HASH_LINES)
    raw40 = bytes.fromhex(prefix40)
    seeds = {
        "hash_raw64": raw,
        "hash_hex_ascii": compact.encode(),
        "hash_sha256": hashlib.sha256(raw).digest(),
        "hash_hex_sha256": hashlib.sha256(compact.encode()).digest(),
        "monokro40": raw40,
        "monokro40_sha": hashlib.sha256(raw40).digest(),
        "line0": bytes.fromhex(HASH_LINES[0]),
    }
    keys = {
        "raw%29": [b % 29 for b in raw],
        "raw40%29": [b % 29 for b in raw40],
        "nibbles": [int(ch, 16) % 29 for ch in compact],
    }
    n = min(len(flat), 900)
    ct = flat[:n]
    kept = []
    tested = 0
    for kn, key in keys.items():
        if not key:
            continue
        for rel, out in (
            ("sub", vigenere_decrypt(ct, key)),
            ("add", [(ct[i] + key[i % len(key)]) % 29 for i in range(n)]),
            ("beau", [(key[i % len(key)] - ct[i]) % 29 for i in range(n)]),
            ("sub_atb", vigenere_decrypt(atbash(ct), key)),
        ):
            tested += 1
            latin = GP.latin_stream(out)
            sc = score_candidate(out, latin)
            rec = {"kind": "repeat", "id": kn, "rel": rel, "head": latin[:90], **sc}
            if interesting(sc, n) or sc["trigram_per_100"] >= 3.2:
                kept.append(rec)
    for sn, seed in seeds.items():
        for width, endian, prehash in ((4, "big", False), (4, "little", False), (8, "big", False), (4, "big", True)):
            material = hashlib.sha256(seed).digest() if prehash else seed
            ks = sha256_ctr(material, n, width, endian)
            for rel, out in (
                ("sub", [(ct[i] - ks[i]) % 29 for i in range(n)]),
                ("add", [(ct[i] + ks[i]) % 29 for i in range(n)]),
                ("beau", [(ks[i] - ct[i]) % 29 for i in range(n)]),
            ):
                tested += 1
                latin = GP.latin_stream(out)
                sc = score_candidate(out, latin)
                rec = {
                    "kind": "ctr",
                    "id": sn,
                    "width": width,
                    "endian": endian,
                    "prehash": prehash,
                    "rel": rel,
                    "head": latin[:90],
                    **sc,
                }
                if interesting(sc, n) or sc["trigram_per_100"] >= 3.2:
                    kept.append(rec)
    # per-page repeating hash key
    page_hits = []
    key = [b % 29 for b in raw]
    for s in range(15, 71):
        ix = GP.rune_indices((PAGE_DIR / f"split_{s:03d}.txt").read_text(encoding="utf-8"))
        if len(ix) < 40:
            continue
        tested += 1
        out = vigenere_decrypt(ix, key)
        latin = GP.latin_stream(out)
        sc = score_candidate(out, latin)
        if interesting(sc, len(ix)) or (sc["trigram_per_100"] >= 5 and sc["ioc"] >= 0.045):
            page_hits.append({"split": s, "head": latin[:80], **sc})
    kept.sort(key=lambda r: r.get("trigram_per_100", 0), reverse=True)
    return {
        "hash_len_hex": len(compact),
        "raw_len": len(raw),
        "tested": tested,
        "kept": kept[:25],
        "n_kept": len(kept),
        "page_hits": page_hits,
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    p56 = page56()
    (OUT / "page56.json").write_text(json.dumps(p56, indent=2) + "\n", encoding="utf-8")
    print("P56 fpos", p56["fpos"])
    for k, v in p56["variants"].items():
        print(f"  {k:16s} eq={v['eq']} agree={v['agree_expected']:.3f} {v['latin'][:95]}")

    flat = flatten_unsolved()
    print("unsolved", len(flat))
    att = hash_attacks(flat)
    (OUT / "hash_key.json").write_text(json.dumps(att, indent=2) + "\n", encoding="utf-8")
    print("hash tested", att["tested"], "kept", att["n_kept"], "page_hits", att["page_hits"])
    for r in att["kept"][:8]:
        print(" KEEP", r.get("kind"), r.get("id"), r.get("rel"), r.get("trigram_per_100"), r.get("head", "")[:70])


if __name__ == "__main__":
    main()
