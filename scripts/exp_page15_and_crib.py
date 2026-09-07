#!/usr/bin/env python3
"""Page-15 square reading orders + p53 word-shape dictionary fill.

Image 15.jpg (sha256 5543cfce...) shows the 4x4 C-grid with 3299 in red
and an infinity mark. rtkd split_030 matches that grid exactly.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cicada.liber_primus.ciphers import atbash, caesar, vigenere_decrypt  # noqa: E402
from cicada.liber_primus.gematria import Gematria  # noqa: E402
from cicada.paths import ROOT as CICADA_ROOT  # noqa: E402
from cicada.scoring import score_candidate  # noqa: E402

GP = Gematria()
PAGE_DIR = CICADA_ROOT / "corpus/normalized/rtkd_pages"
OUT = CICADA_ROOT / "experiments" / "EXP-LP-PAGE15-CRIB-001"

# row-major as printed on 15.jpg / split_030
GRID = [
    [3258, 3222, 3152, 3038],
    [3278, 3299, 3298, 2838],
    [3288, 3294, 3296, 2472],
    [4516, 1206, 708, 1820],
]
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
    if cur:
        words.append("".join(cur))
    return words


def show(label: str, idxs: list[int]) -> dict:
    latin = GP.latin_stream(idxs)
    sc = score_candidate(idxs, latin)
    rec = {"label": label, "latin": latin[:160], "n": len(idxs), **sc}
    print(f"{label:28s} tri={sc['trigram_per_100']:5.2f} ioc={sc['ioc']:.3f} vow={sc['vowelish_ratio']:.3f} {latin[:90]}")
    return rec


def spiral_from(r0: int, c0: int, clockwise: bool = True) -> list[int]:
    seen = set()
    out = []
    r, c = r0, c0
    # right, down, left, up
    dirs = [(0, 1), (1, 0), (0, -1), (-1, 0)]
    if not clockwise:
        dirs = [(0, -1), (1, 0), (0, 1), (-1, 0)]
    di = 0
    for _ in range(16):
        out.append(GRID[r][c])
        seen.add((r, c))
        nr, nc = r + dirs[di][0], c + dirs[di][1]
        if not (0 <= nr < 4 and 0 <= nc < 4) or (nr, nc) in seen:
            di = (di + 1) % 4
            nr, nc = r + dirs[di][0], c + dirs[di][1]
        r, c = nr, nc
    return out


def page15_attacks() -> dict:
    t = page_text(30)
    # runes before the number grid vs after
    pre = GP.rune_indices(t.split("&")[0])
    post = GP.rune_indices(t.split("&", 1)[-1])
    all_ix = GP.rune_indices(t)
    print("split030 pre", len(pre), GP.latin_stream(pre), "post", len(post), "all", len(all_ix))

    results = []
    for name, seq in (
        ("pre_direct", pre),
        ("pre_atbash", atbash(pre)),
        ("post_direct", post[:80]),
        ("post_atbash", atbash(post)[:80]),
    ):
        results.append(show(name, seq if name.startswith("pre") else seq))

    for shift in range(29):
        rec = show(f"pre_caesar_{shift}", caesar(pre, shift))
        if rec["trigram_per_100"] >= 5:
            results.append(rec)
        rec = show(f"pre_atb_c_{shift}", caesar(atbash(pre), shift))
        if rec["trigram_per_100"] >= 5:
            results.append(rec)

    # only keep interesting pre in print; dump all pre to file
    pre_all = []
    for shift in range(29):
        pre_all.append({"shift": shift, "caesar": GP.latin_stream(caesar(pre, shift)), "atb": GP.latin_stream(caesar(atbash(pre), shift))})

    orders = {
        "row_major": [n for row in GRID for n in row],
        "col_major": [GRID[r][c] for c in range(4) for r in range(4)],
        "row_rev": [n for row in GRID for n in reversed(row)],
        "fib_gen": [3299, 3298, 3296, 3294, 3288, 3278, 3258, 3222, 3152, 3038, 2838, 2472, 1820, 708, 1206, 4516],
        "spiral_F_cw": spiral_from(1, 1, True),
        "spiral_F_ccw": spiral_from(1, 1, False),
        "spiral_00_cw": spiral_from(0, 0, True),
        "diag": [GRID[i][i] for i in range(4)] + [GRID[i][3 - i] for i in range(4)],
        # infinity-ish: left lobe then right lobe
        "inf_left_right": [
            GRID[1][1],
            GRID[1][0],
            GRID[0][0],
            GRID[0][1],
            GRID[1][1],
            GRID[2][1],
            GRID[3][1],
            GRID[3][0],
            GRID[2][0],
            GRID[1][2],
            GRID[0][2],
            GRID[0][3],
            GRID[1][3],
            GRID[2][3],
            GRID[3][3],
            GRID[3][2],
        ],
    }
    key_results = []
    targets = {"pre": pre, "post": post, "all": all_ix, "unsolved_head": GP.rune_indices(page_text(15))[:200]}
    # also neighbors of onion 15
    targets["split029"] = GP.rune_indices(page_text(29))
    targets["split031"] = GP.rune_indices(page_text(31))

    for oname, nums in orders.items():
        key = [n % 29 for n in nums]
        for tname, ct in targets.items():
            if not ct:
                continue
            L = len(key)
            for rel, out in (
                ("sub", vigenere_decrypt(ct, key)),
                ("add", [(ct[i] + key[i % L]) % 29 for i in range(len(ct))]),
                ("beau", [(key[i % L] - ct[i]) % 29 for i in range(len(ct))]),
            ):
                latin = GP.latin_stream(out)
                sc = score_candidate(out, latin)
                rec = {"label": f"{tname}/{oname}/{rel}", "latin": latin[:160], "n": len(out), **sc}
                rec.update({"order": oname, "target": tname, "rel": rel, "key_mod29": key})
                if rec["trigram_per_100"] >= 4 or rec["ioc"] >= 0.05:
                    key_results.append(rec)
                    print(f"KEEP {rec['label']:40s} tri={sc['trigram_per_100']:5.2f} {latin[:70]}")

    return {"pre_all_shifts": pre_all, "key_interesting": key_results, "orders": {k: v for k, v in orders.items()}}


def load_dict() -> dict[int, list[tuple[str, list[int]]]]:
    buckets: dict[int, list[tuple[str, list[int]]]] = defaultdict(list)
    path = Path("/usr/share/dict/words")
    extra = """
    THERE THESE THOSE WHICH WOULD COULD SHOULD EVERY AFTER FIRST OTHER ABOUT THEIR
    PRESERVATION PRESERUATIAN UNREASONABLE ENLIGHTENED INSTRUCTION CONSUMPTION
    ADHERENCE DIVINITY CIRCUMFERENCE PILGRIM WISDOM WARNING PARABLE WELCOME
    WITHIN EXISTS DEEP HASHES DUTY EVERY SEEK PAGE KOAN LOSS SACRED COMMAND
    KNOW THIS SOME AN END THE FOR ALL IS OF TO IN AS AT IF IT SO ON WE HE
    BE OR BY MY NO DO GO US YE AN
    LITTLE PEOPLE NUMBER THROUGH BEFORE BECOME BETWEEN ANOTHER WITHOUT NOTHING
    ALWAYS NEVER TRUTH LIGHT DARKNESS HIDDEN SECRET MASTER STUDENT LESSON
    """.split()
    words = extra
    if path.exists():
        words += [w.strip() for w in path.read_text(encoding="utf-8", errors="ignore").splitlines() if w.isascii()]
    seen = set()
    for w in words:
        w = w.upper()
        if not w.isalpha() or w in seen:
            continue
        seen.add(w)
        try:
            ix = GP.encode_latin_key(w)
        except ValueError:
            continue
        n = len(ix)
        if n in CRIB_SHAPE:
            buckets[n].append((w, ix))
    # prefer shorter lists: cap huge buckets by keeping common-looking words first
    common = set(
        """THE AND FOR ARE BUT NOT YOU ALL CAN HER WAS ONE OUR OUT DAY GET HAS HIM HIS HOW
        MAN NEW NOW OLD SEE TWO WAY WHO DID ITS LET PUT SAY SHE TOO USE THAT WITH HAVE THIS
        FROM THEY WILL WERE BEEN WHEN WHAT YOUR MORE SAID SOME INTO THERE WHICH WOULD THEIR
        ABOUT COULD OTHER AFTER FIRST THESE THOSE SHALL EVERY SHOULD THROUGH BEFORE LITTLE
        PEOPLE NUMBER BECOME BETWEEN ANOTHER WITHOUT NOTHING ALWAYS NEVER TRUTH LIGHT
        OF TO IN IS AN OR BE AS AT IF IT SO ON WE HE ME NO DO GO BY MY US YE UP
        PRESERUATIAN UNREASONABLE ENLIGHTENED PRESERVATION INSTRUCTION CONSUMPTION
        ADHERENCE DIVINITY""".split()
    )
    for n, items in buckets.items():
        items.sort(key=lambda x: (0 if x[0] in common else 1, len(x[0]), x[0]))
        if n >= 4 and len(items) > 400:
            buckets[n] = items[:400]
        if n == 2 and len(items) > 80:
            buckets[n] = [x for x in items if x[0] in common or len(x[0]) <= 3][:80]
        if n == 3 and len(items) > 120:
            buckets[n] = items[:120]
        if n == 5 and len(items) > 250:
            buckets[n] = items[:250]
        if n == 6 and len(items) > 250:
            buckets[n] = items[:250]
    print("dict buckets", {k: len(v) for k, v in sorted(buckets.items())})
    return buckets


def crib_fill() -> dict:
    t = page_text(68)
    ws = words_of(t)
    lens = [len(GP.rune_indices(w)) for w in ws]
    # last 12 words should be the crib
    assert tuple(lens[-12:]) == CRIB_SHAPE, lens[-12:]
    ct_words = [GP.rune_indices(w) for w in ws[-12:]]
    ct = [x for w in ct_words for x in w]
    assert len(ct) == 51

    buckets = load_dict()
    grams = ("THE", "AND", "ING", "ENT", "ION", "HER", "FOR", "THA", "NTH", "INT", "HAT", "ERE", "YOU")

    def pref_score(latin: str) -> float:
        if len(latin) < 6:
            return 0.0
        hits = sum(latin.count(g) for g in grams)
        return 100.0 * hits / len(latin)

    beam: list[tuple[float, list[str], list[int]]] = [(0.0, [], [])]
    for slot, need in enumerate(CRIB_SHAPE):
        nxt = []
        cands = buckets.get(need, [])
        for score, words, so_far in beam:
            for w, ix in cands:
                nxt.append((pref_score(GP.latin_stream(so_far + ix)), words + [w], so_far + ix))
        nxt.sort(key=lambda x: x[0], reverse=True)
        beam = nxt[:220]
        print(f"  slot {slot} need {need} beam_top {beam[0][0]:.2f} {beam[0][1]}")

    # also force 11-rune slot to the three book words
    forced_notes = []
    book11 = ["PRESERUATIAN", "UNREASONABLE", "ENLIGHTENED"]
    # re-run a tiny forced beam
    beam2: list[tuple[float, list[str], list[int]]] = [(0.0, [], [])]
    for slot, need in enumerate(CRIB_SHAPE):
        nxt = []
        if slot == 3:
            cands = []
            for w in book11:
                try:
                    cands.append((w, GP.encode_latin_key(w)))
                except ValueError:
                    pass
        else:
            cands = buckets.get(need, [])
        for score, words, so_far in beam2:
            for w, ix in cands:
                nxt.append((pref_score(GP.latin_stream(so_far + ix)), words + [w], so_far + ix))
        nxt.sort(key=lambda x: x[0], reverse=True)
        beam2 = nxt[:180]
    print("forced11 top", beam2[0][1], beam2[0][0] if beam2 else None)

    def implied_ks(pt: list[int]) -> list[int]:
        return [(ct[i] - pt[i]) % 29 for i in range(51)]

    def ks_structure(ks: list[int]) -> dict:
        # period-1..12 IoC of repeating assumption: check if ks[i]==ks[i+p]
        best_p = None
        best_frac = -1
        for p in range(1, 13):
            agree = sum(1 for i in range(p, 51) if ks[i] == ks[i % p]) / (51 - p)
            if agree > best_frac:
                best_frac = agree
                best_p = p
        return {"best_period": best_p, "period_agree": round(best_frac, 3), "head": ks[:16]}

    top = []
    for score, words, pt in beam[:15] + beam2[:8]:
        ks = implied_ks(pt)
        st = ks_structure(ks)
        # extend ks periodically onto previous 80 runes of the page
        page_ix = GP.rune_indices(t)
        # crib is the last 51
        before = page_ix[:-51]
        if st["best_period"] and st["period_agree"] >= 0.6:
            p = st["best_period"]
            ext = [(before[i] - ks[(i - len(before)) % p]) % 29 for i in range(len(before))]
            ext_latin = GP.latin_stream(ext[-80:])
        else:
            ext_latin = ""
        rec = {
            "score": score,
            "words": words,
            "pt": GP.latin_stream(pt),
            "ks_struct": st,
            "extend_tail": ext_latin,
        }
        top.append(rec)
        print("FILL", score, words, "per", st, "pt", rec["pt"])

    return {
        "ct_latin_direct": GP.latin_stream(ct),
        "top_fills": top,
        "beam_width": 220,
        "note": "fills are hypothesized plains matching word lengths only; not decrypts unless keystream extends",
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    p15 = page15_attacks()
    (OUT / "page15.json").write_text(json.dumps(p15, indent=2) + "\n", encoding="utf-8")
    crib = crib_fill()
    (OUT / "crib_fill.json").write_text(json.dumps(crib, indent=2) + "\n", encoding="utf-8")
    interesting = [r for r in p15["key_interesting"] if r["trigram_per_100"] >= 5]
    print("page15 interesting>=5", len(interesting))
    print("done")


if __name__ == "__main__":
    main()
