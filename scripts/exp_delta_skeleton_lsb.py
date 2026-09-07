#!/usr/bin/env python3
"""Keyless delta/cumsum; word-length skeleton vs solved plains + fetched texts;
LSB of onion JPEGs as a new keystream class.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cicada.acquisition import fetch_url  # noqa: E402
from cicada.liber_primus.gematria import Gematria  # noqa: E402
from cicada.paths import ROOT as CICADA_ROOT  # noqa: E402
from cicada.scoring import score_candidate  # noqa: E402

GP = Gematria()
PAGE_DIR = CICADA_ROOT / "corpus/normalized/rtkd_pages"
OUT = CICADA_ROOT / "experiments" / "EXP-LP-DELTA-SKELETON-LSB-001"
TRIAGE = CICADA_ROOT / "reports/candidates/image_triage.json"


def idxs_of(split: int) -> list[int]:
    return GP.rune_indices((PAGE_DIR / f"split_{split:03d}.txt").read_text(encoding="utf-8"))


def word_lens_runes(text: str) -> list[int]:
    words, cur = [], []
    for tok in GP.tokenize(text):
        if tok.kind == "rune":
            cur.append(tok.raw)
        elif tok.kind in {"sep", "punct", "layout"} and cur:
            words.append(len(cur))
            cur = []
    if cur:
        words.append(len(cur))
    return words


def word_lens_latin(s: str) -> list[int]:
    out = []
    for w in re.findall(r"[A-Za-z]+", s.upper()):
        try:
            ix = GP.encode_latin_key(w)
        except ValueError:
            continue
        if ix:
            out.append(len(ix))
    return out


def keep(sc: dict, n: int) -> bool:
    return (
        n >= 80
        and sc["trigram_per_100"] >= 3.5
        and 0.28 <= sc["vowelish_ratio"] <= 0.55
        and sc["ioc"] >= 0.045
    )


def longest_run(needle: list[int], hay: list[int]) -> tuple[int, int | None]:
    best, pos = 0, None
    if len(needle) < 4 or len(hay) < 4:
        return 0, None
    # rolling
    for i in range(0, len(hay) - 3):
        r = 0
        while r < len(needle) and i + r < len(hay) and needle[r] == hay[i + r]:
            r += 1
        if r > best:
            best, pos = r, i
            if best == len(needle):
                break
    return best, pos


def object_path(sha: str) -> Path:
    return CICADA_ROOT / "corpus/objects/sha256" / sha[:2] / sha


def sha256_ctr(seed: bytes, n: int) -> list[int]:
    out: list[int] = []
    i = 0
    while len(out) < n:
        d = hashlib.sha256(seed + i.to_bytes(4, "big")).digest()
        for b in d:
            out.append(b % 29)
            if len(out) >= n:
                break
        i += 1
    return out


SOLVED_PLAINS = {
    "warning": "A WARNING BELIEVE NOTHING FROM THIS BOOK EXCEPT WHAT YOU KNOW TO BE TRUE TEST THE KNOWLEDGE FIND YOUR TRUTH EXPERIENCE YOUR DEATH DO NOT EDIT OR CHANGE THIS BOOK OR THE MESSAGE CONTAINED WITHIN EITHER THE WORDS OR THEIR NUMBERS FOR ALL IS SACRED",
    "wisdom": "SOME WISDOM THE PRIMES ARE SACRED THE TOTIENT FUNCTION IS SACRED ALL THINGS SHOULD BE ENCRYPTED KNOW THIS",
    "parable": "PARABLE LIKE THE INSTAR TUNNELING TO THE SURFACE WE MUST SHED OUR OWN CIRCUMFERENCES FIND THE DIVINITY WITHIN AND EMERGE",
    "anend": "AN END WITHIN THE DEEP WEB THERE EXISTS A PAGE THAT HASHES TO IT IS THE DUTY OF EVERY PILGRIM TO SEEK OUT THIS PAGE",
    "welcome": "WELCOME WELCOME PILGRIM TO THE GREAT JOURNEY TOWARD THE END OF ALL THINGS IT IS NOT AN EASY TRIP BUT FOR THOSE WHO FIND THEIR WAY HERE IT IS A NECESSARY ONE ALONG THE WAY YOU WILL FIND AN END TO ALL STRUGGLE AND SUFFERING YOUR INNOCENCE YOUR ILLUSIONS YOUR CERTAINTY AND YOUR SELF ALL WILL BE WASHED AWAY",
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    prefix = []
    for s in range(15, 71):
        prefix.extend(idxs_of(s))
    print("unsolved runes", len(prefix))

    hits = []
    tested = 0
    # keyless delta / integrate / adjacent combine
    variants = []
    for name, fn in (
        ("delta_prev0", lambda ct: [(ct[0]) % 29] + [(ct[i] - ct[i - 1]) % 29 for i in range(1, len(ct))]),
        ("delta_add", lambda ct: [(ct[0]) % 29] + [(ct[i] + ct[i - 1]) % 29 for i in range(1, len(ct))]),
        ("cumsum_sub", lambda ct: [(ct[i] - ct[0]) % 29 for i in range(len(ct))]),
        ("alt_sub", lambda ct: [(ct[i] - ct[i - 1]) % 29 if i % 2 else ct[i] % 29 for i in range(len(ct))]),
        ("rev_delta", lambda ct: (lambda r: [(r[0]) % 29] + [(r[i] - r[i - 1]) % 29 for i in range(1, len(r))])(ct[::-1])),
    ):
        variants.append((name, fn))

    for span, ct in (("all", prefix), ("sec0-2", idxs_of(15) + idxs_of(16) + idxs_of(17)), ("p0", idxs_of(15))):
        for name, fn in variants:
            tested += 1
            pt = fn(ct)
            latin = GP.latin_stream(pt)
            sc = score_candidate(pt, latin)
            print(f"delta {span:7s} {name:12s} tri={sc['trigram_per_100']:.2f} ioc={sc['ioc']:.3f} {latin[:50]}")
            if keep(sc, len(pt)):
                hits.append({"kind": "delta", "span": span, "name": name, "head": latin[:80], **sc})

    # skeletons
    pages = {s: word_lens_runes((PAGE_DIR / f"split_{s:03d}.txt").read_text(encoding="utf-8")) for s in range(15, 71)}
    hays = {k: word_lens_latin(v) for k, v in SOLVED_PLAINS.items()}
    # solved-page ciphertext word lengths (equals PT lengths)
    for s in list(range(0, 15)) + [71, 72]:
        p = PAGE_DIR / f"split_{s:03d}.txt"
        if p.exists():
            hays[f"rtkd{s:03d}"] = word_lens_runes(p.read_text(encoding="utf-8"))

    fetch_log = []
    urls = [
        ("wiki_cicada", "https://en.wikipedia.org/wiki/Cicada_3301?action=raw"),
        ("wiki_liber_al", "https://en.wikipedia.org/wiki/Liber_AL_vel_Legis?action=raw"),
        ("wiki_emerald", "https://en.wikipedia.org/wiki/Emerald_Tablet?action=raw"),
        ("wiki_totient", "https://en.wikipedia.org/wiki/Euler%27s_totient_function?action=raw"),
        (
            "gitenberg_alice",
            "https://raw.githubusercontent.com/GITenberg/Alice-s-Adventures-in-Wonderland_11/master/11.txt",
        ),
        (
            "kjv_sample",
            "https://raw.githubusercontent.com/scrollmapper/bible_databases/master/sources/kjv.txt",
        ),
    ]
    for name, url in urls:
        try:
            rec = fetch_url(url, source_id=f"skeleton-{name}", source_family="web")
            if rec.get("access_status") != "OK":
                fetch_log.append({"name": name, "ok": False, "status": rec.get("http_status")})
                continue
            path = CICADA_ROOT / rec["path"]
            raw = path.read_text(encoding="utf-8", errors="replace")
            # cap to keep encode time bounded
            wl = word_lens_latin(raw[:200_000])
            hays[name] = wl
            fetch_log.append({"name": name, "ok": True, "chars": len(raw), "words": len(wl), "sha": rec.get("sha256")})
            print("fetched", name, "words", len(wl))
        except Exception as e:
            fetch_log.append({"name": name, "ok": False, "err": str(e)[:200]})
            print("fetch fail", name, e)

    skel = []
    for s, needle in pages.items():
        if len(needle) < 8:
            continue
        for hid, hay in hays.items():
            best, pos = longest_run(needle, hay)
            if best >= 8:
                rec = {"split": s, "hay": hid, "run": best, "pos": pos, "needle_n": len(needle), "hay_n": len(hay)}
                skel.append(rec)
                print("SKEL", rec)
    print("skeleton keeps>=8", len(skel))

    # LSB of a few JPEGs
    triage = {x["url"].rsplit("/", 1)[-1]: x for x in json.loads(TRIAGE.read_text()) if "unsolved" in x["url"]}
    lsb_hits = []
    for onion in (0, 15, 56):
        path = object_path(triage[f"{onion}.jpg"]["sha256"])
        arr = np.asarray(Image.open(path).convert("RGB"))
        # subsample: every 8th pixel LSB of R
        bits = (arr[::8, ::8, 0] & 1).astype(np.uint8).ravel()
        # pack 5 bits -> 0-31 then %29
        ks = []
        for i in range(0, len(bits) - 4, 5):
            v = 0
            for b in bits[i : i + 5]:
                v = (v << 1) | int(b)
            ks.append(v % 29)
        body = prefix[:900]
        if len(ks) < 40:
            continue
        for rel in ("sub", "add"):
            tested += 1
            if rel == "sub":
                out = [(body[i] - ks[i % len(ks)]) % 29 for i in range(len(body))]
            else:
                out = [(body[i] + ks[i % len(ks)]) % 29 for i in range(len(body))]
            latin = GP.latin_stream(out)
            sc = score_candidate(out, latin)
            print(f"lsb {onion:2d} {rel} nks={len(ks)} tri={sc['trigram_per_100']:.2f} ioc={sc['ioc']:.3f} {latin[:48]}")
            if keep(sc, len(body)):
                lsb_hits.append({"onion": onion, "rel": rel, "head": latin[:80], **sc})
        # also SHA of LSB bitstream
        seed = hashlib.sha256(bits.tobytes()).digest()
        k2 = sha256_ctr(seed, 900)
        tested += 1
        out = [(body[i] - k2[i]) % 29 for i in range(900)]
        latin = GP.latin_stream(out)
        sc = score_candidate(out, latin)
        print(f"lsb {onion:2d} sha-ctr tri={sc['trigram_per_100']:.2f} {latin[:48]}")
        if keep(sc, 900):
            lsb_hits.append({"onion": onion, "rel": "sha-ctr", "head": latin[:80], **sc})

    print("tested", tested, "delta_hits", len(hits), "lsb_hits", len(lsb_hits))
    (OUT / "result.json").write_text(
        json.dumps(
            {
                "unsolved_n": len(prefix),
                "tested": tested,
                "delta_hits": hits,
                "skeleton_keeps": skel,
                "fetch_log": fetch_log,
                "hay_sizes": {k: len(v) for k, v in hays.items()},
                "lsb_hits": lsb_hits,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
