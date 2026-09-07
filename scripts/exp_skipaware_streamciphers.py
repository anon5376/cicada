#!/usr/bin/env python3
"""Skip-aware RC4 / ChaCha20 / HKDF / PBKDF2 on attested seeds and the pp49 blob.

SHA-256-CTR and AES-CTR of these seeds were already null. This is the rest of
the B-04 stream-cipher family on this repo's plant-validated beam.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from cicada.liber_primus.gematria import Gematria  # noqa: E402
from cicada.paths import ROOT as CICADA_ROOT  # noqa: E402
from cicada.scoring import score_candidate  # noqa: E402
from exp_grid_icc_headings import decode60, parse_rtkd_grid  # noqa: E402
from exp_skipaware_marsaglia import idxs_of, prefix  # noqa: E402
from exp_skipaware_sha_ctr import beam_decode, encrypt_reject, keep  # noqa: E402

GP = Gematria()
Q = 29
OUT = CICADA_ROOT / "experiments" / "EXP-LP-SKIPAWARE-STREAMCIPHERS-001"
SEEDS = [
    b"CICADA3301",
    b"3301",
    b"DIVINITY",
    b"AN END",
    b"LIBERPRIMUS",
    b"THELOSSOFDIVINITY",
    b"FIRFUMFERENFE",
    bytes.fromhex("6D854CD7933322A601C3286D181F01E57A35090F"),
]


def rc4(key: bytes, n: int) -> list[int]:
    s = list(range(256))
    j = 0
    for i in range(256):
        j = (j + s[i] + key[i % len(key)]) % 256
        s[i], s[j] = s[j], s[i]
    i = j = 0
    out: list[int] = []
    for _ in range(n):
        i = (i + 1) % 256
        j = (j + s[i]) % 256
        s[i], s[j] = s[j], s[i]
        out.append(s[(s[i] + s[j]) % 256] % Q)
    return out


def chacha20(key_seed: bytes, n: int) -> list[int] | None:
    try:
        from Crypto.Cipher import ChaCha20
    except Exception:
        return None
    key = hashlib.sha256(key_seed).digest()
    nonce = b"\x00" * 8
    ks = ChaCha20.new(key=key, nonce=nonce).encrypt(b"\x00" * n)
    return [b % Q for b in ks]


def hkdf_stream(seed: bytes, n: int) -> list[int]:
    prk = hmac.new(b"CICADA3301", seed, hashlib.sha256).digest()
    out: list[int] = []
    i = 1
    while len(out) < n:
        block = hmac.new(prk, i.to_bytes(4, "big"), hashlib.sha256).digest()
        for b in block:
            out.append(b % Q)
            if len(out) >= n:
                break
        i += 1
    return out


def pbkdf2_seed_ctr(seed: bytes, n: int, rounds: int) -> list[int]:
    stretched = hashlib.pbkdf2_hmac("sha256", seed, b"3301", rounds, dklen=32)
    out: list[int] = []
    i = 0
    while len(out) < n:
        d = hashlib.sha256(stretched + i.to_bytes(4, "big")).digest()
        for b in d:
            out.append(b % Q)
            if len(out) >= n:
                break
        i += 1
    return out


def payload() -> bytes:
    raw = parse_rtkd_grid()
    return bytes(decode60(raw))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    blob = payload()
    plant_pt = GP.encode_latin_key(
        "THEPRIMESARESACREDTHETOTIENTFVNCTIANISSACREDALLTHNGSSHOVLDBEENCRYPTEDAWARNNGBELIEVENOTHNG"
    )
    pks = rc4(b"CICADA3301", len(plant_pt) * 4)
    plant_ct, _ = encrypt_reject(plant_pt, pks)
    rec = beam_decode(plant_ct, pks)
    agree = sum(a == b for a, b in zip(rec, plant_pt)) / len(plant_pt) if rec else 0.0
    plant = {"agree": round(agree, 4), "ok": agree >= 0.95, "family": "rc4"}
    print("plant", plant, flush=True)

    targets = [("prefix400", prefix(400)), ("split015", idxs_of(15))]
    materials = [(s.decode("ascii", "replace") if isinstance(s, bytes) and s.isascii() else s.hex()[:16], s) for s in SEEDS]
    materials.append(("payload49", blob))
    hits = []
    tested = 0
    samples = []
    chacha_ok = chacha20(b"CICADA3301", 8) is not None

    for label, seed in materials:
        for span, ct in targets:
            need = len(ct) * 4
            streams = [
                ("rc4", rc4(seed, need)),
                ("hkdf", hkdf_stream(seed, need)),
                ("pbkdf2_3301", pbkdf2_seed_ctr(seed, need, 3301)),
            ]
            cc = chacha20(seed, need)
            if cc is not None:
                streams.append(("chacha20", cc))
            for mode, ks in streams:
                tested += 1
                pt = beam_decode(ct, ks)
                lat = GP.latin_stream(pt)
                sc = score_candidate(pt, lat)
                row = {"seed": label, "span": span, "mode": mode, "head": lat[:80], **sc}
                if tested <= 3 or (label == "CICADA3301" and mode == "rc4" and span == "prefix400"):
                    print(f"beam {label} {span} {mode} tri={sc['trigram_per_100']:.2f} {lat[:36]}", flush=True)
                    samples.append(row)
                if keep(sc, len(pt)):
                    hits.append(row)
                    print("KEEP", row, flush=True)

    print("tested", tested, "keeps", len(hits), "chacha", chacha_ok, flush=True)
    (OUT / "result.json").write_text(
        json.dumps(
            {"plant": plant, "tested": tested, "keeps": hits, "samples": samples, "chacha20": chacha_ok},
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
