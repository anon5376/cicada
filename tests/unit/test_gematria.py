from cicada.liber_primus.gematria import Gematria, first_n_primes
from cicada.liber_primus.ciphers import atbash, totient_prime_stream, vigenere_decrypt


def test_alphabet_size_and_bijection():
    gp = Gematria()
    assert gp.q == 29
    assert len(gp.by_rune) == 29
    assert set(gp.by_index) == set(range(29))


def test_index_and_prime_are_not_interchangeable():
    gp = Gematria()
    fehu = chr(0x16A0)
    assert gp.rune_index(fehu) == 0
    assert gp.rune_prime(fehu) == 2
    assert gp.rune_index(fehu) != gp.rune_prime(fehu)


def test_divinity_key_encoding():
    gp = Gematria()
    assert gp.encode_latin_key("DIVINITY") == [23, 10, 1, 10, 9, 10, 16, 26]


def test_atbash_involution():
    seq = list(range(29))
    assert atbash(atbash(seq)) == seq


def test_vigenere_roundtrip_without_skips():
    gp = Gematria()
    key = gp.encode_latin_key("DIVINITY")
    pt = [1, 2, 3, 4, 5, 6, 7, 8]
    ct = [(pt[i] + key[i % len(key)]) % 29 for i in range(len(pt))]
    assert vigenere_decrypt(ct, key) == pt


def test_totient_on_synthetic():
    # if ct = (pt + p-1) mod 29, totient stream recovers pt
    primes = first_n_primes(5)
    pt = [3, 1, 4, 1, 5]
    ct = [(pt[i] + (primes[i] - 1)) % 29 for i in range(5)]
    assert totient_prime_stream(ct) == pt


def test_first_primes():
    assert first_n_primes(5) == [2, 3, 5, 7, 11]
