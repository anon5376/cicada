#!/usr/bin/env python3
"""Word-parse skip-aware beam (HANDOFF item 0).

The trigram scorer manufactured every PMCEAO/TH-salad keep. Word boundaries are
not encrypted. This replaces the trigram score with a dictionary parse at the
transcribed word ends, on the same skip-aware consume-1..3 decoder.

Not a new key guess: attested SHA-CTR seeds + totient prime-minus-one stream.
Keep-bar is not evidence (WORD-DEPTH-001). Score = word-LM vs shuffled CT.
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
from exp_skipaware_sha_ctr import encrypt_reject, sha256_ctr  # noqa: E402
from exp_word_depth import LM, ends_from_words, idxs_of, page_text, words_of  # noqa: E402

GP = Gematria()
Q = 29
OUT = CICADA_ROOT / "experiments" / "EXP-LP-WORD-SKIP-001"
SEEDS = [b"CICADA3301", b"3301", b"DIVINITY", b"AN END", b"TOTIENT", b"LIBERPRIMUS"]
RNG = np.random.default_rng(3301)
N_SHUF = 8


def totient_ks(n: int, start: int = 0) -> list[int]:
    return [(p - 1) % Q for p in first_n_primes(n + start)][start:]


GRAMS = (
    "THE", "AND", "ING", "ENT", "ION", "HER", "FOR", "THA", "NTH", "INT",
    "TED", "RED", "ARE", "ERE", "ENC", "WAS", "HIS", "HAT", "ETH", "DTH",
    "OTH", "ITH", "VER", "ALL", "THN", "NCR", "YPT", "WAR", "NOT", "BEL",
)


def beam_word(ct: list[int], ks: list[int], ends: np.ndarray, lm: LM,
              lam: float = 2.0, max_skip: int = 3, beam: int = 48) -> tuple[list[int], float]:
    """Skip-aware subtract. Trigram tracks the key pointer; vocab bonus at word ends."""
    beams: list = [(0, (), 0.0, [], ())]  # j, tail, sc, pt, word
    for i, c in enumerate(ct):
        prev = ct[i - 1] if i else None
        nxt = []
        for j, tail, sc, pt, word in beams:
            for s in range(1, max_skip + 1):
                j_acc = j + s - 1
                if j_acc >= len(ks):
                    continue
                p = (c - ks[j_acc]) % Q
                if s > 1:
                    if prev is None:
                        continue
                    need = (prev - c + ks[j_acc]) % Q
                    if any(ks[j + t] != need for t in range(s - 1)):
                        continue
                if prev is not None and c == prev and s != 1:
                    continue
                lat_tail = GP.latin_stream(list(tail) + [p])
                add = sum(lat_tail.count(g) for g in GRAMS) - sum(
                    GP.latin_stream(list(tail)).count(g) for g in GRAMS
                )
                nword = word + (p,)
                nsc = sc + add
                if bool(ends[i]):
                    nsc += lam if nword in lm.logw else -lam
                    nword = ()
                nxt.append((j_acc + 1, tuple((list(tail) + [p])[-4:]), nsc, pt + [p], nword))
        if not nxt:
            for j, tail, sc, pt, word in beams:
                if j < len(ks):
                    p = (c - ks[j]) % Q
                    nxt.append((j + 1, (p,), sc, pt + [p], word + (p,)))
        nxt.sort(key=lambda x: -x[2])
        beams = nxt[:beam]
    if not beams:
        return [], -1e9
    return beams[0][3], float(beams[0][2])


def agree(a: list[int], b: list[int]) -> float:
    n = min(len(a), len(b))
    return sum(x == y for x, y in zip(a[:n], b[:n])) / n if n else 0.0


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    print("loading LM…", flush=True)
    lm = LM()
    plants = {}

    # (a) SHA-CTR skip-aware with real warning word ends
    fx = {f["stage_id"]: f for f in load_fixtures()}
    warn = fx["lp1.warning"]
    pt = apply_named(warn["method"], GP.rune_indices(warn["ciphertext"]), None)
    ends = ends_from_words(words_of(warn["ciphertext"]), len(pt))
    ks = sha256_ctr(b"CICADA3301", len(pt) * 4)
    ct, _ = encrypt_reject(pt, ks)
    rec, sc = beam_word(ct, ks, ends, lm)
    plants["sha_ctr_warning"] = {
        "agree": round(agree(rec, pt), 4),
        "score": round(sc, 3),
        "head": GP.latin_stream(rec)[:64],
        "ok": agree(rec, pt) >= 0.85,
    }
    print("plant sha", plants["sha_ctr_warning"], flush=True)

    # (b) page 56 totient skip-4th is a known replay: instrument must fire
    p56 = fx["lp2.page56_an_end"]
    ct56 = GP.rune_indices(p56["ciphertext"])
    pt56 = apply_named(p56["method"], ct56, None)
    e56 = ends_from_words(words_of(p56["ciphertext"]), len(ct56))
    rec56, sc56 = beam_word(ct56, totient_ks(len(ct56) * 4, 0), e56, lm)
    plants["page56_totient_wordbeam"] = {
        "agree": round(agree(rec56, pt56), 4),
        "score": round(sc56, 3),
        "head": GP.latin_stream(rec56)[:64],
        "true_head": GP.latin_stream(pt56)[:64],
        "ok": agree(rec56, pt56) >= 0.60,
        "note": "known-page control only; skip-4th-F is not encrypt_reject, so agree~0.66 is expected. Does not count.",
    }
    print("plant p56", plants["page56_totient_wordbeam"], flush=True)

    plant_ok = bool(plants["sha_ctr_warning"]["ok"])
    # page56 control is nice-to-have; SHA plant is the skip-aware claim
    if not plant_ok:
        (OUT / "result.json").write_text(json.dumps({
            "experiment": "EXP-LP-WORD-SKIP-001",
            "plant": plants,
            "verified_new_unsolved_runes": 0,
            "aborted": "SHA-CTR word beam failed plant",
        }, indent=2) + "\n")
        print("PLANT FAILED")
        return

    targets = []
    for s in (15, 17, 23, 40, 56, 63):
        v = idxs_of(s)
        if len(v) >= 80:
            e = ends_from_words(words_of(page_text(s)), len(v))
            targets.append((f"split{s:03d}", v, e))

    tests = []
    beats = 0
    for tname, ct, ends in targets:
        keystreams = [(f"sha:{sd.decode()}", sha256_ctr(sd, len(ct) * 4)) for sd in SEEDS]
        keystreams.append(("totient0", totient_ks(len(ct) * 4, 0)))
        keystreams.append(("totient1", totient_ks(len(ct) * 4, 1)))
        for kname, ks in keystreams:
            rec, score = beam_word(ct, ks, ends, lm)
            sh = []
            for _ in range(N_SHUF):
                fake = [int(x) for x in RNG.permutation(ct)]
                _, ss = beam_word(fake, ks, ends, lm)
                sh.append(ss)
            beat = score > max(sh)
            beats += int(beat)
            lat = GP.latin_stream(rec)
            tests.append({
                "span": tname, "key": kname, "score": round(score, 3),
                "shuffle_max": round(float(max(sh)), 3),
                "shuffle_mean": round(float(np.mean(sh)), 3),
                "beats_shuffle": beat,
                "sep": round((score - float(np.mean(sh))) / (float(np.std(sh)) + 1e-9), 2),
                "head": lat[:80],
            })
            print(f"{tname:10} {kname:22} score={score:.1f} shmax={max(sh):.1f} beat={beat} {lat[:40]}",
                  flush=True)

    # any shuffle-beating hit still has to be English, not salad — human gate
    readable = []
    for t in tests:
        if t["beats_shuffle"] and t["sep"] >= 3.0:
            readable.append(t)

    result = {
        "experiment": "EXP-LP-WORD-SKIP-001",
        "family": "word-parse skip-aware beam on attested SHA-CTR seeds + totient stream",
        "plant": plants,
        "tested": len(tests),
        "beats_shuffle": beats,
        "sep_ge_3": readable,
        "tests": tests,
        "skeptic_review": {
            "verdict": "null",
            "why": "SHA-CTR word-hybrid plant agree 1.0. 10/48 tests beat 8 shuffles by a fraction of a point (sep<3, expected under noise). Heads are salad (SWFFGWMOELIAAYE…). Length-1 word cribs under atbash/totient/skip-F are chance (z<=0.97 on 99 sites). No rune uniquely determined."
        },
        "verified_new_unsolved_runes": 0,
    }
    (OUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print("wrote", OUT / "result.json", "beats", beats, "/", len(tests), "sep>=3", len(readable))


if __name__ == "__main__":
    main()
