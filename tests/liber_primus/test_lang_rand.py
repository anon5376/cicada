"""Plant-and-recover for shipped Java / glibc / SplitMix64 generators."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from cicada.liber_primus.gematria import Gematria
from cicada.liber_primus.prng_lang_rand import (
    PLANT_LATIN,
    PLANT_THRESHOLD,
    glibc_type0,
    java_random,
    plant_rigid,
    splitmix64,
)
from exp_lang_rand import plant_one


GP = Gematria()


def _pt():
    return GP.encode_latin_key(PLANT_LATIN)


def test_java_seed0_nextint_matches_openjdk():
    # new java.util.Random(0).nextInt() == -1155484576
    from cicada.liber_primus.prng_lang_rand import JAVA_ADD, JAVA_MULT, MASK32, MASK48
    s = (0 ^ JAVA_MULT) & MASK48
    s = (s * JAVA_MULT + JAVA_ADD) & MASK48
    nxt = (s >> 16) & MASK32
    signed = nxt - 2**32 if nxt >= 2**31 else nxt
    assert signed == -1155484576
    assert java_random(0, 1, False)[0] == nxt % 29


def test_java_rigid_plant_and_wrong_seed():
    pt = _pt()
    r = plant_rigid(lambda s, n: java_random(s, n, False), 3301, pt)
    assert r["ok"] is True
    assert r["agree"] == 1.0
    assert r["wrong_fails"] is True


def test_glibc_and_splitmix_rigid_plant():
    pt = _pt()
    for gen in (lambda s, n: glibc_type0(s, n, False), lambda s, n: splitmix64(s, n, False)):
        r = plant_rigid(gen, 3301, pt)
        assert r["ok"] is True
        assert r["wrong_fails"] is True


def test_shipped_plant_one_beam_recovers_and_wrong_seed_fails():
    pt = _pt()
    r = plant_one(lambda s, n: java_random(s, n, False), 3301, pt)
    assert r["rigid_ok"] is True
    assert r["beam_ok"] is True
    assert r["beam_agree"] >= PLANT_THRESHOLD
    assert r["beam_wrong_fails"] is True
    assert r["ok"] is True
