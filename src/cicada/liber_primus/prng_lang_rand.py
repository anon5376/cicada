"""Language-default RNGs as marked-seed keystreams.

Affine LCG *mod 29* is closed exhaustively (EXP-LP-LCG-MOD29-001). That is
not Java's 48-bit LCG (output >>> 16), glibc TYPE_0 rand, or SplitMix64.
Those machines were never a keystream here.

Pure functions: no I/O. Output is a list of integers in 0..28.
"""
from __future__ import annotations

Q = 29
MASK32 = 0xFFFFFFFF
MASK48 = (1 << 48) - 1
MASK64 = (1 << 64) - 1
JAVA_MULT = 0x5DEECE66D
JAVA_ADD = 0xB
GLIBC_A = 1103515245
GLIBC_C = 12345
SPLITMIX_GAMMA = 0x9E3779B97F4A7C15
SPLITMIX_M1 = 0xBF58476D1CE4E5B9
SPLITMIX_M2 = 0x94D049BB133111EB

PLANT_LATIN = (
    "THEPRIMESARESACREDTHETOTIENTFVNCTIANISSACREDALLTHNGSSHOVLDBEENCRYPTEDAWARNNGBELIEVENOTHNG"
)
PLANT_THRESHOLD = 0.90


def java_random(seed: int, n: int, hi: bool = False) -> list[int]:
    """java.util.Random: seed scramble then 48-bit LCG, next(32)."""
    s = (int(seed) ^ JAVA_MULT) & MASK48
    out: list[int] = []
    for _ in range(n):
        s = (s * JAVA_MULT + JAVA_ADD) & MASK48
        val = (s >> 16) & MASK32
        out.append((val >> 27) % Q if hi else val % Q)
    return out


def glibc_type0(seed: int, n: int, hi: bool = False) -> list[int]:
    """ANSI C / glibc TYPE_0 rand: seed = a*seed+c mod 2^31, return bits 30..16."""
    s = int(seed) & 0x7FFFFFFF
    if s == 0:
        s = 1
    out: list[int] = []
    for _ in range(n):
        s = (GLIBC_A * s + GLIBC_C) & 0x7FFFFFFF
        if hi:
            out.append((s >> 26) % Q)
        else:
            out.append(((s >> 16) & 0x7FFF) % Q)
    return out


def splitmix64(seed: int, n: int, hi: bool = False) -> list[int]:
    """SplitMix64 (Steele / Lea / Clinger)."""
    x = int(seed) & MASK64
    if x == 0:
        x = 1
    out: list[int] = []
    for _ in range(n):
        x = (x + SPLITMIX_GAMMA) & MASK64
        z = x
        z = ((z ^ (z >> 30)) * SPLITMIX_M1) & MASK64
        z = ((z ^ (z >> 27)) * SPLITMIX_M2) & MASK64
        z ^= z >> 31
        out.append((z >> 59) % Q if hi else (z % Q))
    return out


def generators() -> list[tuple[str, callable]]:
    return [
        ("java_mod", lambda seed, n: java_random(seed, n, False)),
        ("java_hi", lambda seed, n: java_random(seed, n, True)),
        ("glibc_mod", lambda seed, n: glibc_type0(seed, n, False)),
        ("splitmix64_mod", lambda seed, n: splitmix64(seed, n, False)),
        ("splitmix64_hi", lambda seed, n: splitmix64(seed, n, True)),
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
