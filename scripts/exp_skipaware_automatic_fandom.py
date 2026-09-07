#!/usr/bin/env python3
"""Skip-aware automatic sequences + fandom Liber Primus wiki pages.

Thue–Morse / paperfold / Fibonacci word / period-doubling were not in this
repo. Fandom how-solved / Liber Primus / 2017-PGP pages are CORE_URLS but
were never used as pads.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from cicada.acquisition import fetch_url  # noqa: E402
from cicada.liber_primus.gematria import Gematria  # noqa: E402
from cicada.paths import ROOT as CICADA_ROOT  # noqa: E402
from cicada.scoring import score_candidate  # noqa: E402
from cicada.store import get_bytes  # noqa: E402
from exp_skipaware_marsaglia import idxs_of, prefix  # noqa: E402
from exp_skipaware_sha_ctr import beam_decode, encrypt_reject, keep  # noqa: E402

GP = Gematria()
Q = 29
OUT = CICADA_ROOT / "experiments" / "EXP-LP-SKIPAWARE-AUTOMATIC-FANDOM-001"
WIKI = (
    ("how_solved", "https://uncovering-cicada.fandom.com/wiki/How_the_solved_pages_of_the_Liber_Primus_were_solved"),
    ("liber_primus", "https://uncovering-cicada.fandom.com/wiki/Liber_Primus"),
    ("pgp_2017", "https://uncovering-cicada.fandom.com/wiki/PGP_Signed_Message_April_2017"),
)


def encode_stream(text: str) -> list[int]:
    compact = "".join(ch for ch in text.upper() if ch.isascii() and ch.isalpha() and ch != "Q")
    return GP.encode_latin_key(compact) if compact else []


def thue_morse(n: int) -> list[int]:
    return [bin(i).count("1") % Q for i in range(n)]


def thue_morse_bit(n: int) -> list[int]:
    return [((i % Q) + (bin(i).count("1") & 1)) % Q for i in range(n)]


def paperfold(n: int) -> list[int]:
    out = []
    i = 0
    while len(out) < n:
        i += 1
        x = i
        while x % 2 == 0:
            x //= 2
        out.append((1 if (x % 4 == 1) else 0))
    return [((k % Q) + out[k]) % Q for k in range(n)]


def fib_word(n: int) -> list[int]:
    a, b = [0], [0, 1]
    while len(b) < n:
        a, b = b, b + a
    return [((i % Q) + b[i]) % Q for i in range(n)]


def period_doubling(n: int) -> list[int]:
    s = [0]
    while len(s) < n:
        nxt = []
        for b in s:
            nxt.extend([0, 1] if b == 0 else [0, 0])
        s = nxt
    return [((i % Q) + s[i]) % Q for i in range(n)]


def rudin_shapiro(n: int) -> list[int]:
    out = []
    for i in range(n):
        bits = bin(i)[2:]
        ones = sum(1 for a, b in zip(bits, bits[1:]) if a == b == "1")
        out.append(((i % Q) + (ones & 1)) % Q)
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    plant_pt = GP.encode_latin_key(
        "THEPRIMESARESACREDTHETOTIENTFVNCTIANISSACREDALLTHNGSSHOVLDBEENCRYPTEDAWARNNGBELIEVENOTHNG"
    )
    pks = thue_morse(len(plant_pt) * 4)
    rec = beam_decode(encrypt_reject(plant_pt, pks)[0], pks)
    agree = sum(a == b for a, b in zip(rec, plant_pt)) / len(plant_pt) if rec else 0.0
    plant = {"agree": round(agree, 4), "ok": agree >= 0.95, "family": "thue_morse"}
    print("plant", plant, flush=True)

    targets = [("prefix400", prefix(400)), ("split015", idxs_of(15))]
    streams = {
        "thue_morse": thue_morse,
        "thue_morse_bit": thue_morse_bit,
        "paperfold": paperfold,
        "fib_word": fib_word,
        "period_doubling": period_doubling,
        "rudin_shapiro": rudin_shapiro,
    }
    hits = []
    tested = 0
    samples = []
    fetch_recs = []
    for name, fn in streams.items():
        for span, ct in targets:
            tested += 1
            pt = beam_decode(ct, fn(len(ct) * 4))
            lat = GP.latin_stream(pt)
            sc = score_candidate(pt, lat)
            row = {"src": name, "span": span, "mode": "automatic", "head": lat[:80], **sc}
            if tested <= 4:
                print(f"beam {name} {span} tri={sc['trigram_per_100']:.2f} {lat[:36]}", flush=True)
                samples.append(row)
            if keep(sc, len(pt)):
                hits.append(row)
                print("KEEP", row, flush=True)

    for name, url in WIKI:
        rec = fetch_url(url, source_id=f"fandom-{name}", source_family="community-wiki")
        fetch_recs.append({"name": name, "url": url, "status": rec.get("access_status"), "sha256": rec.get("sha256")})
        print("fetch", name, rec.get("access_status"), rec.get("http_status"), rec.get("sha256", "")[:16], flush=True)
        if rec.get("access_status") != "OK" or not rec.get("sha256"):
            continue
        hay = encode_stream(get_bytes(rec["sha256"]).decode("utf-8", "replace"))
        print("runes", name, len(hay), flush=True)
        if len(hay) < 200:
            continue
        for span, ct in targets:
            need = len(ct) * 4
            ks = (hay * (need // len(hay) + 1))[:need]
            tested += 1
            pt = beam_decode(ct, ks)
            lat = GP.latin_stream(pt)
            sc = score_candidate(pt, lat)
            row = {"src": name, "span": span, "mode": "fandom_pad", "head": lat[:80], **sc}
            if keep(sc, len(pt)):
                hits.append(row)
                print("KEEP", row, flush=True)

    print("tested", tested, "keeps", len(hits), flush=True)
    (OUT / "result.json").write_text(
        json.dumps(
            {"plant": plant, "tested": tested, "keeps": hits, "samples": samples, "fetches": fetch_recs},
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
