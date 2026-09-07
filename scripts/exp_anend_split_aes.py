#!/usr/bin/env python3
"""AN END 128-hex as 5-line interleave: 160-bit v2 onion + 352-bit leftover.

Does not contact onion services. Tests leftover bytes as AES-CTR / repeating
key / SHA-256-CTR against unsolved runes. Verifies the published base32 claim.
"""
from __future__ import annotations

import base64
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cicada.liber_primus.gematria import Gematria  # noqa: E402
from cicada.paths import ROOT as CICADA_ROOT  # noqa: E402
from cicada.scoring import score_candidate  # noqa: E402

GP = Gematria()
PAGE_DIR = CICADA_ROOT / "corpus/normalized/rtkd_pages"
OUT = CICADA_ROOT / "experiments" / "EXP-LP-ANEND-SPLIT-AES-001"

LINES = [
    "36367763ab73783c7af284446c",
    "59466b4cd653239a311cb7116",
    "d4618dee09a8425893dc7500b",
    "464fdaf1672d7bef5e891c6e227",
    "4568926a49fb4f45132c2a8b4",
]


def idxs_flat() -> list[int]:
    out = []
    for s in range(15, 71):
        out.extend(GP.rune_indices((PAGE_DIR / f"split_{s:03d}.txt").read_text(encoding="utf-8")))
    return out


def keep(sc: dict, n: int) -> bool:
    return (
        n >= 80
        and sc["trigram_per_100"] >= 3.5
        and 0.28 <= sc["vowelish_ratio"] <= 0.55
        and sc["ioc"] >= 0.045
    )


def sha256_ctr(seed: bytes, n: int, start: int = 0) -> list[int]:
    out: list[int] = []
    i = start
    while len(out) < n:
        d = hashlib.sha256(seed + i.to_bytes(4, "big")).digest()
        for b in d:
            out.append(b % 29)
            if len(out) >= n:
                break
        i += 1
    return out


def pack5(idxs: list[int]) -> bytes:
    bits = "".join(f"{x % 29:05b}" for x in idxs)
    bits += "0" * ((8 - len(bits) % 8) % 8)
    return int(bits, 2).to_bytes(len(bits) // 8, "big")


def unpack5(data: bytes, n: int) -> list[int]:
    bits = "".join(f"{b:08b}" for b in data)
    out = []
    for i in range(0, min(len(bits) - 4, 5 * n), 5):
        v = int(bits[i : i + 5], 2)
        if v < 29:
            out.append(v)
        else:
            out.append(v % 29)
        if len(out) >= n:
            break
    return out


def score_ks(ct: list[int], ks: list[int], rel: str) -> dict:
    if rel == "sub":
        out = [(ct[i] - ks[i % len(ks)]) % 29 for i in range(len(ct))]
    elif rel == "add":
        out = [(ct[i] + ks[i % len(ks)]) % 29 for i in range(len(ct))]
    else:
        out = [(ks[i % len(ks)] - ct[i]) % 29 for i in range(len(ct))]
    latin = GP.latin_stream(out)
    sc = score_candidate(out, latin)
    sc["head"] = latin[:80]
    return sc


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    joined = "".join(LINES)
    assert len(joined) == 128
    first8 = "".join(ln[:8] for ln in LINES)
    rest = "".join(ln[8:] for ln in LINES)
    last8 = "".join(ln[-8:] for ln in LINES)
    rest_last = "".join(ln[:-8] for ln in LINES)
    onion160 = bytes.fromhex(first8)
    leftover = bytes.fromhex(rest)
    # RFC 4648 base32, no pad
    b32 = base64.b32encode(onion160).decode("ascii").rstrip("=").lower()
    print("first8", first8, "bytes", len(onion160))
    print("base32", b32, "claimed gy3hoy2zizvuzvdb", b32 == "gy3hoy2zizvuzvdb")
    print("leftover", len(leftover), "key32", leftover[:32].hex()[:16], "nonce", leftover[32:].hex())

    prefix = idxs_flat()[:900]
    sec = []
    for s in range(15, 18):
        sec.extend(GP.rune_indices((PAGE_DIR / f"split_{s:03d}.txt").read_text(encoding="utf-8")))

    blobs = {
        "leftover44": leftover,
        "aeskey32": leftover[:32],
        "nonce12": leftover[32:],
        "onion20": onion160,
        "last8_20": bytes.fromhex(last8),
        "rest_last": bytes.fromhex(rest_last),
    }
    hits = []
    tested = 0
    for name, blob in blobs.items():
        if not blob:
            continue
        key29 = [b % 29 for b in blob]
        for rel in ("sub", "add", "beau"):
            tested += 1
            sc = score_ks(prefix, key29, rel)
            print(f"rep {name:12s} {rel:4s} tri={sc['trigram_per_100']:.2f} ioc={sc['ioc']:.3f} {sc['head'][:48]}")
            if keep(sc, len(prefix)):
                hits.append({"src": name, "kind": f"rep_{rel}", **sc})
        tested += 1
        ks = sha256_ctr(hashlib.sha256(blob).digest(), len(prefix))
        sc = score_ks(prefix, ks, "sub")
        print(f"ctr {name:12s}      tri={sc['trigram_per_100']:.2f} {sc['head'][:48]}")
        if keep(sc, len(prefix)):
            hits.append({"src": name, "kind": "sha_ctr", **sc})

    # AES-CTR if available
    aes_note = "no AES"
    try:
        from Crypto.Cipher import AES
        from Crypto.Util import Counter

        key, nonce = leftover[:32], leftover[32:]
        packed = pack5(prefix)
        for label, nce in (("nonce12", nonce), ("nonce8", nonce[:8] if len(nonce) >= 8 else nonce)):
            try:
                ctr = Counter.new(128, prefix=nce) if len(nce) < 16 else Counter.new(128, prefix=nce[:8])
            except Exception:
                ctr = Counter.new(64, prefix=nce[:8])
            try:
                ciph = AES.new(key, AES.MODE_CTR, counter=ctr)
                ptb = ciph.decrypt(packed)
                out = unpack5(ptb, len(prefix))
                tested += 1
                latin = GP.latin_stream(out)
                sc = score_candidate(out, latin)
                print(f"aes {label:12s}      tri={sc['trigram_per_100']:.2f} ioc={sc['ioc']:.3f} {latin[:48]}")
                if keep(sc, len(out)):
                    hits.append({"src": label, "kind": "aes_ctr_5bit", "head": latin[:80], **sc})
            except Exception as e:
                aes_note = f"aes fail {label}: {e}"
                print(aes_note)
        # also AES-CTR of raw rune-as-byte
        raw = bytes(prefix)
        try:
            ctr = Counter.new(64, prefix=nonce[:8])
            ptb = AES.new(key, AES.MODE_CTR, counter=ctr).decrypt(raw)
            out = [b % 29 for b in ptb]
            tested += 1
            latin = GP.latin_stream(out)
            sc = score_candidate(out, latin)
            print(f"aes rune-byte       tri={sc['trigram_per_100']:.2f} {latin[:48]}")
            if keep(sc, len(out)):
                hits.append({"src": "aes_runebyte", "kind": "aes_ctr", "head": latin[:80], **sc})
        except Exception as e:
            print("aes rune-byte fail", e)
        aes_note = "pycrypto AES-CTR ran"
    except ImportError as e:
        aes_note = f"import {e}"

    print("tested", tested, "hits", len(hits), aes_note)
    (OUT / "result.json").write_text(
        json.dumps(
            {
                "first8_hex": first8,
                "base32": b32,
                "onion_claim_matches": b32 == "gy3hoy2zizvuzvdb",
                "leftover_n": len(leftover),
                "tested": tested,
                "hits": hits,
                "aes_note": aes_note,
                "onion_note": "v2 address derived only; not fetched (onion probing disallowed; v2 retired)",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
