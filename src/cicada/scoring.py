from __future__ import annotations

# Lightweight structural / language scoring. An English-like score is a ranking
# feature, not cryptographic verification.

from collections import Counter

COMMON = set(
    "THE AND FOR ARE BUT NOT YOU ALL CAN HER WAS ONE OUR OUT DAY GET HAS HIM HIS HOW MAN NEW NOW OLD SEE TWO WAY WHO BOY DID ITS LET PUT SAY SHE TOO USE".split()
)

# Cicada-style Latin often uses V for U and C for K.
COMMON |= {"ONE", "YOV", "CNOW", "BOOC", "THNG", "MVST", "OVR", "THVS"}


def ioc(indices: list[int], q: int = 29) -> float:
    n = len(indices)
    if n < 2:
        return 0.0
    counts = Counter(x % q for x in indices)
    return sum(c * (c - 1) for c in counts.values()) / (n * (n - 1))


def repeat_doublet_rate(indices: list[int]) -> float:
    if len(indices) < 2:
        return 0.0
    d = sum(1 for a, b in zip(indices, indices[1:]) if a == b)
    return d / (len(indices) - 1)


def latin_wordish_score(text: str) -> dict:
    compact = "".join(ch for ch in text.upper() if ch.isalpha())
    # crude: count common 3-grams from English
    grams = ("THE", "AND", "ING", "ENT", "ION", "HER", "FOR", "THA", "NTH", "INT")
    hits = sum(compact.count(g) for g in grams)
    return {
        "length": len(compact),
        "common_trigram_hits": hits,
        "trigram_per_100": (100.0 * hits / len(compact)) if compact else 0.0,
        "vowelish_ratio": (
            sum(compact.count(v) for v in "AEIOUY") / len(compact) if compact else 0.0
        ),
    }


def score_candidate(indices: list[int], latin: str) -> dict:
    return {
        "ioc": ioc(indices),
        "doublet_rate": repeat_doublet_rate(indices),
        **latin_wordish_score(latin),
    }
