#!/usr/bin/env python3
"""Acrostics and first-word streams over unsolved rtkd splits 15-70."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cicada.liber_primus.ciphers import apply_named, atbash, caesar, totient_prime_stream  # noqa: E402
from cicada.liber_primus.gematria import Gematria  # noqa: E402
from cicada.experiments import KNOWN_KEYS  # noqa: E402
from cicada.paths import ROOT as CICADA_ROOT  # noqa: E402
from cicada.scoring import score_candidate  # noqa: E402

GP = Gematria()
PAGE_DIR = CICADA_ROOT / "corpus/normalized/rtkd_pages"
OUT = CICADA_ROOT / "experiments" / "EXP-LP-ACROSTIC-UNSOLVED-001"


def page_text(s: int) -> str:
    return (PAGE_DIR / f"split_{s:03d}.txt").read_text(encoding="utf-8")


def words_of(text: str) -> list[str]:
    words, cur = [], []
    for tok in GP.tokenize(text):
        if tok.kind == "rune":
            cur.append(tok.raw)
        elif tok.kind in {"sep", "punct", "layout"} and cur:
            words.append("".join(cur))
            cur = []
    if cur:
        words.append("".join(cur))
    return words


def try_methods(label: str, idxs: list[int], rows: list) -> None:
    if len(idxs) < 8:
        return
    tests = [
        ("direct", idxs),
        ("atbash", atbash(idxs)),
        ("atbash_plus_3", caesar(atbash(idxs), 3)),
        ("totient", totient_prime_stream(idxs)),
    ]
    for kn, key in KNOWN_KEYS.items():
        tests.append((f"vig_{kn}", apply_named("vigenere", idxs, key)))
    for shift in range(29):
        tests.append((f"caesar_{shift}", caesar(idxs, shift)))
        tests.append((f"atb_c_{shift}", caesar(atbash(idxs), shift)))
    best = None
    for name, out in tests:
        latin = GP.latin_stream(out)
        sc = score_candidate(out, latin)
        rec = {"stream": label, "method": name, "latin": latin, **sc}
        if best is None or sc["trigram_per_100"] > best["trigram_per_100"]:
            best = rec
        if sc["trigram_per_100"] >= 6 and 0.28 <= sc["vowelish_ratio"] <= 0.52:
            rows.append({**rec, "keep": True})
    rows.append({**best, "keep": False, "note": "best-of-stream"})
    print(f"{label:22s} best {best['method']:16s} tri={best['trigram_per_100']:5.2f} {best['latin'][:80]}")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    first_page = []
    last_page = []
    first_word = []
    last_word = []
    first_line = []
    last_line = []
    # line = runes between / or newline
    for s in range(15, 71):
        t = page_text(s)
        ix = GP.rune_indices(t)
        if not ix:
            continue
        first_page.append(ix[0])
        last_page.append(ix[-1])
        ws = words_of(t)
        if ws:
            first_word.extend(GP.rune_indices(ws[0]))
            last_word.extend(GP.rune_indices(ws[-1]))
        lines = []
        cur = []
        for ch in t:
            if ch in GP.by_rune:
                cur.append(ch)
            elif ch in "/\n" and cur:
                lines.append("".join(cur))
                cur = []
        if cur:
            lines.append("".join(cur))
        if lines:
            first_line.append(GP.rune_indices(lines[0])[0])
            last_line.append(GP.rune_indices(lines[-1])[0])

    rows = []
    try_methods("first_rune_page", first_page, rows)
    try_methods("last_rune_page", last_page, rows)
    try_methods("first_word_concat", first_word, rows)
    try_methods("last_word_concat", last_word, rows)
    try_methods("first_of_line", first_line, rows)
    try_methods("last_of_line", last_line, rows)

    # DJUBEI positions: verify and dump implied key delta if same plaintext
    # 6-gram [23,11,1,17,18,10]
    needle = [23, 11, 1, 17, 18, 10]
    flat = []
    for s in range(15, 71):
        flat.extend(GP.rune_indices(page_text(s)))
    locs = []
    for i in range(len(flat) - 5):
        if flat[i : i + 6] == needle:
            locs.append(i)
    print("DJUBEI locs", locs)
    delta = None
    if len(locs) >= 2:
        a, b = locs[0], locs[1]
        # if same PT, ks[b+i]-ks[a+i] = ct[b+i]-ct[a+i] = 0, so key repeats or same
        # already identical CT so identical PT implies identical key slice
        delta = "identical-ct-slices-imply-identical-key-slices-if-same-function"

    (OUT / "result.json").write_text(
        json.dumps(
            {
                "streams": {
                    "first_page_latin_direct": GP.latin_stream(first_page),
                    "first_word_latin_direct": GP.latin_stream(first_word)[:200],
                    "n_pages_with_runes": len(first_page),
                },
                "rows": rows,
                "djubei": {"locs": locs, "note": delta},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
