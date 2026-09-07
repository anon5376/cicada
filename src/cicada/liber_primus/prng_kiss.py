"""Marsaglia multiply-with-carry / KISS / complementary-MWC keystreams.

These are the short-seed binary generators left after LCG, lagged-Fibonacci,
MT19937, xorshift32, xoroshiro64**, PCG-XSH-RR, Galois LFSR, and ISAAC were
closed. State is 2^32-class, so only marked seeds — not a 2^32 grind.

Pure functions: no I/O. Output is a list of integers in 0..28.
"""
from __future__ import annotations

import hashlib

Q = 29
MASK32 = 0xFFFFFFFF

# Marsaglia 1999 KISS / 16-bit MWC multipliers.
MWC_Z_A = 36969
MWC_W_A = 18000
# 32-bit MWC multiplier from Marsaglia (numeric recipes / posting).
MWC32_A = 4294957665
# KISS99 congruential and 64-bit MWC.
KISS_LCG_A = 69069
KISS_LCG_C = 12345
KISS_MWC64_A = 698769069
# Small-lag complementary MWC (r=3). Multiplier 18782 is Marsaglia's published
# CMWC constant (normally paired with r=4095; lag-3 is the compact marked-seed
# cousin, not the 4096-word generator).
CMWC_R = 3
CMWC_A = 18782

PLANT_LATIN = (
    "THEPRIMESARESACREDTHETOTIENTFVNCTIANISSACREDALLTHNGSSHOVLDBEENCRYPTEDAWARNNGBELIEVENOTHNG"
)
PLANT_THRESHOLD = 0.90


def _nz32(x: int) -> int:
    return (x & MASK32) or 1


def seed_words(seed: int) -> tuple[int, int, int, int]:
    """Expand one marked 32/64-bit integer into four nonzero uint32 words."""
    h = hashlib.sha256(int(seed).to_bytes(8, "big")).digest()
    words = [int.from_bytes(h[i : i + 4], "big") or 1 for i in range(0, 16, 4)]
    return words[0], words[1], words[2], words[3]


def _mod29(x: int) -> int:
    return (x & MASK32) % Q


def _hi5(x: int) -> int:
    return ((x & MASK32) >> 27) % Q


def mwc16(seed: int, n: int, hi: bool = False) -> list[int]:
    """Concatenated 16-bit MWC (Marsaglia znew/wnew)."""
    z, w, _, _ = seed_words(seed)
    out: list[int] = []
    take = _hi5 if hi else _mod29
    for _ in range(n):
        z = (MWC_Z_A * (z & 65535) + (z >> 16)) & MASK32
        w = (MWC_W_A * (w & 65535) + (w >> 16)) & MASK32
        val = ((z << 16) + (w & 65535)) & MASK32
        out.append(take(val))
    return out


def mwc32(seed: int, n: int, hi: bool = False) -> list[int]:
    """32-bit multiply-with-carry, a = 4294957665."""
    x, c, _, _ = seed_words(seed)
    out: list[int] = []
    take = _hi5 if hi else _mod29
    a = MWC32_A
    for _ in range(n):
        t = a * x + c
        c = t >> 32
        x = t & MASK32
        if x == 0 and c == 0:
            x = 1
        out.append(take(x))
    return out


def kiss99(seed: int, n: int, hi: bool = False) -> list[int]:
    """Marsaglia 1999 KISS: MWC64 + xorshift SHR3 + LCG, summed."""
    x, y, z, c = seed_words(seed)
    out: list[int] = []
    take = _hi5 if hi else _mod29
    a = KISS_MWC64_A
    for _ in range(n):
        x = (KISS_LCG_A * x + KISS_LCG_C) & MASK32
        y ^= (y << 13) & MASK32
        y ^= y >> 17
        y ^= (y << 5) & MASK32
        y &= MASK32
        t = a * z + c
        c = t >> 32
        z = t & MASK32
        val = (x + y + z) & MASK32
        out.append(take(val))
    return out


def cmwc_lag3(seed: int, n: int, hi: bool = False) -> list[int]:
    """Complementary multiply-with-carry, lag r=3, b=2^32."""
    w0, w1, w2, c = seed_words(seed)
    q = [w0, w1, w2]
    i = 0
    out: list[int] = []
    take = _hi5 if hi else _mod29
    a = CMWC_A
    for _ in range(n):
        t = a * q[i] + c
        c = t >> 32
        x = (MASK32 - (t & MASK32)) & MASK32
        if x == 0:
            x = 1
        q[i] = x
        i = (i + 1) % CMWC_R
        out.append(take(x))
    return out


def generators() -> list[tuple[str, callable]]:
    """Named (seed, n) -> list[int] keystream factories."""
    return [
        ("kiss99_mod", lambda seed, n: kiss99(seed, n, False)),
        ("kiss99_hi", lambda seed, n: kiss99(seed, n, True)),
        ("mwc16_mod", lambda seed, n: mwc16(seed, n, False)),
        ("mwc16_hi", lambda seed, n: mwc16(seed, n, True)),
        ("mwc32_mod", lambda seed, n: mwc32(seed, n, False)),
        ("mwc32_hi", lambda seed, n: mwc32(seed, n, True)),
        ("cmwc_lag3_mod", lambda seed, n: cmwc_lag3(seed, n, False)),
        ("cmwc_lag3_hi", lambda seed, n: cmwc_lag3(seed, n, True)),
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
    """Inverse of rigid_decrypt for the same rel."""
    if rel == "sub":
        return [(p + ks[i]) % Q for i, p in enumerate(pt)]
    if rel == "add":
        return [(p - ks[i]) % Q for i, p in enumerate(pt)]
    return [(ks[i] - p) % Q for i, p in enumerate(pt)]


def plant_rigid(gen_fn, seed: int, pt: list[int]) -> dict:
    """Exact additive roundtrip. Wrong seed must not recover pt."""
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
