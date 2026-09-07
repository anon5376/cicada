#!/usr/bin/env python3
"""Previous-word running key: each transcribed word is Vigenere under the prior word's plaintext.

Word-reset vig with a *fixed* attested key is closed. Chaining P_{i-1} as the key
for word i is not. First word decoded by totient / atbash / direct.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from cicada.liber_primus.ciphers import apply_named, totient_prime_stream, vigenere_decrypt  # noqa: E402
from cicada.liber_primus.fixtures import load_fixtures  # noqa: E402
from cicada.liber_primus.gematria import Gematria  # noqa: E402
from cicada.paths import ROOT as CICADA_ROOT  # noqa: E402
from cicada.scoring import score_candidate  # noqa: E402
from exp_skipaware_sha_ctr import keep  # noqa: E402
from exp_word_depth import page_text, words_of  # noqa: E402
from exp_word_local_totient import totient_word  # noqa: E402

GP = Gematria()
Q = 29
OUT = CICADA_ROOT / "experiments" / "EXP-LP-WORD-CHAIN-AK-001"


def first_decode(w: list[int], kind: str) -> list[int]:
    if kind == "direct":
        return list(w)
    if kind == "atbash":
        return [(Q - 1 - x) % Q for x in w]
    if kind == "tot0":
        return totient_word(w, 0)
    raise ValueError(kind)


def chain(words: list[list[int]], first: str) -> list[int]:
    if not words:
        return []
    prev = first_decode(words[0], first)
    out = list(prev)
    for w in words[1:]:
        if not prev:
            prev = first_decode(w, first)
            out.extend(prev)
            continue
        pt = vigenere_decrypt(w, prev)
        out.extend(pt)
        prev = pt
    return out


def vig_enc(pt: list[int], key: list[int]) -> list[int]:
    return [(pt[i] + key[i % len(key)]) % Q for i in range(len(pt))]


def plant() -> dict:
    fx = {f["stage_id"]: f for f in load_fixtures()}
    warn = fx["lp1.warning"]
    pt = apply_named(warn["method"], GP.rune_indices(warn["ciphertext"]), None)
    lens = [len(w) for w in words_of(warn["ciphertext"])]
    pt_words, i = [], 0
    for L in lens:
        pt_words.append(pt[i:i + L])
        i += L
    # encrypt: first word totient-encoded, rest Vigenere under previous PT
    from cicada.liber_primus.gematria import first_n_primes
    enc_w = []
    w0 = pt_words[0]
    pr = first_n_primes(len(w0))
    enc_w.append([(w0[j] + (pr[j] - 1)) % Q for j in range(len(w0))])
    prev = w0
    for w in pt_words[1:]:
        enc_w.append(vig_enc(w, prev))
        prev = w
    rec = chain(enc_w, "tot0")
    agree = sum(a == b for a, b in zip(rec, pt)) / len(pt)
    return {"agree": round(agree, 4), "ok": rec == pt, "n": len(pt)}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    pl = plant()
    print("plant", pl, flush=True)
    if not pl["ok"]:
        (OUT / "result.json").write_text(json.dumps({
            "experiment": "EXP-LP-WORD-CHAIN-AK-001", "plant": pl,
            "verified_new_unsolved_runes": 0, "aborted": "plant failed",
        }, indent=2) + "\n")
        return
    hits, tested, best = [], 0, None
    for s in range(15, 71):
        words = words_of(page_text(s))
        n = sum(len(w) for w in words)
        if n < 80:
            continue
        for first in ("tot0", "atbash", "direct"):
            tested += 1
            pt = chain(words, first)
            lat = GP.latin_stream(pt)
            sc = score_candidate(pt, lat)
            row = {"split": s, "first": first, "head": lat[:80], **sc, "n": n}
            if best is None or sc["trigram_per_100"] > best["trigram_per_100"]:
                best = row
            if keep(sc, n):
                hits.append(row)
                print("KEEP", s, first, sc["trigram_per_100"], lat[:50], flush=True)
    result = {
        "experiment": "EXP-LP-WORD-CHAIN-AK-001",
        "family": "previous-word running key; first word totient/atbash/direct",
        "plant": pl,
        "tested": tested,
        "keep_bar_hits": len(hits),
        "keeps": hits[:12],
        "best": {k: best[k] for k in ("split", "first", "head", "trigram_per_100", "ioc")} if best else None,
        "skeptic_review": {"verdict": "null" if not hits else "keep-bar hits need human read"},
        "verified_new_unsolved_runes": 0,
    }
    (OUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print("tested", tested, "keeps", len(hits), "best", best["trigram_per_100"] if best else None, best["head"][:40] if best else None)


if __name__ == "__main__":
    main()
