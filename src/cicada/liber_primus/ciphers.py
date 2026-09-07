from __future__ import annotations

from dataclasses import dataclass

from .gematria import Gematria, first_n_primes

GP = Gematria()
Q = GP.q


@dataclass(frozen=True)
class TransformSpec:
    plugin_id: str
    version: str
    input_type: str
    output_type: str
    determinism: str
    side_effects: str
    notes: str


ATBASH_SPEC = TransformSpec(
    plugin_id="lp.atbash",
    version="1",
    input_type="RuneIndexSequence",
    output_type="RuneIndexSequence",
    determinism="deterministic",
    side_effects="none",
    notes="index' = (q-1) - index; q observed 29",
)

VIGENERE_SPEC = TransformSpec(
    plugin_id="lp.vigenere_sub",
    version="1",
    input_type="RuneIndexSequence",
    output_type="RuneIndexSequence",
    determinism="deterministic",
    side_effects="none",
    notes="pt[i] = (ct[i] - key[i]) mod q; optional skip of plaintext F after seeing output",
)

TOTIENT_SPEC = TransformSpec(
    plugin_id="lp.totient_prime_stream",
    version="1",
    input_type="RuneIndexSequence",
    output_type="RuneIndexSequence",
    determinism="deterministic",
    side_effects="none",
    notes="pt[i] = (ct[i] - (prime[i]-1)) mod q; 0-based prime stream starting at 2",
)


def atbash(indices: list[int], q: int = Q) -> list[int]:
    return [(q - 1) - (x % q) for x in indices]


def caesar(indices: list[int], shift: int, q: int = Q) -> list[int]:
    return [(x + shift) % q for x in indices]


def add_stream(indices: list[int], key: list[int], q: int = Q) -> list[int]:
    if not key:
        raise ValueError("empty key")
    return [(indices[i] + key[i % len(key)]) % q for i in range(len(indices))]


def vigenere_decrypt(
    indices: list[int],
    key: list[int],
    q: int = Q,
    skip_plaintext_f: bool = False,
    skip_ciphertext_f: bool = False,
) -> list[int]:
    if not key:
        raise ValueError("empty key")
    out: list[int] = []
    k = 0
    for x in indices:
        if skip_ciphertext_f and x % q == 0:
            out.append(x % q)
            continue
        pt = (x - key[k % len(key)]) % q
        out.append(pt)
        if skip_plaintext_f and pt == 0:
            continue
        k += 1
    return out


def totient_prime_stream(indices: list[int], q: int = Q, start: int = 0) -> list[int]:
    primes = first_n_primes(len(indices) + start)
    return [(indices[i] - (primes[i + start] - 1)) % q for i in range(len(indices))]


def totient_skip_ciphertext_f_ordinal(
    indices: list[int],
    ordinal: int,
    q: int = Q,
    start: int = 0,
) -> list[int]:
    """Totient stream, leaving the Nth ciphertext F (1-based) unshifted.

    Page 56 uses ordinal=4 (0-based rune index 56): the fourth F is plaintext
    and does not consume a prime. Other F runes are ordinary ciphertext.
    """
    if ordinal < 1:
        raise ValueError("ordinal is 1-based")
    primes = first_n_primes(len(indices) + start + 2)
    out: list[int] = []
    k = start
    seen = 0
    for x in indices:
        x = x % q
        if x == 0:
            seen += 1
            if seen == ordinal:
                out.append(0)
                continue
        out.append((x - (primes[k] - 1)) % q)
        k += 1
    return out


def direct_latin(indices: list[int], gp: Gematria | None = None) -> str:
    gp = gp or GP
    return gp.latin_stream(indices)


def apply_named(name: str, indices: list[int], key: list[int] | None = None) -> list[int]:
    if name == "direct":
        return list(indices)
    if name == "atbash":
        return atbash(indices)
    if name == "atbash_plus_3":
        return caesar(atbash(indices), 3)
    if name == "totient_prime":
        return totient_prime_stream(indices)
    if name == "totient_prime_skip_4th_ct_f":
        return totient_skip_ciphertext_f_ordinal(indices, 4)
    if name == "vigenere":
        if key is None:
            raise ValueError("vigenere requires key")
        return vigenere_decrypt(indices, key)
    if name == "vigenere_skip_pt_f":
        if key is None:
            raise ValueError("vigenere requires key")
        return vigenere_decrypt(indices, key, skip_plaintext_f=True)
    raise ValueError(f"unknown transform {name}")
