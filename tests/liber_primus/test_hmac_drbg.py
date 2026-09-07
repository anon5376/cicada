"""Plant-and-recover for the shipped HMAC-DRBG generator."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from cicada.liber_primus.gematria import Gematria
from cicada.liber_primus.prng_hmac_drbg import (
    PLANT_LATIN,
    PLANT_THRESHOLD,
    hmac_drbg_int,
    plant_rigid,
)
from exp_hmac_drbg import plant_one

GP = Gematria()


def _pt():
    return GP.encode_latin_key(PLANT_LATIN)


def test_hmac_drbg_not_constant():
    a = hmac_drbg_int(3301, 64, False)
    b = hmac_drbg_int(3301, 64, True)
    c = hmac_drbg_int(1033, 64, False)
    assert a != b and a != c
    assert all(0 <= x < 29 for x in a + b)


def test_hmac_drbg_rigid_plant_and_wrong_seed():
    r = plant_rigid(lambda s, n: hmac_drbg_int(s, n, False), 3301, _pt())
    assert r["ok"] is True
    assert r["agree"] == 1.0
    assert r["wrong_fails"] is True


def test_shipped_plant_one_beam_recovers_and_wrong_seed_fails():
    r = plant_one(lambda s, n: hmac_drbg_int(s, n, False), 3301, _pt())
    assert r["rigid_ok"] is True
    assert r["beam_ok"] is True
    assert r["beam_agree"] >= PLANT_THRESHOLD
    assert r["beam_wrong_fails"] is True
    assert r["ok"] is True
