"""Salsa20/20 and SHAKE256-XOF keystreams (unused siblings of ChaCha20 / SHA3-256-CTR).

ChaCha20 skip-aware is closed (EXP-LP-SKIPAWARE-STREAMCIPHERS-001).
SHA3-256 counter-mode is closed (EXP-LP-SKIPAWARE-SHA3-DEE-001).
Salsa20/20 (Bernstein 2008) and SHAKE256 as a pure XOF were not a keystream
in this tree. Marked seeds only.

Pure functions: no I/O. Output is a list of integers in 0..28.
"""
from __future__ import annotations

import hashlib
import struct

Q = 29
MASK32 = 0xFFFFFFFF

# "expand 32-byte k" as little-endian uint32
_SIGMA = (0x61707865, 0x3320646E, 0x79622D32, 0x6B206574)

PLANT_LATIN = (
    "THEPRIMESARESACREDTHETOTIENTFVNCTIANISSACREDALLTHNGSSHOVLDBEENCRYPTEDAWARNNGBELIEVENOTHNG"
)
PLANT_THRESHOLD = 0.90

# eSTREAM Salsa20/20 set 6 vector 0, stream[0..63]
SALSA20_TV_KEY = bytes.fromhex(
    "0053A6F94C9FF24598EB3E91E4378ADD3083D6297CCF2275C81B6EC11467BA0D"
)
SALSA20_TV_IV = bytes.fromhex("0D74DB42A91077DE")
SALSA20_TV_BLOCK0 = bytes.fromhex(
    "F5FAD53F79F9DF58C4AEA0D0ED9A9601"
    "F278112CA7180D565B420A48019670EA"
    "F24CE493A86263F677B46ACE1924773D"
    "2BB25571E1AA8593758FC382B1280B71"
)


def _rotl(x: int, n: int) -> int:
    x &= MASK32
    return ((x << n) | (x >> (32 - n))) & MASK32


def _quarterround(s: list[int], a: int, b: int, c: int, d: int) -> None:
    s[b] ^= _rotl(s[a] + s[d], 7)
    s[c] ^= _rotl(s[b] + s[a], 9)
    s[d] ^= _rotl(s[c] + s[b], 13)
    s[a] ^= _rotl(s[d] + s[c], 18)


def salsa20_block(key: bytes, nonce: bytes, counter: int) -> bytes:
    """One 64-byte Salsa20/20 block. key=32 bytes, nonce=8 bytes."""
    if len(key) != 32:
        raise ValueError("Salsa20 key must be 32 bytes")
    if len(nonce) != 8:
        raise ValueError("Salsa20 nonce must be 8 bytes")
    k = struct.unpack("<8I", key)
    n0, n1 = struct.unpack("<2I", nonce)
    c0 = counter & MASK32
    c1 = (counter >> 32) & MASK32
    x = [
        _SIGMA[0], k[0], k[1], k[2],
        k[3], _SIGMA[1], n0, n1,
        c0, c1, _SIGMA[2], k[4],
        k[5], k[6], k[7], _SIGMA[3],
    ]
    z = list(x)
    for _ in range(10):
        _quarterround(z, 0, 4, 8, 12)
        _quarterround(z, 5, 9, 13, 1)
        _quarterround(z, 10, 14, 2, 6)
        _quarterround(z, 15, 3, 7, 11)
        _quarterround(z, 0, 1, 2, 3)
        _quarterround(z, 5, 6, 7, 4)
        _quarterround(z, 10, 11, 8, 9)
        _quarterround(z, 15, 12, 13, 14)
    out = [(z[i] + x[i]) & MASK32 for i in range(16)]
    return struct.pack("<16I", *out)


def salsa20_bytes(key: bytes, n: int, nonce: bytes = b"\x00" * 8) -> bytes:
    buf = bytearray()
    ctr = 0
    while len(buf) < n:
        buf.extend(salsa20_block(key, nonce, ctr))
        ctr += 1
    return bytes(buf[:n])


def _key32_from_seed(seed: int) -> bytes:
    return hashlib.sha256(int(seed).to_bytes(8, "big")).digest()


def _key32_from_bytes(seed: bytes) -> bytes:
    return hashlib.sha256(seed).digest() if len(seed) != 32 else seed


def salsa20_mod(seed: int, n: int, hi: bool = False) -> list[int]:
    raw = salsa20_bytes(_key32_from_seed(seed), n)
    if hi:
        return [(b >> 3) % Q for b in raw]
    return [b % Q for b in raw]


def salsa20_mod_bytes(seed: bytes, n: int, hi: bool = False) -> list[int]:
    raw = salsa20_bytes(_key32_from_bytes(seed), n)
    if hi:
        return [(b >> 3) % Q for b in raw]
    return [b % Q for b in raw]


def shake256_mod(seed: bytes, n: int, hi: bool = False) -> list[int]:
    """Pure SHAKE256 XOF (not SHA3-256(seed||counter))."""
    raw = hashlib.shake_256(seed).digest(n)
    if hi:
        return [(b >> 3) % Q for b in raw]
    return [b % Q for b in raw]


def shake256_mod_int(seed: int, n: int, hi: bool = False) -> list[int]:
    return shake256_mod(int(seed).to_bytes(8, "big"), n, hi)


def generators() -> list[tuple[str, callable]]:
    """Named (seed: int, n) -> list[int] factories."""
    return [
        ("salsa20_mod", lambda seed, n: salsa20_mod(seed, n, False)),
        ("salsa20_hi", lambda seed, n: salsa20_mod(seed, n, True)),
        ("shake256_mod", lambda seed, n: shake256_mod_int(seed, n, False)),
        ("shake256_hi", lambda seed, n: shake256_mod_int(seed, n, True)),
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
