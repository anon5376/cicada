#!/usr/bin/env python3
"""Word-local totient / reverse-word / transpose-then-totient.

Word-reset Vigenere with a repeating key is closed (AUTOKEY-PORTA). Restarting
the *totient prime stream* at each transcribed word is not. Neither is reverse-
each-word, nor columnar transposition then totient (IoC-preserving rearrange
then a stream that kills IoC).

Rigid unique decodes — keep bar is valid (not an LM search).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from cicada.liber_primus.ciphers import apply_named, totient_prime_stream  # noqa: E402
from cicada.liber_primus.fixtures import load_fixtures  # noqa: E402
from cicada.liber_primus.gematria import Gematria, first_n_primes  # noqa: E402
from cicada.paths import ROOT as CICADA_ROOT  # noqa: E402
from cicada.scoring import score_candidate  # noqa: E402
from exp_skipaware_sha_ctr import keep  # noqa: E402
from exp_word_depth import idxs_of, page_text, words_of  # noqa: E402

GP = Gematria()
Q = 29
OUT = CICADA_ROOT / "experiments" / "EXP-LP-WORD-LOCAL-TOTIENT-001"


def totient_word(w: list[int], start: int = 0) -> list[int]:
    if not w:
        return []
    return totient_prime_stream(w, start=start)


def skip_first_f_totient(w: list[int]) -> list[int]:
    primes = first_n_primes(len(w) + 2)
    out, k, seen = [], 0, False
    for x in w:
        if x == 0 and not seen:
            out.append(0)
            seen = True
            continue
        out.append((x - (primes[k] - 1)) % Q)
        k += 1
    return out


def decode_words(words: list[list[int]], kind: str) -> list[int]:
    out: list[int] = []
    if kind == "tot0":
        for w in words:
            out.extend(totient_word(w, 0))
    elif kind == "tot1":
        for w in words:
            out.extend(totient_word(w, 1))
    elif kind == "tot_skipF":
        for w in words:
            out.extend(skip_first_f_totient(w))
    elif kind == "rev":
        for w in words:
            out.extend(w[::-1])
    elif kind == "rev_atbash":
        for w in words:
            out.extend((Q - 1 - x) % Q for x in w[::-1])
    elif kind == "rev_tot0":
        for w in words:
            out.extend(totient_word(w[::-1], 0))
    elif kind == "shift_len":
        for w in words:
            s = len(w) % Q
            out.extend((x - s) % Q for x in w)
    elif kind == "shift_idx":
        for i, w in enumerate(words):
            s = i % Q
            out.extend((x - s) % Q for x in w)
    elif kind == "caesar_len_atbash":
        for w in words:
            s = len(w) % Q
            out.extend((Q - 1 - ((x - s) % Q)) % Q for x in w)
    else:
        raise ValueError(kind)
    return out


def route_read_cols(seq: list[int], cols: int) -> list[int]:
    n = len(seq)
    rows = (n + cols - 1) // cols
    pad = rows * cols - n
    cells: list[int | None] = list(seq) + [None] * pad
    grid = [cells[r * cols:(r + 1) * cols] for r in range(rows)]
    out: list[int] = []
    for c in range(cols):
        for r in range(rows):
            v = grid[r][c]
            if v is not None:
                out.append(v)
    return out


def unroute_read_cols(seq: list[int], cols: int, n: int) -> list[int]:
    rows = (n + cols - 1) // cols
    pad = rows * cols - n
    grid: list[list[int | None]] = [[None] * cols for _ in range(rows)]
    k = 0
    for c in range(cols):
        for r in range(rows):
            last_row_pad = r == rows - 1 and c >= cols - pad
            if last_row_pad:
                continue
            if k < len(seq):
                grid[r][c] = seq[k]
                k += 1
    out: list[int] = []
    for r in range(rows):
        for c in range(cols):
            v = grid[r][c]
            if v is not None:
                out.append(v)
    return out


def transpose_then_totient(ct: list[int], cols: int, start: int = 0) -> list[int]:
    n = len(ct)
    if cols < 2 or cols >= n:
        return []
    plain_t = totient_prime_stream(ct, start=start)
    return unroute_read_cols(plain_t, cols, n)


def encode_totient(pt: list[int], start: int = 0) -> list[int]:
    primes = first_n_primes(len(pt) + start)
    return [(pt[i] + (primes[i + start] - 1)) % Q for i in range(len(pt))]


def plant() -> dict:
    fx = {f["stage_id"]: f for f in load_fixtures()}
    warn = fx["lp1.warning"]
    pt = apply_named(warn["method"], GP.rune_indices(warn["ciphertext"]), None)
    words = words_of(warn["ciphertext"])
    # rebuild words from PT using same lengths
    lens = [len(w) for w in words]
    pt_words, i = [], 0
    for L in lens:
        pt_words.append(pt[i:i + L])
        i += L

    out = {}
    # tot0: encrypt each PT word with totient, decode
    enc = [encode_totient(w, 0) for w in pt_words]
    rec = decode_words(enc, "tot0")
    out["tot0"] = {"agree": round(sum(a == b for a, b in zip(rec, pt)) / len(pt), 4),
                   "ok": rec == pt}
    enc_rev = [w[::-1] for w in pt_words]
    rec = decode_words(enc_rev, "rev")
    out["rev"] = {"agree": round(sum(a == b for a, b in zip(rec, pt)) / len(pt), 4),
                  "ok": rec == pt}
    # transpose cols=7 then totient
    # transpose cols=7 then totient
    cols = 7
    routed = route_read_cols(pt, cols)
    ct = encode_totient(routed, 0)
    rec = transpose_then_totient(ct, cols, 0)
    out["trans7_tot"] = {"agree": round(sum(a == b for a, b in zip(rec, pt)) / len(pt), 4),
                         "ok": rec == pt}
    out["ok"] = all(v["ok"] for v in out.values())
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    pl = plant()
    print("plant", pl, flush=True)
    if not pl["ok"]:
        (OUT / "result.json").write_text(json.dumps({
            "experiment": "EXP-LP-WORD-LOCAL-TOTIENT-001", "plant": pl,
            "verified_new_unsolved_runes": 0, "aborted": "plant failed",
        }, indent=2) + "\n")
        return

    kinds = ["tot0", "tot1", "tot_skipF", "rev", "rev_atbash", "rev_tot0",
             "shift_len", "shift_idx", "caesar_len_atbash"]
    hits = []
    tested = 0
    best = None
    for s in range(15, 71):
        text = page_text(s)
        words = words_of(text)
        n = sum(len(w) for w in words)
        if n < 80:
            continue
        for kind in kinds:
            tested += 1
            pt = decode_words(words, kind)
            lat = GP.latin_stream(pt)
            sc = score_candidate(pt, lat)
            row = {"split": s, "kind": kind, "head": lat[:80], **sc, "n": n}
            if best is None or sc["trigram_per_100"] > best["trigram_per_100"]:
                best = row
            if keep(sc, n):
                hits.append(row)
                print("KEEP", s, kind, f"tri={sc['trigram_per_100']:.2f} ioc={sc['ioc']:.3f}", lat[:50], flush=True)
        ct = idxs_of(s)
        nw = max(2, len(words))
        cols_try = list(range(2, 18)) + [nw, 29]
        for cols in dict.fromkeys(cols_try):  # unique preserve order
            if cols >= len(ct):
                continue
            for start in (0, 1):
                tested += 1
                pt = transpose_then_totient(ct, cols, start)
                if len(pt) < 80:
                    continue
                lat = GP.latin_stream(pt)
                sc = score_candidate(pt, lat)
                row = {"split": s, "kind": f"trans{cols}_tot{start}", "head": lat[:80], **sc, "n": len(pt)}
                if sc["trigram_per_100"] > best["trigram_per_100"]:
                    best = row
                if keep(sc, len(pt)):
                    hits.append(row)
                    print("KEEP", s, row["kind"], f"tri={sc['trigram_per_100']:.2f}", lat[:50], flush=True)

    # skeptic: keep-bar on totient of random is rare; still require readable English
    readable = []
    for h in hits:
        lat = h["head"]
        if any(w in lat for w in (" THE ", " AND ", " THAT ", "THIS", "WITHIN", "WISDOM")):
            if h["ioc"] >= 0.055:
                readable.append(h)

    result = {
        "experiment": "EXP-LP-WORD-LOCAL-TOTIENT-001",
        "family": "totient/caesar/reverse restarting at transcribed words; columnar-then-totient",
        "plant": pl,
        "tested": tested,
        "keep_bar_hits": len(hits),
        "keeps": [{"split": h["split"], "kind": h["kind"], "head": h["head"],
                   "trigram_per_100": h["trigram_per_100"], "ioc": h["ioc"]} for h in hits[:20]],
        "best": {k: best[k] for k in ("split", "kind", "head", "trigram_per_100", "ioc", "n")} if best else None,
        "readable_after_ioc055": readable,
        "skeptic_review": {
            "verdict": "pending" if readable else "null",
            "why": "rigid unique decode; keep bar valid. Promote only if IoC>=0.055 and readable English.",
        },
        "verified_new_unsolved_runes": 0,
    }
    (OUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print("tested", tested, "keeps", len(hits), "readable", len(readable),
          "best", best["kind"] if best else None, best["trigram_per_100"] if best else None)


if __name__ == "__main__":
    main()
