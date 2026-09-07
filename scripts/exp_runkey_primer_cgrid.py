#!/usr/bin/env python3
"""Faust/Alice running-key slide; page-local primers; 15.jpg C-grid under autokey/Porta/Nicodemus."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cicada.acquisition import fetch_url  # noqa: E402
from cicada.liber_primus.ciphers import vigenere_decrypt  # noqa: E402
from cicada.liber_primus.gematria import Gematria, first_n_primes  # noqa: E402
from cicada.paths import ROOT as CICADA_ROOT  # noqa: E402
from cicada.scoring import score_candidate  # noqa: E402

# reuse Porta/autokey/Nicodemus from the previous experiment module path
sys.path.insert(0, str(ROOT / "scripts"))
from exp_autokey_porta_skel import (  # noqa: E402
    autokey_ct,
    autokey_pt,
    beaufort,
    beaufort_autokey_pt,
    interrupt_on_f,
    nicodemus_decrypt,
    porta29,
    progressive,
)

GP = Gematria()
Q = 29
PAGE_DIR = CICADA_ROOT / "corpus/normalized/rtkd_pages"
OUT = CICADA_ROOT / "experiments" / "EXP-LP-RUNKEY-PRIMER-CGRID-001"

GRID = [
    [3258, 3222, 3152, 3038],
    [3278, 3299, 3298, 2838],
    [3288, 3294, 3296, 2472],
    [4516, 1206, 708, 1820],
]


def idxs_of(split: int) -> list[int]:
    return GP.rune_indices((PAGE_DIR / f"split_{split:03d}.txt").read_text(encoding="utf-8"))


def prefix(n: int = 900) -> list[int]:
    out: list[int] = []
    for s in range(15, 71):
        out.extend(idxs_of(s))
        if len(out) >= n:
            break
    return out[:n]


def keep(sc: dict, n: int) -> bool:
    return (
        n >= 80
        and sc["trigram_per_100"] >= 3.5
        and 0.28 <= sc["vowelish_ratio"] <= 0.55
        and sc["ioc"] >= 0.045
    )


def encode_stream(text: str) -> list[int]:
    # Q has no gematria letter; drop it. Other English letters alias (K→C, U→V, Z→S).
    compact = "".join(ch for ch in text.upper() if ch.isalpha() and ch != "Q")
    if not compact:
        return []
    return GP.encode_latin_key(compact)


def ioc_rows(pt: np.ndarray) -> np.ndarray:
    n = pt.shape[1]
    acc = np.zeros(pt.shape[0], dtype=np.int64)
    for q in range(Q):
        c = np.sum(pt == q, axis=1)
        acc += c * (c - 1)
    return acc / (n * (n - 1))


def slide_running_key(ct: list[int], hay: list[int], rel: str, ioc_min: float = 0.048) -> list[dict]:
    if len(hay) < len(ct) + 8:
        return []
    c = np.asarray(ct, dtype=np.int16)
    h = np.asarray(hay, dtype=np.int16)
    n = len(ct)
    nwin = len(h) - n + 1
    # chunk to keep memory bounded
    hits: list[dict] = []
    chunk = 8000
    for start in range(0, nwin, chunk):
        end = min(start + chunk, nwin)
        windows = np.lib.stride_tricks.as_strided(
            h[start : end + n - 1],
            shape=(end - start, n),
            strides=(h.strides[0], h.strides[0]),
        )
        if rel == "sub":
            pt = np.mod(c - windows, Q)
        elif rel == "add":
            pt = np.mod(c + windows, Q)
        else:
            pt = np.mod(windows - c, Q)
        iocs = ioc_rows(pt)
        for j in np.nonzero(iocs >= ioc_min)[0]:
            row = [int(x) for x in pt[j]]
            latin = GP.latin_stream(row)
            sc = score_candidate(row, latin)
            if keep(sc, n):
                hits.append({"pos": int(start + j), "rel": rel, "head": latin[:80], **sc})
    return hits


def c_of_a(vals: list[int]) -> list[int]:
    need = max(vals) + 3
    primes = first_n_primes(need)
    # (A+1)th prime: 1-based A+1 → primes[A] if primes[0] is 2 and A is 0-based offset
    return [abs(3301 - primes[a]) % Q for a in vals]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fetches = []
    hays: dict[str, list[int]] = {}
    for name, url, cap in (
        ("faust", "https://raw.githubusercontent.com/GITenberg/Faust_14591/master/14591.txt", 400000),
        (
            "alice",
            "https://raw.githubusercontent.com/GITenberg/Alice-s-Adventures-in-Wonderland_11/master/11.txt",
            None,
        ),
        (
            "beowulf",
            "https://raw.githubusercontent.com/GITenberg/Beowulf_16328/master/16328-8.txt",
            None,
        ),
        (
            "inferno",
            "https://raw.githubusercontent.com/GITenberg/Divine-Comedy-Longfellow-s-Translation-Hell_1001/master/1001.txt",
            400000,
        ),
    ):
        try:
            rec = fetch_url(url, source_id=f"runkey-{name}", source_family="web")
            if rec.get("access_status") != "OK":
                fetches.append({"name": name, "ok": False, "status": rec.get("http_status")})
                print("fetch fail", name, rec.get("http_status"))
                continue
            raw = (CICADA_ROOT / rec["path"]).read_text(encoding="utf-8", errors="replace")
            if cap:
                raw = raw[:cap]
            ix = encode_stream(raw)
            hays[name] = ix
            fetches.append({"name": name, "ok": True, "runes": len(ix), "sha": rec.get("sha256")})
            print("hay", name, "runes", len(ix))
        except Exception as e:
            fetches.append({"name": name, "ok": False, "err": str(e)[:200]})
            print("fetch fail", name, e)

    pages = {s: idxs_of(s) for s in range(15, 71)}
    targets: list[tuple[str, list[int]]] = [("prefix400", prefix(400))]
    for s, ix in pages.items():
        if len(ix) >= 80:
            targets.append((f"split{s:03d}", ix))

    rk_hits: list[dict] = []
    rk_tested = 0
    for hname, hay in hays.items():
        for tname, ct in targets:
            for rel in ("sub", "add", "beau"):
                rk_tested += 1
                found = slide_running_key(ct, hay, rel)
                print(f"rk {hname:8s} {tname:10s} {rel:4s} windows~{max(0,len(hay)-len(ct)+1)} keeps={len(found)}")
                for hit in found:
                    hit.update({"hay": hname, "span": tname})
                    rk_hits.append(hit)
                    print("KEEP rk", hit)

    # C-grid keys
    row = [n for r in GRID for n in r]
    keys = {
        "A_mod29": [n % Q for n in row],
        "C_mod29": c_of_a(row),
        "A_fib": [n % Q for n in [3299, 3298, 3296, 3294, 3288, 3278, 3258, 3222, 3152, 3038, 2838, 2472, 1820, 708, 1206, 4516]],
    }
    keyed = {
        "autokey_pt": autokey_pt,
        "autokey_ct": autokey_ct,
        "beau_ak": beaufort_autokey_pt,
        "porta29": porta29,
        "nicodemus": nicodemus_decrypt,
        "progressive": progressive,
        "interrupt_f": interrupt_on_f,
        "beaufort": beaufort,
        "vigenere": vigenere_decrypt,
    }
    grid_hits: list[dict] = []
    grid_tested = 0
    gtargets = [("prefix900", prefix(900)), ("sec0-2", pages[15] + pages[16] + pages[17]), ("unsolved_h400", prefix(400))]
    gtargets += [(f"split{s:03d}", ix) for s, ix in pages.items() if len(ix) >= 80]
    for kn, key in keys.items():
        for tname, ct in gtargets:
            for cn, fn in keyed.items():
                grid_tested += 1
                pt = fn(ct, key)
                latin = GP.latin_stream(pt)
                sc = score_candidate(pt, latin)
                if kn == "C_mod29" and cn == "autokey_pt" and tname in {"prefix900", "split015"}:
                    print(f"cgrid {cn:12s} {tname:10s} {kn:8s} tri={sc['trigram_per_100']:.2f} ioc={sc['ioc']:.3f} {latin[:40]}")
                if keep(sc, len(pt)):
                    rec = {"cipher": cn, "span": tname, "key": kn, "head": latin[:80], **sc}
                    grid_hits.append(rec)
                    print("KEEP cgrid", rec)

    # page-local primers
    primer_hits: list[dict] = []
    primer_tested = 0
    for s, ix in pages.items():
        if len(ix) < 90:
            continue
        for k in (4, 5, 6, 7, 8, 11, 12, 17):
            primer = ix[:k]
            body = ix[k:]
            if len(body) < 80:
                continue
            for cn, fn in (
                ("ak_pt", autokey_pt),
                ("ak_ct", autokey_ct),
                ("vig", vigenere_decrypt),
                ("beau", beaufort),
                ("porta", porta29),
            ):
                primer_tested += 1
                pt = fn(body, primer)
                latin = GP.latin_stream(pt)
                sc = score_candidate(pt, latin)
                if keep(sc, len(pt)):
                    rec = {"split": s, "k": k, "cipher": cn, "head": latin[:80], **sc}
                    primer_hits.append(rec)
                    print("KEEP primer", rec)

    print(
        "rk_tested",
        rk_tested,
        "rk_keeps",
        len(rk_hits),
        "grid",
        grid_tested,
        len(grid_hits),
        "primer",
        primer_tested,
        len(primer_hits),
    )
    result = {
        "fetches": fetches,
        "running_key_tested": rk_tested,
        "running_key_keeps": rk_hits,
        "cgrid_tested": grid_tested,
        "cgrid_keeps": grid_hits,
        "primer_tested": primer_tested,
        "primer_keeps": primer_hits,
    }
    (OUT / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("wrote", OUT / "result.json")


if __name__ == "__main__":
    main()
