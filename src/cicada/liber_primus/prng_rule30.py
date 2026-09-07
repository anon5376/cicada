"""Wolfram Rule 30 elementary CA as a marked-seed keystream.

Automatic sequences (Thue–Morse / paperfold / Fibonacci word / period-doubling
/ Rudin–Shapiro) are closed. Rule 30 evolving a finite 64-bit register is not
an infinite word and was never a keystream here.

Pure functions: no I/O. Output is a list of integers in 0..28.
"""
from __future__ import annotations

Q = 29
MASK64 = (1 << 64) - 1

PLANT_LATIN = (
    "THEPRIMESARESACREDTHETOTIENTFVNCTIANISSACREDALLTHNGSSHOVLDBEENCRYPTEDAWARNNGBELIEVENOTHNG"
)
PLANT_THRESHOLD = 0.90


def _step(s: int) -> int:
    """One Rule-30 step on a 64-bit cyclic register: left XOR (center OR right)."""
    left = ((s << 1) | (s >> 63)) & MASK64
    right = ((s >> 1) | ((s & 1) << 63)) & MASK64
    return (left ^ (s | right)) & MASK64


def rule30(seed: int, n: int, hi: bool = False) -> list[int]:
    s = int(seed) & MASK64
    if s == 0:
        s = 1
    out: list[int] = []
    for _ in range(n):
        s = _step(s)
        out.append((s >> 59) % Q if hi else s % Q)
    return out


def generators() -> list[tuple[str, callable]]:
    return [
        ("rule30_mod", lambda seed, n: rule30(seed, n, False)),
        ("rule30_hi", lambda seed, n: rule30(seed, n, True)),
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
