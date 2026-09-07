#!/usr/bin/env python3
"""Use newly fetched signed 2014 hash-block (and other message bodies)
as pads / CTR seeds against unsolved runes.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cicada.liber_primus.ciphers import vigenere_decrypt  # noqa: E402
from cicada.liber_primus.gematria import Gematria  # noqa: E402
from cicada.paths import ROOT as CICADA_ROOT  # noqa: E402
from cicada.pgp import inspect_key, verify_clearsigned  # noqa: E402
from cicada.scoring import score_candidate  # noqa: E402

GP = Gematria()
PAGE_DIR = CICADA_ROOT / "corpus/normalized/rtkd_pages"
OUT = CICADA_ROOT / "experiments" / "EXP-LP-PGP-HASHBLOCK-001"
KEY = CICADA_ROOT / "corpus/objects/sha256/ce/ce6c44a4c3daf6d5b3691f8894ddb59b10ab58514ce1a2e692caf9b86af7142a"


def sha256_ctr(seed: bytes, n: int) -> list[int]:
    out = []
    i = 0
    while len(out) < n:
        d = hashlib.sha256(seed + i.to_bytes(4, "big")).digest()
        for b in d:
            out.append(b % 29)
            if len(out) >= n:
                break
        i += 1
    return out


def body_and_hex(path: Path) -> tuple[str, bytes]:
    raw = path.read_text(encoding="utf-8", errors="replace")
    m = re.search(
        r"-----BEGIN PGP SIGNED MESSAGE-----\nHash: [^\n]+\n\n(.*)\n-----BEGIN PGP SIGNATURE-----",
        raw,
        re.S,
    )
    body = m.group(1) if m else raw
    hexchars = re.sub(r"[^0-9a-fA-F]", "", body)
    blob = b""
    if len(hexchars) >= 16 and len(hexchars) % 2 == 0:
        try:
            blob = bytes.fromhex(hexchars)
        except ValueError:
            blob = b""
    return body, blob


def idxs_flat() -> list[int]:
    flat = []
    for s in range(15, 71):
        flat.extend(GP.rune_indices((PAGE_DIR / f"split_{s:03d}.txt").read_text(encoding="utf-8")))
    return flat


def keep(sc, n):
    return n >= 80 and sc["trigram_per_100"] >= 3.5 and 0.28 <= sc["vowelish_ratio"] <= 0.55 and sc["ioc"] >= 0.045


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    key_bytes = Path(
        str(CICADA_ROOT / "corpus/objects/sha256/6d") 
    )
    # find key by listing
    key_path = None
    for p in (CICADA_ROOT / "corpus/objects/sha256").glob("*/*"):
        if p.is_file() and "BEGIN PGP PUBLIC KEY" in p.read_text(encoding="utf-8", errors="ignore")[:80]:
            key_path = p
            break
    # known announcement sha
    cand = CICADA_ROOT / "corpus/objects/sha256/ce/ce6c44a4c3daf6d5b3691f8894ddb59b10ab58514ce1a2e692caf9b86af7142a"
    # that's a message not the key. search
    key_bytes = None
    for p in (CICADA_ROOT / "corpus/objects/sha256").rglob("*"):
        if not p.is_file():
            continue
        t = p.read_bytes()[:40]
        if t.startswith(b"-----BEGIN PGP PUBLIC KEY"):
            key_bytes = p.read_bytes()
            print("key", p)
            break
    files = {
        "hashblock": CICADA_ROOT / "corpus/objects/sha256/2e/2efba5e2283fa16592bedb7c339223bf2db94f07cf2d42188684aa393c12d180",
        "onion5": CICADA_ROOT / "corpus/objects/sha256/55/55904a90db0b3fb1af059097617ee5d411867c7a940a3f978bf56fe875e82d18",
        "welcome": CICADA_ROOT / "corpus/objects/sha256/d5/d5473236dee152c7744f561e5ace95908876ec01d43467c28af1b0c1aa14cc54",
        "final2014": CICADA_ROOT / "corpus/objects/sha256/a4/a48a4753cc12fd2d5110c50765a4b58294077a0af64f678c14bdd773451ef71e",
        "pp2015": CICADA_ROOT / "corpus/objects/sha256/3e/3e9b0ddcfaed0b76f83f7fc491eece21052ebf8c26402f086a96c491ab9d0703",
    }
    verifs = {}
    if key_bytes:
        for name, path in files.items():
            if path.exists():
                verifs[name] = verify_clearsigned(path.read_bytes(), key_bytes)
                print("verify", name, verifs[name].get("status"), verifs[name].get("fingerprint"))

    flat = idxs_flat()
    prefix = flat[:900]
    hits = []
    tested = 0
    meta = {}
    for name, path in files.items():
        if not path.exists():
            continue
        body, blob = body_and_hex(path)
        meta[name] = {
            "body_len": len(body),
            "hex_bytes": len(blob),
            "body_head": body[:120].replace("\n", " "),
        }
        print(name, "body", len(body), "hexbytes", len(blob), "head", body[:80].replace("\n", " "))
        seeds = {"ascii": hashlib.sha256(body.encode()).digest()}
        if blob:
            seeds["hexblob"] = blob[:64] if len(blob) >= 32 else hashlib.sha256(blob).digest()
            seeds["hex_sha"] = hashlib.sha256(blob).digest()
            key29 = [b % 29 for b in blob]
            if len(key29) >= 8:
                for rel, out in (
                    ("sub", vigenere_decrypt(prefix, key29)),
                    ("add", [(prefix[i] + key29[i % len(key29)]) % 29 for i in range(len(prefix))]),
                ):
                    tested += 1
                    latin = GP.latin_stream(out)
                    sc = score_candidate(out, latin)
                    print(f"  repeat {name} {rel} nkey={len(key29)} tri={sc['trigram_per_100']:.2f} ioc={sc['ioc']:.3f} {latin[:50]}")
                    if keep(sc, len(prefix)):
                        hits.append({"src": name, "kind": "repeat", "rel": rel, "head": latin[:80], **sc})
            # OTP-style: first min(len,900) bytes
            n = min(len(blob), len(prefix))
            ks = [blob[i] % 29 for i in range(n)]
            out = [(prefix[i] - ks[i]) % 29 for i in range(n)]
            tested += 1
            latin = GP.latin_stream(out)
            sc = score_candidate(out, latin)
            print(f"  otp    {name} n={n} tri={sc['trigram_per_100']:.2f} {latin[:50]}")
            if keep(sc, n) or sc["trigram_per_100"] >= 3.2:
                hits.append({"src": name, "kind": "otp_prefix", "head": latin[:80], **sc})
        for sn, seed in seeds.items():
            ks = sha256_ctr(seed, len(prefix))
            for rel in ("sub",):
                tested += 1
                out = [(prefix[i] - ks[i]) % 29 for i in range(len(prefix))]
                latin = GP.latin_stream(out)
                sc = score_candidate(out, latin)
                print(f"  ctr    {name}/{sn} tri={sc['trigram_per_100']:.2f} {latin[:50]}")
                if keep(sc, len(prefix)):
                    hits.append({"src": f"{name}/{sn}", "kind": "ctr", "head": latin[:80], **sc})

    (OUT / "result.json").write_text(
        json.dumps(
            {
                "meta": meta,
                "verifs": {k: {kk: vv for kk, vv in v.items() if kk in ("status", "fingerprint", "primary_fingerprint", "result")} for k, v in verifs.items()},
                "tested": tested,
                "hits": hits,
            },
            indent=2,
            default=str,
        )
        + "\n",
        encoding="utf-8",
    )
    print("tested", tested, "hits", len(hits))


if __name__ == "__main__":
    main()
