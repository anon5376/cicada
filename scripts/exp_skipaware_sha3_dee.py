#!/usr/bin/env python3
"""SHA3-256 / BLAKE2s CTR skip-aware + Dee Hieroglyphic Monad pad.

SHA-256 CTR is closed. SHA3/BLAKE2 were never a keystream. Dee Monad had no
text file on the previous IA item; archive.org/download/monas-hieroglyphica
now has DjVuTXT.
"""
from __future__ import annotations

import hashlib
import json
import re
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
from exp_skipaware_rel_inverses import beam_rel, encrypt_reject  # noqa: E402
from exp_skipaware_sha_ctr import beam_decode, encrypt_reject as enc_sub, keep  # noqa: E402

GP = Gematria()
Q = 29
OUT = CICADA_ROOT / "experiments" / "EXP-LP-SKIPAWARE-SHA3-DEE-001"
SEEDS = [b"CICADA3301", b"3301", b"DIVINITY", b"AN END", b"LIBERPRIMUS", b"MONAS", b"HIEROGLYPHIC"]
DEE_URL = "https://archive.org/download/monas-hieroglyphica/MONAS%20HIEROGLYPHICA_djvu.txt"


def ctr(name: str, seed: bytes, n: int) -> list[int]:
    out: list[int] = []
    i = 0
    while len(out) < n:
        block = seed + i.to_bytes(4, "big")
        if name == "sha3":
            d = hashlib.sha3_256(block).digest()
        else:
            d = hashlib.blake2s(block).digest()
        for b in d:
            out.append(b % Q)
            if len(out) >= n:
                break
        i += 1
    return out


def latin_pad(text: str) -> list[int]:
    compact = re.sub(r"[^A-Za-z]", "", text.upper()).replace("Q", "C")
    out: list[int] = []
    i = 0
    while i < len(compact):
        # greedy TH/NG/EO handled by encode_latin_key on chunks
        chunk = compact[i:i + 80]
        try:
            out.extend(GP.encode_latin_key(chunk))
            i += 80
        except Exception:
            i += 1
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rec = fetch_url(DEE_URL)
    dee_raw = get_bytes(rec["sha256"]).decode("utf-8", "replace") if rec.get("sha256") else ""
    dee_pad = latin_pad(dee_raw)
    print("dee", rec.get("http_status"), "chars", len(dee_raw), "runes", len(dee_pad), flush=True)

    plant_pt = GP.encode_latin_key(
        "THEPRIMESARESACREDTHETOTIENTFVNCTIANISSACREDALLTHNGSSHOVLDBEENCRYPTEDAWARNNGBELIEVENOTHNG"
    )
    plants = {}
    for name in ("sha3", "blake2s"):
        ks = ctr(name, b"CICADA3301", len(plant_pt) * 4)
        ct, _ = enc_sub(plant_pt, ks)
        recp = beam_decode(ct, ks)
        agree = sum(a == b for a, b in zip(recp, plant_pt)) / len(plant_pt) if recp else 0.0
        plants[name] = {"agree": round(agree, 4), "ok": agree >= 0.95}
        print("plant", name, plants[name], flush=True)
    if len(dee_pad) >= 80:
        ks = (dee_pad * 4)[: len(plant_pt) * 4]
        ct, _ = enc_sub(plant_pt, ks)
        recp = beam_decode(ct, ks)
        agree = sum(a == b for a, b in zip(recp, plant_pt)) / len(plant_pt) if recp else 0.0
        plants["dee_pad"] = {"agree": round(agree, 4), "ok": agree >= 0.85, "pad_runes": len(dee_pad)}
        print("plant dee_pad", plants["dee_pad"], flush=True)

    if not all(plants[k]["ok"] for k in ("sha3", "blake2s")):
        (OUT / "result.json").write_text(json.dumps({
            "experiment": "EXP-LP-SKIPAWARE-SHA3-DEE-001", "plants": plants,
            "verified_new_unsolved_runes": 0, "aborted": "hash CTR plant failed",
        }, indent=2) + "\n")
        return

    targets = [("prefix400", prefix(400)), ("split015", idxs_of(15))]
    hits, tested, samples = [], 0, []
    streams = []
    for sd in SEEDS:
        streams.append((f"sha3:{sd.decode()}", ctr("sha3", sd, 2500)))
        streams.append((f"blake2s:{sd.decode()}", ctr("blake2s", sd, 2500)))
    if len(dee_pad) >= 80:
        streams.append(("dee_monas", dee_pad * 8))

    for sname, ks0 in streams:
        rels = ("sub",) if sname.startswith("sha3:") or sname.startswith("blake2s:") else ("sub", "add", "beau")
        for rel in rels:
            for span, ct in targets:
                tested += 1
                ks = ks0[: len(ct) * 4]
                if rel == "sub":
                    pt = beam_decode(ct, ks)
                else:
                    pt = beam_rel(ct, ks, rel)
                lat = GP.latin_stream(pt)
                sc = score_candidate(pt, lat)
                row = {"stream": sname, "rel": rel, "span": span, "head": lat[:80], **sc}
                if tested <= 6:
                    print(f"{sname} {rel} {span} tri={sc['trigram_per_100']:.2f} {lat[:36]}", flush=True)
                    samples.append(row)
                if keep(sc, len(pt)):
                    hits.append(row)
                    print("KEEP", row, flush=True)

    result = {
        "experiment": "EXP-LP-SKIPAWARE-SHA3-DEE-001",
        "family": "skip-aware SHA3-256/BLAKE2s CTR + Dee Monad DjVuTXT pad",
        "dee_url": DEE_URL,
        "dee_http": rec.get("http_status"),
        "dee_chars": len(dee_raw),
        "dee_runes": len(dee_pad),
        "plants": plants,
        "tested": tested,
        "keeps": hits,
        "samples": samples,
        "verified_new_unsolved_runes": 0,
    }
    (OUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print("tested", tested, "keeps", len(hits))


if __name__ == "__main__":
    main()
