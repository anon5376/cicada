"""NIST SP 800-90A HMAC-DRBG (SHA-256) as a marked-seed keystream.

HKDF-SHA256 skip-aware is closed (EXP-LP-SKIPAWARE-STREAMCIPHERS-001).
HMAC-DRBG's (K,V) update is a different construction and was never a
keystream here.

Pure functions: no I/O. Output is a list of integers in 0..28.
"""
from __future__ import annotations

import hashlib
import hmac

Q = 29

PLANT_LATIN = (
    "THEPRIMESARESACREDTHETOTIENTFVNCTIANISSACREDALLTHNGSSHOVLDBEENCRYPTEDAWARNNGBELIEVENOTHNG"
)
PLANT_THRESHOLD = 0.90


def _hmac(key: bytes, msg: bytes) -> bytes:
    return hmac.new(key, msg, hashlib.sha256).digest()


def hmac_drbg(seed: bytes, n: int, hi: bool = False) -> list[int]:
    """Instantiate from seed, then generate n output bytes mapped to 0..28."""
    k = b"\x00" * 32
    v = b"\x01" * 32

    def update(data: bytes) -> None:
        nonlocal k, v
        k = _hmac(k, v + b"\x00" + data)
        v = _hmac(k, v)
        if data:
            k = _hmac(k, v + b"\x01" + data)
            v = _hmac(k, v)

    update(seed)
    out: list[int] = []
    while len(out) < n:
        v = _hmac(k, v)
        for b in v:
            out.append((b >> 3) % Q if hi else b % Q)
            if len(out) >= n:
                break
    return out


def hmac_drbg_int(seed: int, n: int, hi: bool = False) -> list[int]:
    return hmac_drbg(int(seed).to_bytes(8, "big"), n, hi)


def generators() -> list[tuple[str, callable]]:
    return [
        ("hmac_drbg_mod", lambda seed, n: hmac_drbg_int(seed, n, False)),
        ("hmac_drbg_hi", lambda seed, n: hmac_drbg_int(seed, n, True)),
    ]


def apply_p(c: int, k: int, rel: str) -> int:
    if rel == "sub":
        return (c - k) % Q
    if rel == "add":
        return (c + k) % Q
    return (k - c) % Q


def rigid_decrypt(ct: list[int], ks: list[int], rel: str = "sub") -> list[int]:
    return [apply_p(c, ks[i], rel) for i, c in enumerate(ct)]


def rigid_encrypt(pt: list[int], ks: list[int], rel: str = "sub") -> list[int]:
    if rel == "sub":
        return [(p + ks[i]) % Q for i, p in enumerate(pt)]
    if rel == "add":
        return [(p - ks[i]) % Q for i, p in enumerate(pt)]
    return [(ks[i] - p) % Q for i, p in enumerate(pt)]


def plant_rigid(gen_fn, seed: int, pt: list[int]) -> dict:
    ks = gen_fn(seed, len(pt))
    ct = rigid_encrypt(pt, ks, "sub")
    rec = rigid_decrypt(ct, ks, "sub")
    agree = sum(a == b for a, b in zip(rec, pt)) / len(pt)
    wrong_ks = gen_fn(seed ^ 0xA5A5A5A5, len(pt))
    rec_w = rigid_decrypt(ct, wrong_ks, "sub")
    agree_w = sum(a == b for a, b in zip(rec_w, pt)) / len(pt)
    return {
        "agree": agree,
        "ok": rec == pt,
        "wrong_agree": agree_w,
        "wrong_fails": rec_w != pt and agree_w < 0.4,
    }
