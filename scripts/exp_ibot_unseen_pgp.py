#!/usr/bin/env python3
"""Fetch every iBotPeaches clearsigned message; beam bodies new to this store.

The 2016 path-lies-empty file was VALID and unused as a pad. Other yearly
files may also be absent from the krisyotam pgp/messages ingest.
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
OUT = CICADA_ROOT / "experiments" / "EXP-LP-IBOT-UNSEEN-PGP-001"
BASE = "https://raw.githubusercontent.com/iBotPeaches/cicada_3301/master/messages"
KEY_SHA = "6e397c5c6ceeeb4da08535db74874989f193c914b8d2d87972dd282b24ea809f"
# From gh listing this turn (no liber_primus/ subtree — that is pages, not .asc).
FILES = {
    "2012": [
        "162667212858.asc", "52.216802.asc", "a-poem-of-fading-death.asc",
        "congratulations.asc", "from-here-on-out.asc", "hello-we-have-now.asc",
        "hello-you-have-shared.asc", "in-twenty-nine-volumes.asc",
        "miss-round-1.asc", "some-news-organizations.asc",
        "the-key-has-always-been.asc", "the-song-is-your-own-path.asc",
        "this-message-will-only-be-displayed.asc", "you-have-done-well.asc",
    ],
    "2013": [
        "26.41968.asc", "32.478944.asc", "33.092817.asc", "34.7477910.asc",
        "37.182685.asc", "38.977845.asc", "55.793765.asc",
        "do-not-share-this-information-2.asc", "do-not-share-this-information.asc",
        "if-you-followed.asc", "no-more-testing.asc", "ssss-03.asc",
        "ssss-09.asc", "ssss-10.asc", "standby-for-coords.asc",
        "tcp-server.asc", "the-key-is-all-around-you.asc", "very-good.asc",
        "welcome-again.asc", "welcome-and-congratulations.asc",
        "well-done-you-have-come-far.asc", "you-already-have-everything.asc",
        "you-cant-see-the-forest.asc",
    ],
    "2014": [
        "hello-you-have-done-well.asc", "hello-your-enlightenment.asc",
        "idgtk-umloo.asc", "let-the-text-guide-you.asc",
        "the-work-of-a-private-man.asc", "very-good-you-have-done-well.asc",
        "welcome.asc",
    ],
    "2015": ["some-news-organizations.asc"],
    "2016": ["hello-the-path-lies-empty.asc"],
    "2017": ["beware-false-paths.asc"],
}


def encode_stream(text: str) -> list[int]:
    compact = "".join(ch for ch in text.upper() if ch.isascii() and ch.isalpha() and ch != "Q")
    return GP.encode_latin_key(compact) if compact else []


def extract_body(raw: bytes) -> str:
    m = re.search(br"Hash:[^\n]*\n\n(.+?)\n-----BEGIN PGP SIGNATURE-----", raw, re.S)
    return m.group(1).decode("utf-8", "replace") if m else ""


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    db.init_db()
    conn = db.connect()
    try:
        known = {r[0] for r in conn.execute("SELECT sha256 FROM retrievals").fetchall()}
    finally:
        conn.close()
    known.add(KEY_SHA)

    key_bytes = store.get_bytes(KEY_SHA)
    catalog, unseen, errors = [], [], []
    for year, names in FILES.items():
        for name in names:
            url = f"{BASE}/{year}/{name}"
            try:
                rec = fetch_url(url, source_family="github")
            except Exception as exc:  # noqa: BLE001
                errors.append({"url": url, "error": str(exc)})
                print("FAIL", year, name, exc, flush=True)
                continue
            if rec.get("http_status") != 200 or not rec.get("sha256"):
                errors.append({"url": url, "error": rec.get("access_status")})
                continue
            sha = rec["sha256"]
            raw = store.get_bytes(sha)
            body = extract_body(raw)
            is_new = sha not in known
            row = {
                "year": year, "name": name, "url": url, "sha256": sha,
                "bytes": rec.get("byte_length"), "body_len": len(body),
                "already_stored": not is_new,
            }
            if is_new and raw.lstrip().startswith(b"-----BEGIN PGP"):
                ver = pgp.verify_clearsigned(raw, key_bytes)
                row["verify"] = ver.get("result")
                row["signing_fpr"] = ver.get("signing_fpr")
                row["body"] = body.strip()[:400]
                unseen.append(row)
                print("NEW", year, name, ver.get("result"), sha[:16], len(body), flush=True)
            else:
                print("old", year, name, sha[:16], flush=True)
            catalog.append({k: v for k, v in row.items() if k != "body"})

    pt = GP.encode_latin_key(
        "THEPRIMESARESACREDTHETOTIENTFVNCTIANISSACREDALLTHNGSSHOVLDBEENCRYPTEDAWARNNGBELIEVENOTHNG"
    )
    plants = {"ok": True}
    if unseen:
        raw0 = store.get_bytes(unseen[0]["sha256"])
        pad0 = encode_stream(unseen[0].get("body") or extract_body(raw0))
        if pad0:
            pks = (pad0 * 8)[: len(pt) * 4]
            recp = beam_decode(encrypt_reject(pt, pks)[0], pks)
            agree = sum(a == b for a, b in zip(recp, pt)) / len(pt) if recp else 0.0
            plants["pad_beam"] = {"agree": round(agree, 4), "ok": agree >= 0.85}
            plants["ok"] = plants["pad_beam"]["ok"]
    print("plant", plants, "unseen", len(unseen), flush=True)

    targets = [("prefix400", prefix(400)), ("split015", idxs_of(15))]
    hits, tested, best = [], 0, None
    valid_new = [u for u in unseen if u.get("verify") == "VALID"]
    for u in valid_new:
        raw = store.get_bytes(u["sha256"])
        body = u.get("body") or extract_body(raw)
        pad = encode_stream(body)
        if len(pad) < 8:
            continue
        for tname, ct in targets:
            need = len(ct) * 4
            ks = (pad * (need // len(pad) + 1))[:need]
            tested += 1
            recb = beam_decode(ct, ks)
            lat = GP.latin_stream(recb)
            sc = score_candidate(recb, lat)
            row = {"family": "pad", "key": f"{u['year']}/{u['name']}", "span": tname,
                   "head": lat[:80], **sc, "n": len(recb)}
            if best is None or sc["trigram_per_100"] > best["trigram_per_100"]:
                best = row
            if keep(sc, len(recb)):
                hits.append(row)
            tested += 1
            recb = beam_decode(ct, sha256_ctr(hashlib.sha256(raw).digest(), need))
            lat = GP.latin_stream(recb)
            sc = score_candidate(recb, lat)
            row = {"family": "sha", "key": f"{u['year']}/{u['name']}", "span": tname,
                   "head": lat[:80], **sc, "n": len(recb)}
            if best is None or sc["trigram_per_100"] > best["trigram_per_100"]:
                best = row
            if keep(sc, len(recb)):
                hits.append(row)

    result = {
        "experiment": "EXP-LP-IBOT-UNSEEN-PGP-001",
        "family": "iBotPeaches yearly clearsigned messages; beam only SHAs not already in retrievals",
        "catalog_n": len(catalog),
        "unseen_n": len(unseen),
        "valid_new_n": len(valid_new),
        "unseen": [{k: v for k, v in u.items() if k != "body"} | {"body_head": (u.get("body") or "")[:160]} for u in unseen],
        "errors": errors,
        "plant": plants,
        "tested": tested,
        "keep_bar_hits": len(hits),
        "keeps": hits[:12],
        "best": {k: best[k] for k in ("family", "key", "span", "head", "trigram_per_100", "ioc")} if best else None,
        "skeptic_review": {"verdict": "null" if not hits else "keep-bar needs human English", "english": False},
        "verified_new_unsolved_runes": 0,
    }
    (OUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print("catalog", len(catalog), "unseen", len(unseen), "valid_new", len(valid_new),
          "tested", tested, "keeps", len(hits),
          "best", None if not best else (best["trigram_per_100"], best["key"], best["head"][:40]))


if __name__ == "__main__":
    main()
