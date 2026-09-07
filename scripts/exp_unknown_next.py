#!/usr/bin/env python3
"""Bounded next-wave attacks on unsolved LP2 (rtkd splits 15-70).

Does not claim a decrypt. Writes experiment JSON under experiments/.
"""
from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cicada.liber_primus.ciphers import (  # noqa: E402
    apply_named,
    atbash,
    caesar,
    totient_prime_stream,
    vigenere_decrypt,
)
from cicada.liber_primus.fixtures import load_fixtures  # noqa: E402
from cicada.liber_primus.gematria import Gematria, first_n_primes  # noqa: E402
from cicada.experiments import KNOWN_KEYS  # noqa: E402
from cicada.paths import ROOT as CICADA_ROOT  # noqa: E402
from cicada.scoring import score_candidate  # noqa: E402

GP = Gematria()
PAGE_DIR = CICADA_ROOT / "corpus/normalized/rtkd_pages"
OUT = CICADA_ROOT / "experiments" / "EXP-LP-UNKNOWN-NEXT-001"
CRIB_SHAPE = (5, 4, 4, 11, 2, 3, 2, 6, 5, 5, 2, 2)


def page_text(split: int) -> str:
    return (PAGE_DIR / f"split_{split:03d}.txt").read_text(encoding="utf-8")


def words_of(text: str) -> list[str]:
    words: list[str] = []
    cur: list[str] = []
    for tok in GP.tokenize(text):
        if tok.kind == "rune":
            cur.append(tok.raw)
        elif tok.kind in {"sep", "punct", "layout"} and cur:
            words.append("".join(cur))
            cur = []
        elif tok.kind == "break" and cur:
            # line-break is not a word break in rtkd
            continue
    if cur:
        words.append("".join(cur))
    return words


def word_lens(words: list[str]) -> list[int]:
    return [len(GP.rune_indices(w)) for w in words]


def interesting(sc: dict) -> bool:
    return (
        sc["trigram_per_100"] >= 6
        and 0.26 <= sc["vowelish_ratio"] <= 0.55
        and sc["ioc"] >= 0.040
    )


def flatten_unsolved() -> tuple[list[int], list[tuple[int, int]]]:
    flat: list[int] = []
    pos: list[tuple[int, int]] = []
    for s in range(15, 71):
        ix = GP.rune_indices(page_text(s))
        for j, x in enumerate(ix):
            flat.append(x)
            pos.append((s, j))
    return flat, pos


def sha256_ctr(seed: bytes, n: int, counter_width: int = 4, endian: str = "big") -> list[int]:
    out: list[int] = []
    i = 0
    while len(out) < n:
        ctr = i.to_bytes(counter_width, endian)
        digest = hashlib.sha256(seed + ctr).digest()
        for b in digest:
            out.append(b % 29)
            if len(out) >= n:
                break
        i += 1
    return out


def map_word_shapes() -> dict:
    pages = []
    all_words = []
    for s in range(15, 71):
        t = page_text(s)
        ws = words_of(t)
        lens = word_lens(ws)
        pages.append(
            {
                "split": s,
                "onion": s - 15,
                "rune_count": sum(lens),
                "n_words": len(lens),
                "n_one_rune_words": sum(1 for x in lens if x == 1),
                "max_word": max(lens) if lens else 0,
                "first_words": lens[:12],
            }
        )
        for w, n in zip(ws, lens):
            all_words.append({"split": s, "n": n, "head": GP.latin_stream(GP.rune_indices(w))[:20]})

    crib_hits = []
    flat_n = [w["n"] for w in all_words]
    for j in range(len(flat_n) - 11):
        if tuple(flat_n[j : j + 12]) == CRIB_SHAPE:
            crib_hits.append(all_words[j : j + 12])

    # last-51 rune word tails
    tails = []
    for s in range(15, 71):
        ws = words_of(page_text(s))
        acc = 0
        tail = []
        for w in reversed(ws):
            n = len(GP.rune_indices(w))
            tail.append(n)
            acc += n
            if acc >= 51:
                break
        tail = list(reversed(tail))
        tails.append({"split": s, "onion": s - 15, "tail_shape": tail, "acc": acc})

    return {"pages": pages, "crib_hits": crib_hits, "tails_ge_51": tails, "total_words": len(all_words)}


def heading_transfer() -> dict:
    """First 1-4 words of each unsolved page under solved methods."""
    methods = [
        ("direct", None),
        ("atbash", None),
        ("atbash_plus_3", None),
        ("totient_prime", None),
        ("vigenere", KNOWN_KEYS["DIVINITY"]),
        ("vigenere_skip_pt_f", KNOWN_KEYS["DIVINITY"]),
        ("vigenere", KNOWN_KEYS["FIRFUMFERENFE"]),
    ]
    # also caesar 0-28 and atbash+caesar
    hits = []
    tested = 0
    samples = []
    for s in range(15, 71):
        ws = words_of(page_text(s))
        if not ws:
            continue
        # take prefix until 34 runes (artwaste heading cap)
        pref = []
        n = 0
        for w in ws:
            ix = GP.rune_indices(w)
            if n and n + len(ix) > 34:
                break
            pref.extend(ix)
            n += len(ix)
            if n >= 8 and len(pref) >= 8:
                # keep accumulating up to 34
                if n >= 20:
                    break
        if len(pref) < 4:
            continue
        for name, key in methods:
            tested += 1
            out = apply_named(name, pref, key)
            latin = GP.latin_stream(out)
            sc = score_candidate(out, latin)
            rec = {
                "split": s,
                "onion": s - 15,
                "method": name if key is None else f"{name}:{key}",
                "n": len(pref),
                "latin": latin,
                "trigram_per_100": sc["trigram_per_100"],
            }
            if s == 15:
                samples.append(rec)
            # heading vocabulary check
            compact = latin
            vocab = (
                "AKOAN",
                "ANEND",
                "ANINSTRUCTION",
                "KNOWTHIS",
                "AWARNING",
                "SOMEWISDOM",
                "THELOSSOFDIVINITY",
                "PARABLE",
                "WELCOME",
                "PRESERVATION",
                "ADHERENCE",
                "CONSUMPTION",
                "FORALLISSACRED",
                "ANINSTRUCTIONCOMMANDYOUROWNSELF",
            )
            if any(compact.startswith(v) or v in compact for v in vocab):
                hits.append({**rec, "why": "heading-vocab"})
            if sc["trigram_per_100"] >= 10 and 0.28 <= sc["vowelish_ratio"] <= 0.52:
                hits.append({**rec, "why": "trigram"})
        # caesar / atbash+caesar on short prefix
        for shift in range(29):
            tested += 1
            for lab, seq in (("caesar", caesar(pref, shift)), ("atbash_caesar", caesar(atbash(pref), shift))):
                latin = GP.latin_stream(seq)
                if any(latin.startswith(v) for v in ("ANEND", "AKOAN", "WELCOME", "PARABLE", "AWARNING", "SOMEWISDOM", "KNOWTHIS")):
                    hits.append({"split": s, "method": f"{lab}+{shift}", "latin": latin, "why": "heading-vocab-shift"})
    return {"tested": tested, "hits": hits, "split015_samples": samples[:8]}


def page56_finish() -> dict:
    fix = [f for f in load_fixtures() if f["stage_id"] == "lp2.page56_an_end"][0]
    c56 = GP.rune_indices(fix["ciphertext"])
    primes = first_n_primes(200)
    exp2 = GP.encode_latin_key("ITISTHEDVTYOFEVERYPILGRIMTOSEECOVTTHISPAGE")
    p2 = c56[45:]
    variants = {}
    # skip ciphertext F anywhere
    out = []
    k = 0
    for x in c56:
        if x == 0:
            out.append(0)
            continue
        out.append((x - (primes[k] - 1)) % 29)
        k += 1
    variants["skip_all_ct_F"] = GP.latin_stream(out)
    # skip only first ct F
    out = []
    k = 0
    skipped = False
    for x in c56:
        if x == 0 and not skipped:
            out.append(0)
            skipped = True
            continue
        out.append((x - (primes[k] - 1)) % 29)
        k += 1
    variants["skip_first_ct_F"] = GP.latin_stream(out)
    # skip_pt_F
    out = []
    k = 0
    for x in c56:
        pt = (x - (primes[k] - 1)) % 29
        out.append(pt)
        if pt != 0:
            k += 1
    variants["skip_pt_F"] = GP.latin_stream(out)
    # offset scan agree rates
    agrees = []
    for off in range(0, 90):
        dec = [(p2[i] - (primes[i + off] - 1)) % 29 for i in range(len(p2))]
        agree = sum(a == b for a, b in zip(dec, exp2)) / len(exp2)
        if agree >= 0.5:
            agrees.append({"offset": off, "agree": round(agree, 3), "latin": GP.latin_stream(dec)})
    return {
        "n": len(c56),
        "ct_F_positions": [i for i, x in enumerate(c56) if x == 0],
        "variants": variants,
        "para2_offset_hits": agrees,
        "expected_para2": GP.latin_stream(exp2),
    }


def derived_key_sweep(flat: list[int]) -> dict:
    n = min(len(flat), 800)  # score a prefix; enough to see English
    seeds = [
        b"CICADA3301",
        b"cicada3301",
        b"3301",
        b"Cicada 3301",
        b"DIVINITY",
        b"LIBERPRIMUS",
        b"Liber Primus",
        b"ANEND",
        b"AN END",
        b"FIRFUMFERENFE",
        b"CIRCUMFERENCE",
        b"INSTAR",
        b"7A35090F",
        b"6D854CD7933322A601C3286D181F01E57A35090F",
        bytes.fromhex("6D854CD7933322A601C3286D181F01E57A35090F"),
        b"845145127",
        b"20140105",
        b"201405",
        b"2014",
        b"0",
        b"15",
        b"56",
        b"57",
        b"WARNING",
        b"WISDOM",
        b"PARABLE",
        b"WELCOME",
        b"THELOSSOFDIVINITY",
        b"seek within",
        b"SEEKWITHIN",
        b"mayfly",
        b"MAYFLY",
        b"ephemeral",
        b"PRIMES",
        b"TOTIENT",
        b"Gematria Primus",
        b"GEMATRIAPRIMUS",
    ]
    # 15.jpg C sequence as seed
    C = [3299, 3298, 3296, 3294, 3288, 3278, 3258, 3222, 3152, 3038, 2838, 2472, 1820, 708, 1206, 4516]
    seeds.append(b"".join(c.to_bytes(2, "big") for c in C))
    seeds.append(",".join(map(str, C)).encode())

    best = []
    tested = 0
    for seed in seeds:
        for width, endian, hashed in (
            (4, "big", False),
            (4, "little", False),
            (8, "big", False),
            (4, "big", True),
        ):
            material = hashlib.sha256(seed).digest() if hashed else seed
            ks = sha256_ctr(material, n, width, endian)
            for lab, out in (
                ("sub", [(flat[i] - ks[i]) % 29 for i in range(n)]),
                ("add", [(flat[i] + ks[i]) % 29 for i in range(n)]),
                ("beau", [(ks[i] - flat[i]) % 29 for i in range(n)]),
            ):
                tested += 1
                latin = GP.latin_stream(out)
                sc = score_candidate(out, latin)
                rec = {
                    "seed": seed[:40].hex() if any(b < 32 or b > 126 for b in seed[:12]) else seed[:40].decode("ascii", "replace"),
                    "width": width,
                    "endian": endian,
                    "prehash": hashed,
                    "rel": lab,
                    "trigram_per_100": sc["trigram_per_100"],
                    "vowelish": sc["vowelish_ratio"],
                    "ioc": sc["ioc"],
                    "head": latin[:80],
                }
                if sc["trigram_per_100"] >= 3.5 or interesting(sc):
                    best.append(rec)
                elif sc["trigram_per_100"] >= 2.5 and sc["ioc"] >= 0.04:
                    best.append(rec)
    best.sort(key=lambda r: r["trigram_per_100"], reverse=True)
    return {"tested": tested, "n_prefix": n, "kept": best[:30], "n_kept": len(best)}


def crib_nonadditive(flat: list[int], pos: list[tuple[int, int]]) -> dict:
    """Hill 2x2 and multiplicative on the 51-rune tail of onion 53 (split 68) if shape matches,
    else on every page's last 51 runes and on first 40 of split 15.
    """
    # locate crib by walking words
    hits_shape = []
    cursor = 0
    word_spans = []
    for s in range(15, 71):
        ws = words_of(page_text(s))
        for w in ws:
            ix = GP.rune_indices(w)
            word_spans.append((s, cursor, len(ix), ix))
            cursor += len(ix)
    for j in range(len(word_spans) - 11):
        shape = tuple(word_spans[j + k][2] for k in range(12))
        if shape == CRIB_SHAPE:
            start = word_spans[j][1]
            runes = []
            for k in range(12):
                runes.extend(word_spans[j + k][3])
            hits_shape.append({"start_split": word_spans[j][0], "start_flat": start, "n": len(runes)})

    targets = []
    if hits_shape:
        start = hits_shape[0]["start_flat"]
        targets.append(("p53_shape_crib", flat[start : start + 51]))
    targets.append(("split015_head40", GP.rune_indices(page_text(15))[:40]))
    # onion 53 = split 68 last 51
    ix68 = GP.rune_indices(page_text(68))
    if len(ix68) >= 51:
        targets.append(("split068_tail51", ix68[-51:]))
    ix53 = GP.rune_indices(page_text(53))  # onion 38
    if len(ix53) >= 51:
        targets.append(("split053_tail51", ix53[-51:]))

    def inv(a: int) -> int:
        return pow(a, 27, 29)  # a^(p-2)

    hill_hits = []
    tested = 0
    # multiplicative a*x+b already excluded globally; still try on crib only for heading vocab
    for tname, ct in targets:
        for a in range(1, 29):
            ai = inv(a)
            for b in range(29):
                tested += 1
                out = [(ai * (x - b)) % 29 for x in ct]
                latin = GP.latin_stream(out)
                if any(w in latin for w in ("THE", "AND", "ING", "WELCOME", "ANEND", "INSTRUCTION")):
                    sc = score_candidate(out, latin)
                    if sc["trigram_per_100"] >= 8:
                        hill_hits.append({"target": tname, "kind": "affine", "a": a, "b": b, "latin": latin, **sc})

        # Hill 2x2 exhaustive on even prefix
        if len(ct) < 20:
            continue
        pairs = len(ct) // 2
        c0 = ct[0 : 2 * pairs : 2]
        c1 = ct[1 : 2 * pairs : 2]
        # brute invertible 2x2 decrypt matrices
        local_best = None
        for a in range(29):
            for b in range(29):
                for c in range(29):
                    for d in range(29):
                        det = (a * d - b * c) % 29
                        if det == 0:
                            continue
                        tested += 1
                        di = inv(det)
                        ia = (d * di) % 29
                        ib = ((-b) * di) % 29
                        ic = ((-c) * di) % 29
                        id_ = (a * di) % 29
                        out = []
                        for i in range(pairs):
                            p0 = (ia * c0[i] + ib * c1[i]) % 29
                            p1 = (ic * c0[i] + id_ * c1[i]) % 29
                            out.extend((p0, p1))
                        latin = GP.latin_stream(out)
                        # cheap filter
                        if "THE" not in latin and "AND" not in latin and "ING" not in latin:
                            continue
                        sc = score_candidate(out, latin)
                        if local_best is None or sc["trigram_per_100"] > local_best["trigram_per_100"]:
                            local_best = {"target": tname, "kind": "hill2", "A": [a, b, c, d], "latin": latin[:100], **sc}
                        if sc["trigram_per_100"] >= 8 and 0.28 <= sc["vowelish_ratio"] <= 0.52:
                            hill_hits.append({"target": tname, "kind": "hill2", "A": [a, b, c, d], "latin": latin, **sc})
        if local_best:
            hill_hits.append({"best_of_target": local_best})

    return {"crib_locations": hits_shape, "tested": tested, "hits": hill_hits[:40]}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    shapes = map_word_shapes()
    (OUT / "word_shapes.json").write_text(json.dumps(shapes, indent=2) + "\n", encoding="utf-8")
    print("crib_hits", len(shapes["crib_hits"]))
    if shapes["crib_hits"]:
        print("first crib", shapes["crib_hits"][0])
    # show tails that match
    for t in shapes["tails_ge_51"]:
        if t["tail_shape"][:12] == list(CRIB_SHAPE) or t["acc"] == 51:
            print("tail", t)

    p56 = page56_finish()
    (OUT / "page56.json").write_text(json.dumps(p56, indent=2) + "\n", encoding="utf-8")
    print("page56 skip_pt_F", p56["variants"]["skip_pt_F"][:90])
    print("page56 skip_first_ct_F", p56["variants"]["skip_first_ct_F"][:90])
    print("page56 offset hits", p56["para2_offset_hits"])

    heads = heading_transfer()
    (OUT / "headings.json").write_text(json.dumps(heads, indent=2) + "\n", encoding="utf-8")
    print("heading tested", heads["tested"], "hits", len(heads["hits"]))
    for h in heads["hits"][:20]:
        print(" HEAD", h)

    flat, pos = flatten_unsolved()
    print("unsolved runes", len(flat))
    derived = derived_key_sweep(flat)
    (OUT / "derived_key.json").write_text(json.dumps(derived, indent=2) + "\n", encoding="utf-8")
    print("derived tested", derived["tested"], "kept", derived["n_kept"])
    for r in derived["kept"][:8]:
        print(" DER", r["trigram_per_100"], r["seed"], r["rel"], r["head"][:60])

    crib = crib_nonadditive(flat, pos)
    (OUT / "crib_nonadditive.json").write_text(json.dumps(crib, indent=2) + "\n", encoding="utf-8")
    print("crib locs", crib["crib_locations"])
    print("hill/affine tested", crib["tested"], "hits", len(crib["hits"]))
    for h in crib["hits"][:12]:
        print(" CRIB", h if "latin" not in h else {k: h[k] for k in h if k != "latin"}, h.get("latin", "")[:70])

    summary = {
        "experiment_id": "EXP-LP-UNKNOWN-NEXT-001",
        "unsolved_runes": len(flat),
        "five_percent_runes": int(len(flat) * 0.05 + 0.999),
        "verified_new_decrypt_runes": 0,
        "crib_hits": len(shapes["crib_hits"]),
        "heading_hits": len(heads["hits"]),
        "derived_kept": derived["n_kept"],
        "nonadditive_hits": len(crib["hits"]),
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
