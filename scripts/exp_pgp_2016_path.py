#!/usr/bin/env python3
"""2016 iBotPeaches 'path lies empty' clearsigned body — not in prior ingest.

krisyotam pgp/messages has no 2016 file. SKIPAWARE-PGP-BODIES only covered
stored bodies. Verify 7A35090F, then skip-aware pad / SHA-CTR / new phrases.
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

from cicada import db, pgp, store  # noqa: E402
from cicada.acquisition import fetch_url  # noqa: E402
from cicada.liber_primus.gematria import Gematria  # noqa: E402
from cicada.paths import ROOT as CICADA_ROOT  # noqa: E402
from cicada.scoring import score_candidate  # noqa: E402
from exp_skipaware_sha_ctr import beam_decode, encrypt_reject, idxs_of, keep, prefix, sha256_ctr  # noqa: E402

GP = Gematria()
Q = 29
OUT = CICADA_ROOT / "experiments" / "EXP-LP-PGP-2016-PATH-001"
URL = "https://raw.githubusercontent.com/iBotPeaches/cicada_3301/master/messages/2016/hello-the-path-lies-empty.asc"
KRIS = "https://raw.githubusercontent.com/krisyotam/cicada3301/main/tools/solvers/ibotpeaches/messages/2016/hello-the-path-lies-empty.asc"
KEY_SHA = "6e397c5c6ceeeb4da08535db74874989f193c914b8d2d87972dd282b24ea809f"
PHRASES = (
    "EPIPHANY",
    "THEPATHLIESEMPTY",
    "EPIPHANYSEEKSTHEDEVOTED",
    "LIBERPRIMVSISTHEWAY",
    "ITSWORDSARETHEMAP",
    "THEIRMEANINGISTHEROAD",
    "THEIRNVMBERSARETHEDIRECTION",
    "SEEKANDYOVWILLBEFOVND",
)


def encode_stream(text: str) -> list[int]:
    compact = "".join(ch for ch in text.upper() if ch.isascii() and ch.isalpha() and ch != "Q")
    return GP.encode_latin_key(compact) if compact else []


def apply_p(c, k, rel):
    if rel == "sub":
        return (c - k) % Q
    if rel == "add":
        return (c + k) % Q
    return (k - c) % Q


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    db.init_db()
    fetched = fetch_url(URL, source_family="github")
    raw = store.get_bytes(fetched["sha256"]) if fetched.get("sha256") else b""
    kris = None
    try:
        kris = fetch_url(KRIS, source_family="github")
    except Exception as exc:  # noqa: BLE001
        kris = {"error": str(exc)}

    body_m = re.search(
        br"Hash:[^\n]*\n\n(.+?)\n-----BEGIN PGP SIGNATURE-----",
        raw,
        re.S,
    )
    body = body_m.group(1).decode("utf-8", "replace") if body_m else ""
    key_bytes = store.get_bytes(KEY_SHA)
    ver = pgp.verify_clearsigned(raw, key_bytes)
    verify = {
        "result": ver.get("result"),
        "signing_fpr": ver.get("signing_fpr"),
        "primary_fpr": ver.get("primary_fpr"),
        "tool_version": ver.get("tool_version"),
    }
    print("verify", verify, "body_len", len(body), flush=True)

    pad = encode_stream(body)
    phrases = {p: GP.encode_latin_key(p) for p in PHRASES}
    pt = GP.encode_latin_key(
        "THEPRIMESARESACREDTHETOTIENTFVNCTIANISSACREDALLTHNGSSHOVLDBEENCRYPTEDAWARNNGBELIEVENOTHNG"
    )
    plants = {}
    pks = (pad * 8)[: len(pt) * 4]
    recp = beam_decode(encrypt_reject(pt, pks)[0], pks)
    agree = sum(a == b for a, b in zip(recp, pt)) / len(pt) if recp else 0.0
    plants["pad_beam"] = {"agree": round(agree, 4), "ok": agree >= 0.85}
    seed = hashlib.sha256(raw).digest()
    ks = sha256_ctr(seed, len(pt) * 4)
    rec2 = beam_decode(encrypt_reject(pt, ks)[0], ks)
    agree2 = sum(a == b for a, b in zip(rec2, pt)) / len(pt) if rec2 else 0.0
    plants["sha_beam"] = {"agree": round(agree2, 4), "ok": agree2 >= 0.85}
    first = next(iter(phrases.values()))
    vks = [first[i % len(first)] for i in range(len(pt) * 4)]
    rec3 = beam_decode(encrypt_reject(pt, vks)[0], vks)
    agree3 = sum(a == b for a, b in zip(rec3, pt)) / len(pt) if rec3 else 0.0
    plants["vig_beam"] = {"agree": round(agree3, 4), "ok": agree3 >= 0.85}
    plants["ok"] = all(v.get("ok") for v in plants.values() if isinstance(v, dict))
    print("plant", plants, flush=True)

    targets_beam = [("prefix400", prefix(400)), ("split015", idxs_of(15))]
    pages = [(f"split{s:03d}", idxs_of(s)) for s in range(15, 71) if len(idxs_of(s)) >= 80]
    hits, tested, best = [], 0, None

    def consider(row):
        nonlocal best, tested
        tested += 1
        if best is None or row["trigram_per_100"] > best["trigram_per_100"]:
            best = row
        if keep(row, row["n"]):
            hits.append(row)
            print("KEEP", row.get("family"), row.get("key"), row.get("span"),
                  row["trigram_per_100"], row["head"][:40], flush=True)

    for tname, ct in targets_beam:
        need = len(ct) * 4
        ks = (pad * (need // max(len(pad), 1) + 1))[:need]
        recb = beam_decode(ct, ks)
        lat = GP.latin_stream(recb)
        sc = score_candidate(recb, lat)
        consider({"family": "pad", "key": "2016body", "span": tname, "rel": "sub",
                  "head": lat[:80], **sc, "n": len(recb)})
        recb = beam_decode(ct, sha256_ctr(hashlib.sha256(raw).digest(), need))
        lat = GP.latin_stream(recb)
        sc = score_candidate(recb, lat)
        consider({"family": "sha_blob", "key": "2016asc", "span": tname, "rel": "sub",
                  "head": lat[:80], **sc, "n": len(recb)})
        recb = beam_decode(ct, sha256_ctr(hashlib.sha256(body.encode()).digest(), need))
        lat = GP.latin_stream(recb)
        sc = score_candidate(recb, lat)
        consider({"family": "sha_body", "key": "2016body", "span": tname, "rel": "sub",
                  "head": lat[:80], **sc, "n": len(recb)})
        for pname, pix in phrases.items():
            vks = [pix[i % len(pix)] for i in range(need)]
            recb = beam_decode(ct, vks)
            lat = GP.latin_stream(recb)
            sc = score_candidate(recb, lat)
            consider({"family": "vig_beam", "key": pname, "span": tname, "rel": "sub",
                      "head": lat[:80], **sc, "n": len(recb)})

    for pname, pix in phrases.items():
        for tname, ct in ([("prefix400", prefix(400))] + pages):
            for rel in ("sub", "add", "beau"):
                rec = [apply_p(c, pix[i % len(pix)], rel) for i, c in enumerate(ct)]
                lat = GP.latin_stream(rec)
                sc = score_candidate(rec, lat)
                consider({"family": "vig_rigid", "key": pname, "span": tname, "rel": rel,
                          "head": lat[:80], **sc, "n": len(rec)})

    result = {
        "experiment": "EXP-LP-PGP-2016-PATH-001",
        "family": "2016 path-lies-empty PGP body (new to this tree): verify + skip-aware pad/SHA + new phrases",
        "url": URL,
        "sha256": fetched.get("sha256"),
        "kris_sha256": kris.get("sha256") if isinstance(kris, dict) else None,
        "verify": verify,
        "body": body.strip(),
        "pad_runes": len(pad),
        "plant": plants,
        "tested": tested,
        "keep_bar_hits": len(hits),
        "keeps": hits[:16],
        "best": {k: best[k] for k in ("family", "key", "span", "rel", "head", "trigram_per_100", "ioc")} if best else None,
        "skeptic_review": {
            "verdict": "null" if not hits else "keep-bar needs human English",
            "english": False,
            "new_signed_body": verify.get("result") == "VALID",
        },
        "verified_new_unsolved_runes": 0,
    }
    (OUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print("tested", tested, "keeps", len(hits), "verify", verify.get("result"),
          "best", None if not best else (best["trigram_per_100"], best["family"], best["key"], best["head"][:40]))


if __name__ == "__main__":
    main()
