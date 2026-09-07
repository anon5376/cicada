"""xoshiro256** marked-seed keystreams.

xoroshiro64** is closed (EXP-LP-XORSHIFT-PCG-001). xoshiro256** (Blackman /
Vigna, 256-bit state, ** scrambler) was never a keystream here.

Pure functions: no I/O. Output is a list of integers in 0..28.
"""
from __future__ import annotations

Q = 29
MASK64 = (1 << 64) - 1
SPLITMIX_GAMMA = 0x9E3779B97F4A7C15
SPLITMIX_M1 = 0xBF58476D1CE4E5B9
SPLITMIX_M2 = 0x94D049BB133111EB

PLANT_LATIN = (
    "THEPRIMESARESACREDTHETOTIENTFVNCTIANISSACREDALLTHNGSSHOVLDBEENCRYPTEDAWARNNGBELIEVENOTHNG"
)
PLANT_THRESHOLD = 0.90


def _rotl(x: int, k: int) -> int:
    x &= MASK64
    return ((x << k) | (x >> (64 - k))) & MASK64


def _splitmix64_step(x: int) -> tuple[int, int]:
    x = (x + SPLITMIX_GAMMA) & MASK64
    z = x
    z = ((z ^ (z >> 30)) * SPLITMIX_M1) & MASK64
    z = ((z ^ (z >> 27)) * SPLITMIX_M2) & MASK64
    z ^= z >> 31
    return x, z


def _seed4(seed: int) -> list[int]:
    x = int(seed) & MASK64
    if x == 0:
        x = 1
    s = []
    for _ in range(4):
        x, z = _splitmix64_step(x)
        s.append(z or 1)
    return s


def xoshiro256ss(seed: int, n: int, hi: bool = False) -> list[int]:
    """xoshiro256** : result = rotl(s1*5, 7)*9."""
    s0, s1, s2, s3 = _seed4(seed)
    out: list[int] = []
    for _ in range(n):
        result = (_rotl((s1 * 5) & MASK64, 7) * 9) & MASK64
        t = (s1 << 17) & MASK64
        s2 ^= s0
        s3 ^= s1
        s1 ^= s2
        s0 ^= s3
        s2 ^= t
        s3 = _rotl(s3, 45)
        out.append((result >> 59) % Q if hi else result % Q)
    return out


def generators() -> list[tuple[str, callable]]:
    return [
        ("xoshiro256ss_mod", lambda seed, n: xoshiro256ss(seed, n, False)),
        ("xoshiro256ss_hi", lambda seed, n: xoshiro256ss(seed, n, True)),
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
