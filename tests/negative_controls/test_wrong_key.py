from cicada.liber_primus.ciphers import vigenere_decrypt
from cicada.liber_primus.gematria import Gematria
from cicada.scoring import latin_wordish_score


def test_wrong_key_is_not_english_like():
    """A wrong key must not score as English-like under the ranking feature.

    The plaintext must contain at least one of the ten trigrams the scorer
    actually tracks, otherwise the control compares 0.0 against 0.0 and asserts
    nothing.  The previous fixture, WELCOMEPILGRIM, contains none of them.
    THEPRIMESARESACRED is real lp1.wisdom plaintext and does.
    """
    gp = Gematria()
    key_right = gp.encode_latin_key("DIVINITY")
    key_wrong = gp.encode_latin_key("AAAAAAAA")
    pt = gp.encode_latin_key("THEPRIMESARESACRED")
    ct = [(pt[i] + key_right[i % len(key_right)]) % 29 for i in range(len(pt))]
    good = gp.latin_stream(vigenere_decrypt(ct, key_right))
    bad = gp.latin_stream(vigenere_decrypt(ct, key_wrong))
    assert good == "THEPRIMESARESACRED"
    assert latin_wordish_score(good)["common_trigram_hits"] > 0
    assert latin_wordish_score(bad)["common_trigram_hits"] == 0
    assert latin_wordish_score(good)["trigram_per_100"] > latin_wordish_score(bad)["trigram_per_100"]


def test_trigram_scorer_is_inflated_by_multigraph_runes():
    """Documents a KNOWN limitation of the keep bar, so it cannot be forgotten.

    TH, NG, EO, AE, IA and EA each expand to two Latin letters, so a rune stream
    that is not English at all manufactures THE/ING hits at the expansion joins.
    This is the "TH-salad" artifact behind the split066 and Faust/Inferno
    keep-bar hits recorded in NEGATIVE_RESULTS.md.

    trigram_per_100 is therefore a ranking feature only.  It is not evidence of
    a decryption, and a candidate that clears it still has to clear IoC and a
    calibrated surrogate comparison.
    """
    gp = Gematria()
    th, e, n, g = 2, 18, 9, 6
    salad = [th, e] * 12          # THETHETHE...
    latin = gp.latin_stream(salad)
    score = latin_wordish_score(latin)
    assert latin.startswith("THETHE")
    # 24 runes -> 36 Latin characters -> 12 "THE" hits, a rate no English text reaches
    assert score["trigram_per_100"] > 30.0

    salad2 = gp.latin_stream([n, g] * 12)   # NGNGNG..., no ING join
    assert latin_wordish_score(salad2)["common_trigram_hits"] == 0
