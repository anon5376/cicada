#!/usr/bin/env python3
"""Known-position extra key consumes at transcribed word boundaries.

WORD-SKIP-001 beamed over *unknown* skips and used word-vocab as a score.
This family is the opposite: the `-` marks are observed, so if the cipher
drops 1 (or 2) keystream symbols between words, the decode is unique and
rigid. Word-reset vig (key pointer back to 0) is already closed; this keeps
the stream running and only inserts extra consumes at word ends or starts.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from cicada.liber_primus.ciphers import apply_named  # noqa: E402
from cicada.liber_primus.fixtures import load_fixtures  # noqa: E402
from cicada.liber_primus.gematria import Gematria, first_n_primes  # noqa: E402
from cicada.paths import ROOT as CICADA_ROOT  # noqa: E402
from cicada.scoring import score_candidate  # noqa: E402
from exp_skipaware_sha_ctr import keep, sha256_ctr  # noqa: E402
from exp_word_depth import ends_from_words, idxs_of, page_text, words_of  # noqa: E402

GP = Gematria()
Q = 29
OUT = CICADA_ROOT / "experiments" / "EXP-LP-WORD-END-KEYSKIP-001"
SEEDS = [b"CICADA3301", b"3301", b"DIVINITY", b"AN END", b"LIBERPRIMUS", b"TOTIENT"]


def totient_ks(n: int, start: int = 0) -> list[int]:
    return [(p - 1) % Q for p in first_n_primes(n + start + 8)][start:]


def apply_p(c: int, k: int, rel: str) -> int:
    if rel == "sub":
        return (c - k) % Q
    if rel == "add":
        return (c + k) % Q
    return (k - c) % Q  # beau


def apply_c(p: int, k: int, rel: str) -> int:
    if rel == "sub":
        return (p + k) % Q
    if rel == "add":
        return (p - k) % Q
    return (k - p) % Q


def starts_from_words(ws: list[list[int]], n: int):
    s = np.zeros(n, bool)
    p = 0
    for w in ws:
        if p < n:
            s[p] = True
        p += len(w)
    return s


def decode(ct: list[int], ks: list[int], marks, extra: int, rel: str = "sub",
           phase: str = "after") -> list[int]:
    out, j = [], 0
    for i, c in enumerate(ct):
        if phase == "before" and bool(marks[i]):
            j += extra
        if j >= len(ks):
            break
        out.append(apply_p(c, ks[j], rel))
        j += 1
        if phase == "after" and bool(marks[i]):
            j += extra
    return out


def encode(pt: list[int], ks: list[int], marks, extra: int, rel: str = "sub",
           phase: str = "after") -> list[int]:
    out, j = [], 0
    for i, p in enumerate(pt):
        if phase == "before" and bool(marks[i]):
            j += extra
        out.append(apply_c(p, ks[j], rel))
        j += 1
        if phase == "after" and bool(marks[i]):
            j += extra
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fx = {f["stage_id"]: f for f in load_fixtures()}
    warn = fx["lp1.warning"]
    pt = apply_named(warn["method"], GP.rune_indices(warn["ciphertext"]), None)
    ws = words_of(warn["ciphertext"])
    ends = ends_from_words(ws, len(pt))
    starts = starts_from_words(ws, len(pt))
    ks = sha256_ctr(b"CICADA3301", len(pt) * 4)
    plants = {}
    for extra in (1, 2):
        for rel in ("sub", "add", "beau"):
            for phase, marks in (("after", ends), ("before", starts)):
                ct = encode(pt, ks, marks, extra, rel, phase)
                rec = decode(ct, ks, marks, extra, rel, phase)
                plants[f"{rel}_{phase}_extra{extra}"] = {
                    "agree": round(sum(a == b for a, b in zip(rec, pt)) / len(pt), 4),
                    "ok": rec == pt,
                }
    rec_wrong = decode(encode(pt, ks, ends, 1, "sub", "after"), ks, ends, 0, "sub", "after")
    plants["wrong_extra_breaks"] = rec_wrong != pt
    plants["ok"] = all(v["ok"] for k, v in plants.items() if isinstance(v, dict)) and plants["wrong_extra_breaks"]
    print("plant", plants, flush=True)
    if not plants["ok"]:
        (OUT / "result.json").write_text(json.dumps({
            "experiment": "EXP-LP-WORD-END-KEYSKIP-001", "plant": plants,
            "verified_new_unsolved_runes": 0, "aborted": "plant failed",
        }, indent=2) + "\n")
        return

    streams = [(f"sha:{s.decode()}", lambda n, s=s: sha256_ctr(s, n)) for s in SEEDS]
    streams += [(f"tot{st}", lambda n, st=st: totient_ks(n, st)) for st in (0, 1)]

    hits, tested, best = [], 0, None
    for sidx in range(15, 71):
        ct = idxs_of(sidx)
        if len(ct) < 80:
            continue
        ws = words_of(page_text(sidx))
        ends = ends_from_words(ws, len(ct))
        starts = starts_from_words(ws, len(ct))
        for sname, kfn in streams:
            ks = kfn(len(ct) * 4)
            for extra in (1, 2):
                for rel in ("sub", "add", "beau"):
                    for phase, marks in (("after", ends), ("before", starts)):
                        tested += 1
                        rec = decode(ct, ks, marks, extra, rel, phase)
                        lat = GP.latin_stream(rec)
                        sc = score_candidate(rec, lat)
                        row = {"split": sidx, "stream": sname, "extra": extra, "rel": rel,
                               "phase": phase, "head": lat[:80], **sc, "n": len(rec)}
                        if best is None or sc["trigram_per_100"] > best["trigram_per_100"]:
                            best = row
                        if keep(sc, len(rec)):
                            hits.append(row)
                            print("KEEP", sidx, sname, extra, rel, phase,
                                  sc["trigram_per_100"], lat[:48], flush=True)

    result = {
        "experiment": "EXP-LP-WORD-END-KEYSKIP-001",
        "family": "rigid extra key consumes at transcribed word ends/starts (not a beam)",
        "plant": plants,
        "tested": tested,
        "keep_bar_hits": len(hits),
        "keeps": hits[:15],
        "best": {k: best[k] for k in ("split", "stream", "extra", "rel", "phase", "head", "trigram_per_100", "ioc")} if best else None,
        "skeptic_review": {"verdict": "null" if not hits else "keep-bar needs human English"},
        "verified_new_unsolved_runes": 0,
    }
    (OUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print("tested", tested, "keeps", len(hits),
          "best", None if not best else (best["trigram_per_100"], best["stream"], best["head"][:40]))


if __name__ == "__main__":
    main()
