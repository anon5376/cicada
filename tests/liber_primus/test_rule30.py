"""Plant-and-recover for the shipped Rule 30 generator."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from cicada.liber_primus.gematria import Gematria
from cicada.liber_primus.prng_rule30 import PLANT_LATIN, PLANT_THRESHOLD, plant_rigid, rule30
from exp_rule30 import plant_one

GP = Gematria()


def _pt():
    return GP.encode_latin_key(PLANT_LATIN)


def test_rule30_not_constant_and_in_alphabet():
    a = rule30(3301, 64, False)
    b = rule30(3301, 64, True)
    c = rule30(1033, 64, False)
    assert a != b and a != c
    assert all(0 <= x < 29 for x in a + b)


def test_rule30_rigid_plant_and_wrong_seed():
    r = plant_rigid(lambda s, n: rule30(s, n, False), 3301, _pt())
    assert r["ok"] is True
    assert r["agree"] == 1.0
    assert r["wrong_fails"] is True


def test_shipped_plant_one_beam_recovers_and_wrong_seed_fails():
    r = plant_one(lambda s, n: rule30(s, n, False), 3301, _pt())
    assert r["rigid_ok"] is True
    assert r["beam_ok"] is True
    assert r["beam_agree"] >= PLANT_THRESHOLD
    assert r["beam_wrong_fails"] is True
    assert r["ok"] is True
