from __future__ import annotations

from dataclasses import dataclass

# Mapping recovered from Uncovering Cicada Wiki "How the solved pages of the
# Liber Primus were solved", retrieved 2026-09-07. Stored as code points so
# this file cannot be silently corrupted by encoding mishaps.
#
# Source: https://uncovering-cicada.fandom.com/wiki/How_the_solved_pages_of_the_Liber_Primus_were_solved
# Status: STRONGLY SUPPORTED community mapping. Not a signed Cicada artifact.

# rune_cp, primary_latin, index, prime, latin_aliases
_MAPPING_ROWS = [
    (0x16A0, "F", 0, 2, ("F",)),
    (0x16A2, "V", 1, 3, ("V", "U")),
    (0x16A6, "TH", 2, 5, ("TH",)),
    (0x16A9, "O", 3, 7, ("O",)),
    (0x16B1, "R", 4, 11, ("R",)),
    (0x16B3, "C", 5, 13, ("C", "K")),
    (0x16B7, "G", 6, 17, ("G",)),
    (0x16B9, "W", 7, 19, ("W",)),
    (0x16BB, "H", 8, 23, ("H",)),
    (0x16BE, "N", 9, 29, ("N",)),
    (0x16C1, "I", 10, 31, ("I",)),
    (0x16C4, "J", 11, 37, ("J",)),
    (0x16C7, "EO", 12, 41, ("EO",)),
    (0x16C8, "P", 13, 43, ("P",)),
    (0x16C9, "X", 14, 47, ("X",)),
    (0x16CB, "S", 15, 53, ("S", "Z")),
    (0x16CF, "T", 16, 59, ("T",)),
    (0x16D2, "B", 17, 61, ("B",)),
    (0x16D6, "E", 18, 67, ("E",)),
    (0x16D7, "M", 19, 71, ("M",)),
    (0x16DA, "L", 20, 73, ("L",)),
    (0x16DD, "NG", 21, 79, ("NG", "ING")),
    (0x16DF, "OE", 22, 83, ("OE",)),
    (0x16DE, "D", 23, 89, ("D",)),
    (0x16AA, "A", 24, 97, ("A",)),
    (0x16AB, "AE", 25, 101, ("AE",)),
    (0x16A3, "Y", 26, 103, ("Y",)),
    (0x16E1, "IA", 27, 107, ("IA", "IO")),
    (0x16E0, "EA", 28, 109, ("EA",)),
]

MAPPING_V1 = tuple(
    (chr(cp), latin, idx, prime, aliases)
    for cp, latin, idx, prime, aliases in _MAPPING_ROWS
)

WORD_SEPARATORS = set("•-–—")
SOFT_BREAKS = set("/\n")
LAYOUT_MARKS = set("%&$")
PUNCT = set(".,;:\"'?!")

_MULTI = ("ING", "TH", "NG", "EO", "OE", "AE", "IA", "IO", "EA")
_MULTI_TO_LATIN = {
    "ING": "NG",
    "TH": "TH",
    "NG": "NG",
    "EO": "EO",
    "OE": "OE",
    "AE": "AE",
    "IA": "IA",
    "IO": "IA",
    "EA": "EA",
}
_SINGLE_ALIAS = {"U": "V", "K": "C", "Z": "S"}


@dataclass(frozen=True)
class Token:
    kind: str
    raw: str
    index: int | None = None
    prime: int | None = None
    latin: str | None = None


class Gematria:
    version = "mapping-v1-wiki-2026-09-07"

    def __init__(self, table=MAPPING_V1):
        self.table = table
        self.q = len(table)
        if self.q != 29:
            raise ValueError(f"expected 29-rune alphabet, got {self.q}")
        self.by_rune = {row[0]: row for row in table}
        self.by_index = {row[2]: row for row in table}
        self.by_primary_latin = {row[1]: row for row in table}
        if len(self.by_index) != 29 or len(self.by_rune) != 29:
            raise ValueError("mapping is not a bijection over 29 runes/indices")

    def rune_index(self, rune: str) -> int:
        return self.by_rune[rune][2]

    def rune_prime(self, rune: str) -> int:
        return self.by_rune[rune][3]

    def latin_of_index(self, index: int) -> str:
        return self.by_index[index % self.q][1]

    def rune_of_index(self, index: int) -> str:
        return self.by_index[index % self.q][0]

    def tokenize(self, text: str) -> list[Token]:
        tokens: list[Token] = []
        i = 0
        while i < len(text):
            ch = text[i]
            if ch in self.by_rune:
                row = self.by_rune[ch]
                tokens.append(Token("rune", ch, row[2], row[3], row[1]))
                i += 1
            elif ch in WORD_SEPARATORS:
                tokens.append(Token("sep", ch))
                i += 1
            elif ch in SOFT_BREAKS:
                tokens.append(Token("break", ch))
                i += 1
            elif ch in LAYOUT_MARKS:
                tokens.append(Token("layout", ch))
                i += 1
            elif ch in PUNCT:
                tokens.append(Token("punct", ch))
                i += 1
            elif ch.isdigit():
                j = i
                while j < len(text) and text[j].isdigit():
                    j += 1
                tokens.append(Token("number", text[i:j]))
                i = j
            elif ch.isspace():
                i += 1
            else:
                tokens.append(Token("other", ch))
                i += 1
        return tokens

    def rune_indices(self, text: str) -> list[int]:
        return [t.index for t in self.tokenize(text) if t.kind == "rune" and t.index is not None]

    def latin_stream(self, indices: list[int]) -> str:
        return "".join(self.latin_of_index(i) for i in indices)

    def encode_latin_key(self, text: str) -> list[int]:
        s = text.upper()
        out: list[int] = []
        i = 0
        while i < len(s):
            if not s[i].isalpha():
                i += 1
                continue
            matched = False
            for m in _MULTI:
                if s.startswith(m, i):
                    latin = _MULTI_TO_LATIN[m]
                    out.append(self.by_primary_latin[latin][2])
                    i += len(m)
                    matched = True
                    break
            if matched:
                continue
            ch = _SINGLE_ALIAS.get(s[i], s[i])
            if ch not in self.by_primary_latin:
                raise ValueError(f"cannot encode key letter {s[i]!r}")
            out.append(self.by_primary_latin[ch][2])
            i += 1
        return out


def first_n_primes(n: int) -> list[int]:
    primes: list[int] = []
    cand = 2
    while len(primes) < n:
        if all(cand % p for p in primes if p * p <= cand):
            primes.append(cand)
        cand += 1
    return primes
