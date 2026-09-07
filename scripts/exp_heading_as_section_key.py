#!/usr/bin/env python3
"""Decrypt red-page openings, then use the recovered latin as a Vigenere key
for the following section. This is the solved-page pattern (heading + body key).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cicada.liber_primus.ciphers import (  # noqa: E402
    atbash,
    caesar,
    totient_prime_stream,
    totient_skip_ciphertext_f_ordinal,
    vigenere_decrypt,
)
from cicada.liber_primus.gematria import Gematria  # noqa: E402
from cicada.paths import ROOT as CICADA_ROOT  # noqa: E402
from cicada.scoring import score_candidate  # noqa: E402

GP = Gematria()
PAGE_DIR = CICADA_ROOT / "corpus/normalized/rtkd_pages"
OUT = CICADA_ROOT / "experiments" / "EXP-LP-HEADING-SECTION-KEY-001"

# onion inclusive start, exclusive end. 56-57 solved, omitted from body.
SECTIONS = [
    (0, 3, "0"),
    (3, 8, "3"),
    (8, 15, "8"),
    (15, 23, "15"),
    (23, 27, "23"),
    (27, 33, "27"),
    (33, 40, "33"),
    (40, 54, "40"),
    (54, 56, "54"),
]


def split_of(onion: int) -> int:
    return 15 + onion


def page_ix(onion: int) -> list[int]:
    return GP.rune_indices((PAGE_DIR / f"split_{split_of(onion):03d}.txt").read_text(encoding="utf-8"))


def words_of_page(onion: int) -> list[list[int]]:
    text = (PAGE_DIR / f"split_{split_of(onion):03d}.txt").read_text(encoding="utf-8")
    words, cur = [], []
    for tok in GP.tokenize(text):
        if tok.kind == "rune" and tok.index is not None:
            cur.append(tok.index)
        elif tok.kind in {"sep", "punct", "layout"} and cur:
            words.append(cur)
            cur = []
    if cur:
        words.append(cur)
    return words


def heading_candidates(onion: int) -> list[tuple[str, list[int]]]:
    words = words_of_page(onion)
    out = []
    acc: list[int] = []
    for i, w in enumerate(words[:6]):
        acc = acc + w
        if 4 <= len(acc) <= 34:
            out.append((f"words0-{i}", list(acc)))
    ix = page_ix(onion)
    for n in (5, 6, 7, 8, 9, 10, 11, 12, 13, 16, 20):
        if n <= len(ix):
            out.append((f"prefix{n}", ix[:n]))
    # unique by tuple
    seen = set()
    uniq = []
    for name, seq in out:
        t = tuple(seq)
        if t in seen:
            continue
        seen.add(t)
        uniq.append((name, seq))
    return uniq


def heading_plains(ct: list[int]) -> list[tuple[str, list[int], str]]:
    plains = [
        ("direct", ct, GP.latin_stream(ct)),
        ("atbash", atbash(ct), GP.latin_stream(atbash(ct))),
        ("atbash_plus_3", caesar(atbash(ct), 3), GP.latin_stream(caesar(atbash(ct), 3))),
        ("totient", totient_prime_stream(ct), GP.latin_stream(totient_prime_stream(ct))),
        ("tot_skip4", totient_skip_ciphertext_f_ordinal(ct, 4), GP.latin_stream(totient_skip_ciphertext_f_ordinal(ct, 4))),
    ]
    for s in range(29):
        a = caesar(ct, s)
        plains.append((f"caesar_{s}", a, GP.latin_stream(a)))
        b = caesar(atbash(ct), s)
        plains.append((f"atb_c_{s}", b, GP.latin_stream(b)))
    return plains


def load_words() -> set[str]:
    words = set()
    p = Path("/usr/share/dict/words")
    if p.exists():
        for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
            w = line.strip().upper()
            if w.isalpha() and 3 <= len(w) <= 16:
                words.add(w)
    words.update(
        "ANEND AKOAN AWARNING SOMEWISDOM KNOWTHIS PARABLE WELCOME DIVINITY "
        "INSTRUCTION PRESERVATION ADHERENCE CONSUMPTION PILGRIM CIRCUMFERENCE "
        "WISDOM WARNING SACRED COMMAND ENLIGHTENED UNREASONABLE".split()
    )
    return words


def wordish(latin: str, dict_words: set[str]) -> bool:
    if latin in dict_words:
        return True
    # consecutive dict words covering the string
    i = 0
    hits = 0
    while i < len(latin):
        found = False
        for L in range(min(16, len(latin) - i), 2, -1):
            if latin[i : i + L] in dict_words:
                i += L
                hits += 1
                found = True
                break
        if not found:
            return hits >= 2 and i >= 0.7 * len(latin)
    return hits >= 1


def section_body(start: int, end: int, skip_heading_n: int) -> list[int]:
    body = []
    first = page_ix(start)
    body.extend(first[skip_heading_n:])
    for o in range(start + 1, end):
        body.extend(page_ix(o))
    return body


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    dict_words = load_words()
    hits = []
    tested = 0
    heading_log = []
    for start, end, tag in SECTIONS:
        cands = heading_candidates(start)
        for hname, hct in cands:
            for mname, hpt, latin in heading_plains(hct):
                if not wordish(latin, dict_words):
                    continue
                heading_log.append({"section": tag, "heading": hname, "method": mname, "latin": latin, "n": len(hct)})
                key = hpt
                if not key:
                    continue
                body = section_body(start, end, len(hct))
                if len(body) < 40:
                    continue
                for rel, out in (
                    ("sub", vigenere_decrypt(body, key)),
                    ("sub_skipF", vigenere_decrypt(body, key, skip_plaintext_f=True)),
                    ("add", [(body[i] + key[i % len(key)]) % 29 for i in range(len(body))]),
                ):
                    tested += 1
                    blat = GP.latin_stream(out)
                    sc = score_candidate(out, blat)
                    rec = {
                        "section": f"{start}-{end}",
                        "heading": hname,
                        "h_method": mname,
                        "h_latin": latin,
                        "rel": rel,
                        "body_n": len(body),
                        "head": blat[:100],
                        **sc,
                    }
                    if sc["trigram_per_100"] >= 3.2 or sc["ioc"] >= 0.05:
                        hits.append(rec)
                        print("KEEP", rec["section"], mname, latin, rel, f"tri={sc['trigram_per_100']:.2f}", blat[:70])
    # also: use heading CT itself as key (no decrypt)
    for start, end, tag in SECTIONS:
        for hname, hct in heading_candidates(start)[:4]:
            body = section_body(start, end, len(hct))
            if len(body) < 40 or not hct:
                continue
            tested += 1
            out = vigenere_decrypt(body, hct)
            blat = GP.latin_stream(out)
            sc = score_candidate(out, blat)
            if sc["trigram_per_100"] >= 3.2:
                hits.append({"section": f"{start}-{end}", "heading": hname, "h_method": "ct_as_key", "h_latin": GP.latin_stream(hct), "rel": "sub", "body_n": len(body), "head": blat[:100], **sc})

    hits.sort(key=lambda r: r.get("trigram_per_100", 0), reverse=True)
    (OUT / "headings_wordish.json").write_text(json.dumps(heading_log, indent=2) + "\n", encoding="utf-8")
    (OUT / "result.json").write_text(
        json.dumps({"tested": tested, "n_wordish_headings": len(heading_log), "hits": hits[:40], "n_hits": len(hits)}, indent=2) + "\n",
        encoding="utf-8",
    )
    print("wordish headings", len(heading_log))
    for h in heading_log[:30]:
        print(" H", h["section"], h["method"], h["latin"])
    print("tested", tested, "body-keeps", len(hits))
    for h in hits[:12]:
        print(" B", h.get("section"), h.get("h_latin"), h.get("rel"), h.get("trigram_per_100"), h.get("head", "")[:60])


if __name__ == "__main__":
    main()
