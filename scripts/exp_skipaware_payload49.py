#!/usr/bin/env python3
"""Skip-aware expansion of the pp49–51 256-byte grid (Dukotah B-05).

Prior work used the blob as a repeating additive key. This expands it with
hash-CTR / HMAC / raw-pad-through-beam. Also covers MD5/SHA-1/SHA-512 CTR
on a short attested seed list (B-04 family leftover vs SHA-256-only).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from cicada.liber_primus.gematria import Gematria  # noqa: E402
from cicada.paths import ROOT as CICADA_ROOT  # noqa: E402
from cicada.scoring import score_candidate  # noqa: E402
from exp_grid_icc_headings import decode60, parse_rtkd_grid  # noqa: E402
from exp_skipaware_marsaglia import idxs_of, pad_bytes, prefix  # noqa: E402
from exp_skipaware_sha_ctr import beam_decode, encrypt_reject, keep  # noqa: E402

GP = Gematria()
Q = 29
OUT = CICADA_ROOT / "experiments" / "EXP-LP-SKIPAWARE-PAYLOAD49-001"
SEEDS = [
    b"CICADA3301",
    b"3301",
    b"DIVINITY",
    b"AN END",
    b"LIBERPRIMUS",
    b"THELOSSOFDIVINITY",
]


def hash_ctr(algo: str, seed: bytes, n: int) -> list[int]:
    hfn = getattr(hashlib, algo)
    out: list[int] = []
    i = 0
    while len(out) < n:
        digest = hfn(seed + i.to_bytes(4, "big")).digest()
        for b in digest:
            out.append(b % Q)
            if len(out) >= n:
                break
        i += 1
    return out


def hmac_ctr(seed: bytes, n: int) -> list[int]:
    out: list[int] = []
    i = 0
    while len(out) < n:
        digest = hmac.new(seed, i.to_bytes(4, "big"), hashlib.sha256).digest()
        for b in digest:
            out.append(b % Q)
            if len(out) >= n:
                break
        i += 1
    return out


def grid_blobs() -> dict[str, bytes]:
    raw = parse_rtkd_grid()
    claimed = list(raw)
    for idx, old, new in ((45, "1L", "1l"), (50, "0L", "0l"), (165, "0l", "0I"), (246, "3i", "3I")):
        if idx < len(claimed) and claimed[idx] == old:
            claimed[idx] = new
    out = {}
    for name, toks in (("rtkd_raw", raw), ("artwaste_4fix", claimed)):
        vals = decode60(toks)
        if len(vals) != 256 or min(vals) < 0 or max(vals) > 255:
            raise SystemExit(f"bad grid {name} n={len(vals)} range={min(vals), max(vals)}")
        out[name] = bytes(vals)
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    blobs = grid_blobs()
    plant_pt = GP.encode_latin_key(
        "THEPRIMESARESACREDTHETOTIENTFVNCTIANISSACREDALLTHNGSSHOVLDBEENCRYPTEDAWARNNGBELIEVENOTHNG"
    )
    pks = hash_ctr("sha256", blobs["rtkd_raw"], len(plant_pt) * 4)
    plant_ct, _ = encrypt_reject(plant_pt, pks)
    rec = beam_decode(plant_ct, pks)
    agree = sum(a == b for a, b in zip(rec, plant_pt)) / len(plant_pt) if rec else 0.0
    plant = {"agree": round(agree, 4), "ok": agree >= 0.95, "n_tokens": 256}
    print("plant", plant, "blob_lens", {k: len(v) for k, v in blobs.items()}, flush=True)

    targets = [("prefix400", prefix(400)), ("split015", idxs_of(15))]
    hits = []
    tested = 0
    samples = []

    for bname, blob in blobs.items():
        for span, ct in targets:
            need = len(ct) * 4
            streams = [
                ("raw_pad", pad_bytes(blob, 0, need)),
                ("sha256_ctr", hash_ctr("sha256", blob, need)),
                ("sha1_ctr", hash_ctr("sha1", blob, need)),
                ("md5_ctr", hash_ctr("md5", blob, need)),
                ("sha512_ctr", hash_ctr("sha512", blob, need)),
                ("hmac_sha256", hmac_ctr(blob, need)),
                ("sha256_ctr_head32", hash_ctr("sha256", blob[:32], need)),
            ]
            try:
                from Crypto.Cipher import AES
                from Crypto.Util import Counter

                key = hashlib.sha256(blob).digest()
                ctr = Counter.new(128, initial_value=0)
                ks = list(AES.new(key, AES.MODE_CTR, counter=ctr).encrypt(b"\x00" * need))
                streams.append(("aes_ctr_zero", [b % Q for b in ks]))
            except Exception:
                pass
            for mode, ks in streams:
                tested += 1
                pt = beam_decode(ct, ks)
                lat = GP.latin_stream(pt)
                sc = score_candidate(pt, lat)
                row = {"blob": bname, "span": span, "mode": mode, "head": lat[:80], **sc}
                if tested <= 3 or (bname == "rtkd_raw" and mode == "sha256_ctr" and span == "prefix400"):
                    print(f"beam {bname} {span} {mode} tri={sc['trigram_per_100']:.2f} {lat[:36]}", flush=True)
                    samples.append(row)
                if keep(sc, len(pt)):
                    hits.append(row)
                    print("KEEP", row, flush=True)

    for algo in ("md5", "sha1", "sha512"):
        for seed in SEEDS:
            for span, ct in targets:
                tested += 1
                pt = beam_decode(ct, hash_ctr(algo, seed, len(ct) * 4))
                lat = GP.latin_stream(pt)
                sc = score_candidate(pt, lat)
                row = {
                    "blob": f"{algo}:{seed.decode()}",
                    "span": span,
                    "mode": f"{algo}_ctr",
                    "head": lat[:80],
                    **sc,
                }
                if keep(sc, len(pt)):
                    hits.append(row)
                    print("KEEP", row, flush=True)

    print("tested", tested, "keeps", len(hits), flush=True)
    (OUT / "result.json").write_text(
        json.dumps({"plant": plant, "tested": tested, "keeps": hits, "samples": samples}, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
