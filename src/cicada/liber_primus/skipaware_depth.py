"""Skip-aware pair depth that models skipped *key* steps, not CT crops.

encrypt_reject consumes extra keystream symbols that never appear in CT.
A pad shift of S keys therefore is NOT a crop of S ciphertext runes: the
shifted stream emits only the *accepted* keys from that prefix (about
S / 1.03 CT runes). EXP-LP-SKIPAWARE-DEPTH-PAGESHIFT-001 cropped exactly
S CT runes and failed majority-plant at n<=277.

This decoder searches the accept-count nB in a tight window around
S * 29/30, then runs a tight-band match/gap forward HMM on A vs B[nB:].
"""
from __future__ import annotations

import numpy as np

Q = 29
NEG = -1e12
P_MATCH = 0.934
P_GAP = (1.0 - P_MATCH) / 2.0
LOG_M = float(np.log(P_MATCH))
LOG_G = float(np.log(P_GAP))
# keys per accepted CT rune under reject-on-doublet ≈ 1 + 1/29
KEYS_PER_CT = 1.0 + 1.0 / Q


def _lse3(x: float, y: float, z: float) -> float:
    m = x if x > y else y
    if z > m:
        m = z
    return m + float(np.log(np.exp(x - m) + np.exp(y - m) + np.exp(z - m)))


def band_w(n: int, m: int, w_skip: int = 12) -> int:
    return max(w_skip, abs(n - m) + 4)


def forward_score(
    a: np.ndarray,
    b: np.ndarray,
    logratio: np.ndarray,
    w: int | None = None,
    w_skip: int = 12,
) -> float:
    """Match/gap forward log-prob. logratio[d] = log P(depth d) / P(uniform)."""
    n, m = int(len(a)), int(len(b))
    if n < 8 or m < 8:
        return NEG
    if w is None:
        w = band_w(n, m, w_skip)
    prev = np.full(m + 1, NEG)
    prev[0] = 0.0
    for j in range(1, min(m, w) + 1):
        prev[j] = prev[j - 1] + LOG_G
    a = np.asarray(a, np.int64)
    b = np.asarray(b, np.int64)
    lr = np.asarray(logratio, float)
    for i in range(1, n + 1):
        cur = np.full(m + 1, NEG)
        j_lo = max(0, i - w)
        j_hi = min(m, i + w)
        if j_lo == 0:
            cur[0] = prev[0] + LOG_G
        ai = int(a[i - 1])
        for j in range(max(1, j_lo), j_hi + 1):
            em = LOG_M + float(lr[(ai - int(b[j - 1])) % Q])
            cur[j] = _lse3(prev[j - 1] + em, prev[j] + LOG_G, cur[j - 1] + LOG_G)
        prev = cur
    return float(prev[m])


def accept_window(shift: int) -> range:
    """Plausible CT-rune counts produced from `shift` prefix keys.

    Extra consumes are ~1/29, so nB = shift / (1+1/29) ± a few; not a
    ±3σ window over sqrt(shift) (that reintroduces CT-crop look-elsewhere).
    """
    if shift <= 0:
        return range(0, 1)
    mean = shift / KEYS_PER_CT
    lo = max(0, int(round(mean)) - 3)
    hi = min(shift, int(round(mean)) + 3)
    return range(lo, hi + 1)


def score_keyshift(
    a: np.ndarray,
    b: np.ndarray,
    shift: int,
    logratio: np.ndarray,
    w_skip: int = 12,
) -> dict:
    """A starts `shift` keys later than B. Search accept-count, not CT-crop=shift."""
    a = np.asarray(a, np.int64)
    b = np.asarray(b, np.int64)
    if shift <= 0:
        n = min(int(len(a)), int(len(b)))
        s = forward_score(a[:n], b[:n], logratio, w=w_skip)
        return {"score": s, "nB": 0, "shift": 0}
    best = NEG
    best_k = 0
    for nB in accept_window(shift):
        if nB >= len(b) - 8:
            continue
        bb = b[nB:]
        n = min(int(len(a)), int(len(bb)))
        if n < 8:
            continue
        # equalize: length mismatch would inflate the band and cherry-pick
        s = forward_score(a[:n], bb[:n], logratio, w=w_skip)
        if s > best:
            best = s
            best_k = nB
    return {"score": float(best), "nB": int(best_k), "shift": int(shift)}


def viterbi_match_pairs(
    a: np.ndarray,
    b: np.ndarray,
    logratio: np.ndarray,
    w: int = 12,
) -> list[tuple[int, int]]:
    """Viterbi match/gap; return (i, j) CT-index pairs that used the same key."""
    n, m = int(len(a)), int(len(b))
    if n < 8 or m < 8:
        return []
    prev = np.full(m + 1, NEG)
    ptr = np.zeros((n + 1, m + 1), np.int8)  # 1=match 2=gapA 3=gapB
    prev[0] = 0.0
    for j in range(1, min(m, w) + 1):
        prev[j] = prev[j - 1] + LOG_G
        ptr[0, j] = 3
    a = np.asarray(a, np.int64)
    b = np.asarray(b, np.int64)
    lr = np.asarray(logratio, float)
    for i in range(1, n + 1):
        cur = np.full(m + 1, NEG)
        j_lo = max(0, i - w)
        j_hi = min(m, i + w)
        if j_lo == 0:
            cur[0] = prev[0] + LOG_G
            ptr[i, 0] = 2
        ai = int(a[i - 1])
        for j in range(max(1, j_lo), j_hi + 1):
            em = LOG_M + float(lr[(ai - int(b[j - 1])) % Q])
            cand = (prev[j - 1] + em, prev[j] + LOG_G, cur[j - 1] + LOG_G)
            k = int(np.argmax(cand))
            cur[j] = cand[k]
            ptr[i, j] = k + 1
        prev = cur
    i, j = n, m
    pairs: list[tuple[int, int]] = []
    while i > 0 or j > 0:
        mv = int(ptr[i, j])
        if mv == 1 and i and j:
            pairs.append((i - 1, j - 1))
            i -= 1
            j -= 1
        elif mv == 2 and i:
            i -= 1
        elif mv == 3 and j:
            j -= 1
        else:
            if i:
                i -= 1
            elif j:
                j -= 1
            else:
                break
    pairs.reverse()
    return pairs


def matched_difference(
    a: np.ndarray,
    b: np.ndarray,
    logratio: np.ndarray,
    w: int = 12,
) -> np.ndarray:
    """Skip-aware D = C_a[i] - C_b[j] on Viterbi-matched key indices."""
    pairs = viterbi_match_pairs(a, b, logratio, w)
    if not pairs:
        return np.zeros(0, np.int64)
    a = np.asarray(a, np.int64)
    b = np.asarray(b, np.int64)
    return np.array([(int(a[i]) - int(b[j])) % Q for i, j in pairs], np.int64)


def plant_pair(
    pt_a: list[int],
    pt_b: list[int],
    ks: list[int],
    shift: int,
    encrypt_reject,
) -> tuple[np.ndarray, np.ndarray]:
    """Build reject-filtered CT. A uses ks[shift:], B uses ks[0:]."""
    ca, _ = encrypt_reject(pt_a, ks[shift:] if shift else ks)
    cb, used_b = encrypt_reject(pt_b, ks)
    return np.array(ca, np.int64), np.array(cb, np.int64)
