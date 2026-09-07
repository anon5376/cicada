#!/usr/bin/env python3
"""Autokey / Beaufort / Porta-29 / Nicodemus / word-reset Vigenere; unused-text skeletons.

Quixote 10-word hit on split 56 is recorded here as a chance-length alignment
(keystream IoC ~0.033, no period, totient agree ~0.05). Not a decrypt.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cicada.acquisition import fetch_url  # noqa: E402
from cicada.liber_primus.ciphers import vigenere_decrypt  # noqa: E402
from cicada.liber_primus.gematria import Gematria, first_n_primes  # noqa: E402
from cicada.paths import ROOT as CICADA_ROOT  # noqa: E402
from cicada.scoring import ioc, score_candidate  # noqa: E402

GP = Gematria()
Q = 29
PAGE_DIR = CICADA_ROOT / "corpus/normalized/rtkd_pages"
OUT = CICADA_ROOT / "experiments" / "EXP-LP-AUTOKEY-PORTA-SKEL-001"
CAS = CICADA_ROOT / "corpus/objects/sha256"

KEY_WORDS = [
    "DIVINITY",
    "FIRFUMFERENFE",
    "INSTAR",
    "CIRCUMFERENCE",
    "PILGRIM",
    "PRIMES",
    "CICADA",
    "LIBERPRIMUS",
    "ANEND",
    "PARABLE",
    "WELCOME",
    "AWARNING",
    "SOMEWISDOM",
    "KNOWTHIS",
    "THELOSSOFDIVINITY",
    "PRESERVATION",
    "ADHERENCE",
    "CONSUMPTION",
    "KOAN",
    "ENLIGHTENMENT",
    "DEEPWEB",
    "TOTIENT",
    "PHI",
    "3301",
]


def idxs_of(split: int) -> list[int]:
    return GP.rune_indices((PAGE_DIR / f"split_{split:03d}.txt").read_text(encoding="utf-8"))


def page_words(split: int) -> list[list[int]]:
    text = (PAGE_DIR / f"split_{split:03d}.txt").read_text(encoding="utf-8")
    words: list[list[int]] = []
    cur: list[int] = []
    for tok in GP.tokenize(text):
        if tok.kind == "rune" and tok.index is not None:
            cur.append(tok.index)
        elif tok.kind in {"sep", "punct", "layout"} and cur:
            words.append(cur)
            cur = []
    if cur:
        words.append(cur)
    return words


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


def beaufort(ct: list[int], key: list[int]) -> list[int]:
    return [(key[i % len(key)] - x) % Q for i, x in enumerate(ct)]


def autokey_pt(ct: list[int], primer: list[int]) -> list[int]:
    out: list[int] = []
    key = list(primer)
    for i, x in enumerate(ct):
        k = key[i] if i < len(key) else out[i - len(primer)]
        pt = (x - k) % Q
        out.append(pt)
    return out


def autokey_ct(ct: list[int], primer: list[int]) -> list[int]:
    out: list[int] = []
    for i, x in enumerate(ct):
        k = primer[i] if i < len(primer) else ct[i - len(primer)]
        out.append((x - k) % Q)
    return out


def beaufort_autokey_pt(ct: list[int], primer: list[int]) -> list[int]:
    out: list[int] = []
    for i, x in enumerate(ct):
        k = primer[i] if i < len(primer) else out[i - len(primer)]
        out.append((k - x) % Q)
    return out


def progressive(ct: list[int], key: list[int]) -> list[int]:
    return [(x - (key[i % len(key)] + i)) % Q for i, x in enumerate(ct)]


def trithemius(ct: list[int], off: int) -> list[int]:
    return [(x - (i + off)) % Q for i, x in enumerate(ct)]


def porta29(ct: list[int], key: list[int]) -> list[int]:
    """Involutive 14+14 Porta analogue; index 28 is fixed."""
    out: list[int] = []
    for i, x in enumerate(ct):
        k = key[i % len(key)] % 14
        x = x % Q
        if x == 28:
            out.append(28)
            continue
        if x < 14:
            out.append(14 + (x + k) % 14)
        else:
            out.append((x - 14 - k) % 14)
    return out


def nicodemus_decrypt(ct: list[int], key: list[int]) -> list[int]:
    n = len(key)
    if n < 2:
        return vigenere_decrypt(ct, key)
    L = len(ct)
    rows = (L + n - 1) // n
    rem = L % n
    col_len = [rows if (rem == 0 or i < rem) else rows - 1 for i in range(n)]
    order = sorted(range(n), key=lambda i: (key[i], i))
    cols: list[list[int]] = [[] for _ in range(n)]
    pos = 0
    for col in order:
        ln = col_len[col]
        cols[col] = ct[pos : pos + ln]
        pos += ln
    vig: list[int] = []
    for r in range(rows):
        for c in range(n):
            if r < len(cols[c]):
                vig.append(cols[c][r])
    return vigenere_decrypt(vig, key)


def word_reset_vig(words: list[list[int]], key: list[int]) -> list[int]:
    out: list[int] = []
    for w in words:
        out.extend(vigenere_decrypt(w, key))
    return out


def word_reset_autokey(words: list[list[int]], primer: list[int]) -> list[int]:
    out: list[int] = []
    for w in words:
        out.extend(autokey_pt(w, primer))
    return out


def interrupt_on_f(ct: list[int], key: list[int]) -> list[int]:
    out: list[int] = []
    k = 0
    for x in ct:
        if x % Q == 0:
            out.append(0)
            k = 0
            continue
        out.append((x - key[k % len(key)]) % Q)
        k += 1
    return out


def word_lens_runes(text: str) -> list[int]:
    out: list[int] = []
    n = 0
    for tok in GP.tokenize(text):
        if tok.kind == "rune":
            n += 1
        elif tok.kind in {"sep", "punct", "layout"} and n:
            out.append(n)
            n = 0
    if n:
        out.append(n)
    return out


def word_lens_latin(text: str) -> list[int]:
    out: list[int] = []
    for w in re.findall(r"[A-Za-z]+", text):
        try:
            ix = GP.encode_latin_key(w.upper())
        except ValueError:
            continue
        if ix:
            out.append(len(ix))
    return out


def longest_run(needle: list[int], hay: list[int]) -> tuple[int, int]:
    best, pos = 0, -1
    if len(needle) < 4 or len(hay) < 4:
        return 0, -1
    for i in range(len(hay) - 3):
        r = 0
        while r < len(needle) and i + r < len(hay) and needle[r] == hay[i + r]:
            r += 1
        if r > best:
            best, pos = r, i
            if best == len(needle):
                break
    return best, pos


def find_cas(pref: str) -> Path | None:
    xs = list((CAS / pref[:2]).glob(pref + "*"))
    return xs[0] if xs else None


def quixote_skeptic() -> dict:
    qx = find_cas("69ef241e632ef4fb")
    if not qx:
        return {"ok": False, "reason": "quixote missing"}
    raw = qx.read_text(encoding="utf-8", errors="replace")[:350000]
    surv: list[tuple[str, list[int]]] = []
    for w in re.findall(r"[A-Za-z]+", raw):
        try:
            ix = GP.encode_latin_key(w.upper())
        except ValueError:
            continue
        if ix:
            surv.append((w.upper(), ix))
    win = surv[50184:50194]
    words = page_words(56)
    ct: list[int] = []
    pt: list[int] = []
    labels = []
    for pw, (w, ix) in zip(words[:10], win):
        if len(pw) != len(ix):
            return {"ok": False, "reason": "length mismatch", "w": w}
        ct.extend(pw)
        pt.extend(ix)
        labels.append(w)
    ks = [(c - p) % Q for c, p in zip(ct, pt)]
    primes = first_n_primes(len(ks) + 2)
    tot = [(p - 1) % Q for p in primes[: len(ks)]]
    tot_agree = sum(a == b for a, b in zip(ks, tot)) / len(ks)
    period = {}
    for p in range(1, 13):
        period[str(p)] = round(
            sum(ks[i] == ks[i - p] for i in range(p, len(ks))) / (len(ks) - p), 3
        )
    return {
        "ok": True,
        "phrase": " ".join(labels),
        "n_runes": len(ks),
        "ks_ioc": round(ioc(ks), 4),
        "period_agree": period,
        "totient_agree": round(tot_agree, 3),
        "verdict": "chance-length alignment; unstructured keystream; not a decrypt",
    }


def consider(hits: list, cipher: str, span: str, key: str, pt: list[int]) -> dict:
    latin = GP.latin_stream(pt)
    sc = score_candidate(pt, latin)
    rec = {"cipher": cipher, "span": span, "key": key, "n": len(pt), "head": latin[:80], **sc}
    if keep(sc, len(pt)):
        hits.append(rec)
        print(f"KEEP {cipher:18s} {span:10s} {key:20s} tri={sc['trigram_per_100']:.2f} ioc={sc['ioc']:.3f} {latin[:48]}")
    return rec


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    keys: list[tuple[str, list[int]]] = []
    for w in KEY_WORDS:
        try:
            enc = GP.encode_latin_key(w)
        except ValueError:
            continue
        if enc:
            keys.append((w, enc))
    keys.append(("seq", list(range(29))))

    streams: list[tuple[str, list[int]]] = [
        ("prefix900", prefix(900)),
        ("sec0-2", idxs_of(15) + idxs_of(16) + idxs_of(17)),
    ]
    all_unsolved: list[int] = []
    page_streams: list[tuple[str, list[int]]] = []
    for s in range(15, 71):
        ix = idxs_of(s)
        all_unsolved.extend(ix)
        if len(ix) >= 80:
            page_streams.append((f"split{s:03d}", ix))
    streams.append(("unsolved", all_unsolved))

    hits: list[dict] = []
    tested = 0
    sample: list[dict] = []

    def run_stream(label: str, ct: list[int], keyed_only: bool = False) -> None:
        nonlocal tested
        if not keyed_only:
            for off in (0, 1, 3301 % 29):
                tested += 1
                rec = consider(hits, f"trithemius{off}", label, "-", trithemius(ct, off))
                if off == 0:
                    sample.append(rec)
        for kn, key in keys:
            for name, fn in (
                ("beaufort", beaufort),
                ("autokey_pt", autokey_pt),
                ("autokey_ct", autokey_ct),
                ("beau_ak_pt", beaufort_autokey_pt),
                ("progressive", progressive),
                ("porta29", porta29),
                ("nicodemus", nicodemus_decrypt),
                ("interrupt_f", interrupt_on_f),
            ):
                tested += 1
                rec = consider(hits, name, label, kn, fn(ct, key))
                if kn == "DIVINITY" and name in {"beaufort", "autokey_pt", "porta29", "nicodemus"}:
                    print(
                        f"{name:12s} {label:10s} {kn:16s} tri={rec['trigram_per_100']:.2f} ioc={rec['ioc']:.3f} {rec['head'][:40]}"
                    )
                    sample.append(rec)

    for label, ct in streams:
        run_stream(label, ct)
    # pages: keyed families only (trithemius already covered on concat)
    for label, ct in page_streams:
        run_stream(label, ct, keyed_only=True)

    # word-reset needs page word lists
    for s in range(15, 71):
        words = page_words(s)
        if sum(len(w) for w in words) < 80:
            continue
        label = f"split{s:03d}"
        for kn, key in keys:
            tested += 1
            consider(hits, "word_reset_vig", label, kn, word_reset_vig(words, key))
            tested += 1
            consider(hits, "word_reset_ak", label, kn, word_reset_autokey(words, key))

    print("cipher tested", tested, "keeps", len(hits))

    qx = quixote_skeptic()
    print("quixote skeptic", qx.get("verdict"), qx.get("phrase"), "ks_ioc", qx.get("ks_ioc"))

    # unused public texts via allowed hosts
    fetch_log = []
    hays: dict[str, list[int]] = {}
    urls = [
        ("beowulf", "https://raw.githubusercontent.com/GITenberg/Beowulf_16328/master/16328.txt"),
        ("divine_comedy", "https://raw.githubusercontent.com/GITenberg/The-Divine-Comedy-of-Dante-Alighieri_8800/master/8800.txt"),
        ("faust", "https://raw.githubusercontent.com/GITenberg/Faust_14591/master/14591.txt"),
        ("mormon", "https://raw.githubusercontent.com/GITenberg/The-Book-of-Mormon_17/master/17.txt"),
        ("tao", "https://en.wikipedia.org/wiki/Tao_Te_Ching?action=raw"),
        ("nag_hammadi", "https://en.wikipedia.org/wiki/Nag_Hammadi_library?action=raw"),
    ]
    for name, url in urls:
        try:
            rec = fetch_url(url, source_id=f"skeleton-{name}", source_family="web")
            if rec.get("access_status") != "OK":
                fetch_log.append({"name": name, "ok": False, "status": rec.get("http_status")})
                print("fetch fail", name, rec.get("http_status"))
                continue
            path = CICADA_ROOT / rec["path"]
            raw = path.read_text(encoding="utf-8", errors="replace")
            cap = raw if name in {"tao", "nag_hammadi"} else raw[:400000]
            wl = word_lens_latin(cap)
            hays[name] = wl
            fetch_log.append(
                {"name": name, "ok": True, "chars": len(raw), "words": len(wl), "sha": rec.get("sha256")}
            )
            print("fetched", name, "words", len(wl))
        except Exception as e:
            fetch_log.append({"name": name, "ok": False, "err": str(e)[:200]})
            print("fetch fail", name, e)

    pages = {
        s: word_lens_runes((PAGE_DIR / f"split_{s:03d}.txt").read_text(encoding="utf-8"))
        for s in range(15, 71)
    }
    skel_top: list[dict] = []
    skel_keeps: list[dict] = []
    for s, needle in pages.items():
        if len(needle) < 8:
            continue
        for hname, hay in hays.items():
            run, pos = longest_run(needle, hay)
            rec = {"run": run, "split": s, "hay": hname, "pos": pos, "needle_n": len(needle)}
            skel_top.append(rec)
            if run >= 10:
                skel_keeps.append(rec)
                print("skel", rec)
    skel_top.sort(key=lambda r: (-r["run"], r["split"]))
    print("skel max", skel_top[0] if skel_top else None)

    result = {
        "cipher_tested": tested,
        "cipher_keeps": hits,
        "sample": [
            {k: r[k] for k in ("cipher", "span", "key", "trigram_per_100", "ioc", "head") if k in r}
            for r in sample[:24]
        ],
        "quixote_skeptic": qx,
        "fetch_log": fetch_log,
        "skel_keeps": skel_keeps,
        "skel_top": skel_top[:20],
        "skel_max_run": skel_top[0]["run"] if skel_top else 0,
    }
    (OUT / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("wrote", OUT / "result.json")


if __name__ == "__main__":
    main()
