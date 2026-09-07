"""Plant-and-recover for the shipped Salsa20/20 + SHAKE256 generators."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from cicada.liber_primus.gematria import Gematria
from cicada.liber_primus.prng_salsa_shake import (
    PLANT_LATIN,
    PLANT_THRESHOLD,
    SALSA20_TV_BLOCK0,
    SALSA20_TV_IV,
    SALSA20_TV_KEY,
    plant_rigid,
    salsa20_block,
    salsa20_mod,
    shake256_mod_int,
)
from exp_salsa20_shake import plant_one


GP = Gematria()


def _pt():
    return GP.encode_latin_key(PLANT_LATIN)


def test_salsa20_known_answer_block0():
    assert salsa20_block(SALSA20_TV_KEY, SALSA20_TV_IV, 0) == SALSA20_TV_BLOCK0


def test_salsa20_rigid_plant_and_wrong_seed():
    pt = _pt()
    r = plant_rigid(lambda s, n: salsa20_mod(s, n, False), 3301, pt)
    assert r["ok"] is True
    assert r["agree"] == 1.0
    assert r["wrong_fails"] is True
    assert r["wrong_agree"] < 0.4


def test_shake256_rigid_plant():
    pt = _pt()
    r = plant_rigid(lambda s, n: shake256_mod_int(s, n, False), 3301, pt)
    assert r["ok"] is True
    assert r["wrong_fails"] is True


def test_shipped_plant_one_beam_recovers_and_wrong_seed_fails():
    pt = _pt()
    r = plant_one(lambda s, n: salsa20_mod(s, n, False), 3301, pt)
    assert r["rigid_ok"] is True
    assert r["beam_ok"] is True
    assert r["beam_agree"] >= PLANT_THRESHOLD
    assert r["beam_wrong_fails"] is True
    assert r["ok"] is True


def test_hi_bit_map_is_not_the_mod29_stream():
    a = salsa20_mod(3301, 64, False)
    b = salsa20_mod(3301, 64, True)
    assert a != b
    assert all(0 <= x < 29 for x in a + b)
