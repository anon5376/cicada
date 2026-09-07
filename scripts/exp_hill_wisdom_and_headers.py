#!/usr/bin/env python3
"""Hill using the solved wisdom-page number square, 15.jpg C-grid as 4x4,
and simple attacks on the rune headers around pp49-51.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cicada.liber_primus.ciphers import (  # noqa: E402
    apply_named,
    atbash,
    caesar,
    totient_prime_stream,
    totient_skip_ciphertext_f_ordinal,
)
from cicada.liber_primus.gematria import Gematria  # noqa: E402
from cicada.experiments import KNOWN_KEYS  # noqa: E402
from cicada.paths import ROOT as CICADA_ROOT  # noqa: E402
from cicada.scoring import score_candidate  # noqa: E402

GP = Gematria()
Q = 29
PAGE_DIR = CICADA_ROOT / "corpus/normalized/rtkd_pages"
OUT = CICADA_ROOT / "experiments" / "EXP-LP-HILL-WISDOM-001"

# LP1 wisdom page number square (community layout)
WISDOM = [
    [272, 138, 341, 131, 151],
    [366, 199, 130, 320, 18],
    [226, 245, 91, 245, 226],
    [18, 320, 130, 199, 366],
    [151, 131, 341, 138, 272],
]
C15 = [
    [3258, 3222, 3152, 3038],
    [3278, 3299, 3298, 2838],
    [3288, 3294, 3296, 2472],
    [4516, 1206, 708, 1820],
]


def mod_inv(a: int) -> int | None:
    a %= Q
    if a == 0:
        return None
    return pow(a, Q - 2, Q)


def mat_mod(M: list[list[int]]) -> list[list[int]]:
    return [[x % Q for x in row] for row in M]


def det(M: list[list[int]]) -> int:
    n = len(M)
    if n == 1:
        return M[0][0] % Q
    if n == 2:
        return (M[0][0] * M[1][1] - M[0][1] * M[1][0]) % Q
    s = 0
    for j in range(n):
        minor = [row[:j] + row[j + 1 :] for row in M[1:]]
        s += ((-1) ** j) * M[0][j] * det(minor)
    return s % Q


def invert(M: list[list[int]]) -> list[list[int]] | None:
    n = len(M)
    d = det(M)
    di = mod_inv(d)
    if di is None:
        return None
    if n == 2:
        return [
            [(M[1][1] * di) % Q, ((-M[0][1]) * di) % Q],
            [((-M[1][0]) * di) % Q, (M[0][0] * di) % Q],
        ]
    # adjugate
    inv = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            minor = [row[:j] + row[j + 1 :] for k, row in enumerate(M) if k != i]
            inv[j][i] = (((-1) ** (i + j)) * det(minor) * di) % Q
    return inv


def hill_apply(ct: list[int], K: list[list[int]]) -> list[int]:
    n = len(K)
    out = []
    for i in range(0, len(ct) - n + 1, n):
        vec = ct[i : i + n]
        for r in range(n):
            out.append(sum(K[r][c] * vec[c] for c in range(n)) % Q)
    return out


def idxs_of(s: int) -> list[int]:
    return GP.rune_indices((PAGE_DIR / f"split_{s:03d}.txt").read_text(encoding="utf-8"))


def keep(sc: dict, n: int) -> bool:
    return n >= 40 and sc["trigram_per_100"] >= 3.5 and 0.28 <= sc["vowelish_ratio"] <= 0.55 and sc["ioc"] >= 0.045


def header_attacks() -> list[dict]:
    # runes before & on split 64; after & on split 66
    t64 = (PAGE_DIR / "split_064.txt").read_text(encoding="utf-8")
    t66 = (PAGE_DIR / "split_066.txt").read_text(encoding="utf-8")
    pre = GP.rune_indices(t64.split("&")[0])
    post = GP.rune_indices(t66.split("&", 1)[-1])
    rows = []
    methods = [
        ("direct", lambda x: x),
        ("atbash", atbash),
        ("atb3", lambda x: caesar(atbash(x), 3)),
        ("tot", totient_prime_stream),
        ("tot4", lambda x: totient_skip_ciphertext_f_ordinal(x, 4)),
    ]
    for kn, key in KNOWN_KEYS.items():
        methods.append((f"vig_{kn}", lambda x, k=key: apply_named("vigenere", x, k)))
        methods.append((f"vigF_{kn}", lambda x, k=key: apply_named("vigenere_skip_pt_f", x, k)))
    for label, ix in (("p49_pre", pre), ("p51_post", post)):
        for s in range(29):
            methods.append((f"{label}_c{s}", None))
        print(label, "n", len(ix), GP.latin_stream(ix)[:80])
        for name, fn in methods:
            if fn is None:
                continue
            out = fn(ix)
            latin = GP.latin_stream(out)
            sc = score_candidate(out, latin)
            rec = {"where": label, "method": name, "latin": latin, **sc}
            if sc["trigram_per_100"] >= 4 or latin.startswith(("ANEND", "ANINSTRUCTION", "KNOWTHIS", "WELCOME")):
                rows.append(rec)
                print(" H", label, name, latin[:70])
        for s in range(29):
            for name, seq in ((f"c{s}", caesar(ix, s)), (f"ac{s}", caesar(atbash(ix), s))):
                latin = GP.latin_stream(seq)
                if any(w in latin for w in ("ANEND", "INSTRUCTION", "KNOWTHIS", "WELCOME", "THELOSS", "PAYLOAD", "NUMBERS")):
                    rows.append({"where": label, "method": name, "latin": latin})
                    print(" H", label, name, latin[:70])
    return rows


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    headers = header_attacks()

    mats = {
        "wisdom5": mat_mod(WISDOM),
        "wisdom5T": [list(r) for r in zip(*mat_mod(WISDOM))],
        "c15_4": mat_mod(C15),
        "c15_4T": [list(r) for r in zip(*mat_mod(C15))],
        "wisdom_ul3": mat_mod([row[:3] for row in WISDOM[:3]]),
        "wisdom_br3": mat_mod([row[2:] for row in WISDOM[2:]]),
    }
    invs = {}
    for name, M in mats.items():
        inv = invert(M)
        print(f"mat {name} det={det(M)} invertible={inv is not None}")
        if inv:
            invs[name + "_inv"] = inv
            invs[name] = M  # also try as encrypt-direction

    concat = []
    for s in range(15, 71):
        concat.extend(idxs_of(s))

    hits = []
    tested = 0
    targets = {"concat800": concat[:800]}
    for s in (15, 16, 23, 27, 40, 53, 54, 64, 66, 68):
        targets[f"split{s:03d}"] = idxs_of(s)

    for tname, ct in targets.items():
        for kname, K in invs.items():
            tested += 1
            out = hill_apply(ct, K)
            if len(out) < 20:
                continue
            latin = GP.latin_stream(out)
            sc = score_candidate(out, latin)
            if keep(sc, len(out)) or sc["trigram_per_100"] >= 4:
                hits.append({"target": tname, "K": kname, "head": latin[:90], **sc})
                print("KEEP", tname, kname, sc["trigram_per_100"], latin[:70])

    summary = {
        "tested": tested,
        "hits": hits,
        "header_hits": headers,
        "overlay_note": "glyph overlay failed page 56/57 controls; not used as heading truth",
    }
    (OUT / "result.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print("hill tested", tested, "keeps", len(hits), "header_hits", len(headers))


if __name__ == "__main__":
    main()
