"""Plant path for skipped-key-step depth (not CT-crop)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from cicada.liber_primus.skipaware_depth import accept_window, score_keyshift
from exp_depth_kappa import LOGRATIO, Q, UNI
from exp_skipaware_sha_ctr import encrypt_reject


def test_accept_window_is_keystep_not_ct_crop():
    w37 = list(accept_window(37))
    assert w37[0] >= 33 and w37[-1] <= 37
    assert 37 in w37
    # not the PAGESHIFT single crop {37} only, and not all offsets 0..37
    assert w37 != [37]
    assert w37 != list(range(38))
    assert 0 not in w37


def test_true_accept_count_lands_in_window():
    rng = np.random.default_rng(3301)
    n, shift = 120, 37
    p1 = [int(x) for x in rng.integers(0, Q, n)]
    p2 = [int(x) for x in rng.integers(0, Q, n)]
    ks = [int(x) for x in rng.integers(0, Q, (n + shift) * 8)]
    _, used_b = encrypt_reject(p2, ks)
    nB = sum(1 for u in used_b if u < shift)
    assert nB in accept_window(shift)


def test_independent_pad_fails_on_documented_seed():
    """Shipped score_keyshift: independent pads do not beat shuffle (seed 8200)."""
    rng = np.random.default_rng(8200)
    n, shift = 200, 37
    p1 = [int(x) for x in rng.choice(Q, n, p=UNI)]
    p2 = [int(x) for x in rng.choice(Q, n, p=UNI)]
    ks = [int(x) for x in rng.integers(0, Q, (n + shift) * 8 + 16)]
    ks2 = [int(x) for x in rng.integers(0, Q, (n + shift) * 8 + 16)]
    ca, _ = encrypt_reject(p1, ks[shift:])
    cb, _ = encrypt_reject(p2, ks2)
    a, b = np.array(ca), np.array(cb)
    true = score_keyshift(a, b, shift, LOGRATIO)["score"]
    sh = [
        score_keyshift(rng.permutation(a), rng.permutation(b), shift, LOGRATIO)["score"]
        for _ in range(8)
    ]
    assert true <= max(sh)


def test_shared_pad_shift37_beats_shuffle_on_documented_seed():
    """Shipped decoder recovers a reject-filtered shared pad at key-shift 37 (seed 8002)."""
    rng = np.random.default_rng(8002)
    n, shift = 400, 37
    p1 = [int(x) for x in rng.choice(Q, n, p=UNI)]
    p2 = [int(x) for x in rng.choice(Q, n, p=UNI)]
    ks = [int(x) for x in rng.integers(0, Q, (n + shift) * 8 + 16)]
    ca, _ = encrypt_reject(p1, ks[shift:])
    cb, _ = encrypt_reject(p2, ks)
    a, b = np.array(ca), np.array(cb)
    true = score_keyshift(a, b, shift, LOGRATIO)["score"]
    sh = [
        score_keyshift(rng.permutation(a), rng.permutation(b), shift, LOGRATIO)["score"]
        for _ in range(8)
    ]
    assert true > max(sh)
