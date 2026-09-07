#!/usr/bin/env python3
"""05.jpg trailer as skip-aware pad/seed; word prime-sum self-key (words or their numbers)."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from cicada.liber_primus.gematria import Gematria  # noqa: E402
from cicada.paths import ROOT as CICADA_ROOT  # noqa: E402
from cicada.scoring import score_candidate  # noqa: E402
from exp_skipaware_sha_ctr import beam_decode, keep, sha256_ctr  # noqa: E402

GP = Gematria()
Q = 29
PAGE_DIR = CICADA_ROOT / "corpus/normalized/rtkd_pages"
CAS = CICADA_ROOT / "corpus/objects/sha256"
OUT = CICADA_ROOT / "experiments" / "EXP-LP-TRAILER-WORDSUM-001"


def idxs_of(s: int) -> list[int]:
    return GP.rune_indices((PAGE_DIR / f"split_{s:03d}.txt").read_text(encoding="utf-8"))


def page_words(s: int) -> list[list[int]]:
    text = (PAGE_DIR / f"split_{s:03d}.txt").read_text(encoding="utf-8")
    words: list[list[int]] = []
    cur: list[int] = []
    primes: list[list[int]] = []
    curp: list[int] = []
    for tok in GP.tokenize(text):
        if tok.kind == "rune" and tok.index is not None:
            cur.append(tok.index)
            curp.append(tok.prime if tok.prime is not None else 0)
        elif tok.kind in {"sep", "punct", "layout"} and cur:
            words.append(cur)
            primes.append(curp)
            cur, curp = [], []
    if cur:
        words.append(cur)
        primes.append(curp)
    return words, primes


def prefix(n: int = 400) -> list[int]:
    out: list[int] = []
    for s in range(15, 71):
        out.extend(idxs_of(s))
        if len(out) >= n:
            break
    return out[:n]


def wordsum_dec(words: list[list[int]], primes: list[list[int]], mode: str) -> list[int]:
    out: list[int] = []
    prev_sum = 0
    for i, (w, pr) in enumerate(zip(words, primes)):
        s = sum(pr)
        if mode == "ct_prev_caesar":
            sh = prev_sum % Q
            out.extend((x - sh) % Q for x in w)
            prev_sum = s
        elif mode == "ct_prev_totientish":
            sh = (prev_sum - 1) % Q if prev_sum else 0
            out.extend((x - sh) % Q for x in w)
            prev_sum = s
        elif mode == "self_caesar":
            sh = s % Q
            out.extend((x - sh) % Q for x in w)
        elif mode == "first_direct_then_prev":
            if i == 0:
                out.extend(w)
            else:
                out.extend((x - (prev_sum % Q)) % Q for x in w)
            prev_sum = s
        else:
            raise ValueError(mode)
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    hits = []
    tested = 0
    trailer = (CAS / "3e" / "3e95593e226980e3bf743ce9d12f38cf41b96dc7797587f9ff7470788719803f").read_bytes()
    print("trailer", len(trailer), "sha", hashlib.sha256(trailer).hexdigest()[:16], flush=True)

    p400 = prefix(400)
    p15 = idxs_of(15)
    seeds = [
        ("trailer_sha", hashlib.sha256(trailer).digest()),
        ("trailer_head32", trailer[:32]),
        ("trailer_hex", hashlib.sha256(trailer).hexdigest().encode()),
    ]
    for label, seed in seeds:
        for span, ct in (("prefix400", p400), ("split015", p15)):
            tested += 1
            pt = beam_decode(ct, sha256_ctr(seed, len(ct) * 4))
            lat = GP.latin_stream(pt)
            sc = score_candidate(pt, lat)
            print(f"beam {span} {label} tri={sc['trigram_per_100']:.2f} ioc={sc['ioc']:.3f} {lat[:40]}", flush=True)
            if keep(sc, len(pt)):
                hits.append({"kind": "trailer_seed", "seed": label, "span": span, "head": lat[:80], **sc})

    # raw trailer as keystream through the beam (if it is the pad)
    ks = [b % Q for b in trailer]
    for span, ct in (("prefix400", p400), ("split015", p15)):
        tested += 1
        pt = beam_decode(ct, ks)
        lat = GP.latin_stream(pt)
        sc = score_candidate(pt, lat)
        print(f"beam {span} trailer_raw tri={sc['trigram_per_100']:.2f} ioc={sc['ioc']:.3f} {lat[:40]}", flush=True)
        if keep(sc, len(pt)):
            hits.append({"kind": "trailer_raw", "span": span, "head": lat[:80], **sc})

    modes = ("ct_prev_caesar", "ct_prev_totientish", "self_caesar", "first_direct_then_prev")
    for s in range(15, 71):
        words, primes = page_words(s)
        n = sum(len(w) for w in words)
        if n < 80:
            continue
        for mode in modes:
            tested += 1
            pt = wordsum_dec(words, primes, mode)
            lat = GP.latin_stream(pt)
            sc = score_candidate(pt, lat)
            if s == 15 and mode == "ct_prev_caesar":
                print(f"wsum split015 {mode} tri={sc['trigram_per_100']:.2f} ioc={sc['ioc']:.3f} {lat[:40]}", flush=True)
            if keep(sc, len(pt)):
                hits.append({"kind": "wordsum", "split": s, "mode": mode, "head": lat[:80], **sc})
                print("KEEP", s, mode, lat[:48], flush=True)

    print("tested", tested, "keeps", len(hits), flush=True)
    (OUT / "result.json").write_text(
        json.dumps({"tested": tested, "keeps": hits, "trailer_n": len(trailer)}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
