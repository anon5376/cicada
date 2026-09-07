"""Plant-and-recover for the shipped KISS/MWC generators.

Drives cicada.liber_primus.prng_kiss and scripts/exp_kiss_mwc.plant_one —
not a copy of the keystream.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from cicada.liber_primus.gematria import Gematria
from cicada.liber_primus.prng_kiss import (
    PLANT_LATIN,
    PLANT_THRESHOLD,
    kiss99,
    mwc16,
    mwc32,
    cmwc_lag3,
    plant_rigid,
)
from exp_kiss_mwc import plant_one


GP = Gematria()


def _pt():
    return GP.encode_latin_key(PLANT_LATIN)


def test_kiss99_rigid_plant_and_wrong_seed():
    pt = _pt()
    r = plant_rigid(lambda s, n: kiss99(s, n, False), 3301, pt)
    assert r["ok"] is True
    assert r["agree"] == 1.0
    assert r["wrong_fails"] is True
    assert r["wrong_agree"] < 0.4


def test_mwc32_cmwc_mwc16_rigid_plant():
    pt = _pt()
    for gen in (
        lambda s, n: mwc32(s, n, False),
        lambda s, n: mwc16(s, n, False),
        lambda s, n: cmwc_lag3(s, n, False),
    ):
        r = plant_rigid(gen, 3301, pt)
        assert r["ok"] is True
        assert r["wrong_fails"] is True


def test_shipped_plant_one_beam_recovers_and_wrong_seed_fails():
    """Experiment entry plant: skip-aware beam on encrypt_reject ciphertext."""
    pt = _pt()
    r = plant_one(lambda s, n: kiss99(s, n, False), 3301, pt)
    assert r["rigid_ok"] is True
    assert r["beam_ok"] is True
    assert r["beam_agree"] >= PLANT_THRESHOLD
    assert r["beam_wrong_fails"] is True
    assert r["ok"] is True


def test_hi_bit_map_is_not_the_mod29_stream():
    a = kiss99(3301, 64, False)
    b = kiss99(3301, 64, True)
    assert a != b
    assert all(0 <= x < 29 for x in a + b)
