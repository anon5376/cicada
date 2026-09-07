#!/usr/bin/env python3
"""Skip-aware beam on in-CAS Latin (CLTK) plus Quran-JSON / onion-HTML leftovers.

English keep() rejects Latin. Also flag high Latin function-word density.
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from cicada.db import db_path  # noqa: E402
from cicada.liber_primus.gematria import Gematria  # noqa: E402
from cicada.paths import ROOT as CICADA_ROOT  # noqa: E402
from cicada.scoring import score_candidate  # noqa: E402
from cicada.store import get_bytes  # noqa: E402
from exp_skipaware_marsaglia import idxs_of, prefix  # noqa: E402
from exp_skipaware_sha_ctr import beam_decode, encrypt_reject, keep  # noqa: E402

GP = Gematria()
Q = 29
OUT = CICADA_ROOT / "experiments" / "EXP-LP-SKIPAWARE-LATIN-CAS-001"
LATIN_WORDS = (
    "ET", "IN", "EST", "NON", "AD", "CVM", "PER", "SED", "NEC", "SVT", "SIT",
    "HIC", "NAM", "SIC", "ITA", "PRO", "SVB", "EX", "AB", "DE", "VT", "NE",
    "QVE", "QVI", "QVA", "AVT", "VEL", "IAM", "NEC", "DVM", "SVA",
)


def encode_stream(text: str) -> list[int]:
    compact = "".join(ch for ch in text.upper() if ch.isascii() and ch.isalpha() and ch != "Q")
    return GP.encode_latin_key(compact) if compact else []


def latin_hits(lat: str) -> int:
    return sum(lat.count(w) for w in LATIN_WORDS)


def latin_keep(sc: dict, lat: str, n: int) -> bool:
    if keep(sc, n):
        return True
    hits = latin_hits(lat)
    return n >= 80 and hits >= 12 and sc["ioc"] >= 0.045 and 0.25 <= sc["vowelish_ratio"] <= 0.60


def load_docs() -> dict[str, list[int]]:
    conn = sqlite3.connect(db_path())
    rows = conn.execute(
        "SELECT r.url, r.sha256, b.byte_length FROM retrievals r "
        "JOIN blobs b ON b.sha256 = r.sha256"
    ).fetchall()
    conn.close()
    out = {}
    for url, sha, n in rows:
        if not url:
            continue
        label = None
        if "cltk/lat_text_latin_library" in url and url.endswith(".txt"):
            label = "lat:" + url.rsplit("/", 1)[-1]
        elif "quran-json" in url:
            label = "quran_json"
        elif "onions/" in url and url.endswith("index.html"):
            label = "onion:" + url.split("/onions/")[-1].split("/")[0][:12]
        if not label or label in out:
            continue
        raw = get_bytes(sha)
        if label.startswith("onion:"):
            text = re.sub(r"<[^>]+>", " ", raw.decode("utf-8", "replace"))
        elif label == "quran_json":
            text = re.sub(r"[^A-Za-z]+", " ", raw.decode("utf-8", "replace"))
        else:
            text = raw.decode("utf-8", "replace")
        ix = encode_stream(text)
        if len(ix) < 400:
            continue
        out[label] = ix[:8000]
        print("doc", label, len(ix), flush=True)
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    docs = load_docs()
    first = next(iter(docs.values()))
    plant_pt = GP.encode_latin_key(
        "THEPRIMESARESACREDTHETOTIENTFVNCTIANISSACREDALLTHNGSSHOVLDBEENCRYPTEDAWARNNGBELIEVENOTHNG"
    )
    pks = first[: len(plant_pt) * 4]
    rec = beam_decode(encrypt_reject(plant_pt, pks)[0], pks)
    agree = sum(a == b for a, b in zip(rec, plant_pt)) / len(plant_pt) if rec else 0.0
    plant = {"agree": round(agree, 4), "ok": agree >= 0.85, "n_docs": len(docs)}
    print("plant", plant, flush=True)

    targets = [("prefix400", prefix(400)), ("split015", idxs_of(15))]
    hits = []
    tested = 0
    samples = []
    for name, hay in docs.items():
        for span, ct in targets:
            need = len(ct) * 4
            ks = (hay * (need // len(hay) + 1))[:need]
            tested += 1
            pt = beam_decode(ct, ks)
            lat = GP.latin_stream(pt)
            sc = score_candidate(pt, lat)
            lh = latin_hits(lat)
            row = {"doc": name, "span": span, "latin_fn": lh, "head": lat[:80], **sc}
            if tested <= 4 or (name.startswith("lat:gall1") and span == "prefix400"):
                print(
                    f"beam {name} {span} tri={sc['trigram_per_100']:.2f} latfn={lh} {lat[:32]}",
                    flush=True,
                )
                samples.append(row)
            if latin_keep(sc, lat, len(pt)):
                hits.append(row)
                print("KEEP", row, flush=True)

    print("tested", tested, "keeps", len(hits), flush=True)
    (OUT / "result.json").write_text(
        json.dumps(
            {"plant": plant, "tested": tested, "keeps": hits, "samples": samples, "n_docs": len(docs)},
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
