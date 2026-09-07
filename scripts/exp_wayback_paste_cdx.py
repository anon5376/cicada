#!/usr/bin/env python3
"""Wayback CDX for pastebin/GitHub 7A35090F and cicada pastes (CC index 404/drop)."""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from urllib.parse import quote

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from cicada.acquisition import validate_url  # noqa: E402
from cicada.liber_primus.gematria import Gematria  # noqa: E402
from cicada.paths import ROOT as CICADA_ROOT  # noqa: E402
from cicada.pgp import verify_clearsigned  # noqa: E402
from cicada.scoring import score_candidate  # noqa: E402
from exp_skipaware_marsaglia import idxs_of, prefix, record_blob  # noqa: E402
from exp_skipaware_sha_ctr import beam_decode, keep, sha256_ctr  # noqa: E402

GP = Gematria()
OUT = CICADA_ROOT / "experiments" / "EXP-LP-WAYBACK-PASTE-CDX-001"
UA = {"User-Agent": "cicada-research/0.1 (historical puzzle archive; passive GET)"}
KEY = CICADA_ROOT / "corpus/objects/sha256/ce/ce6c44a4c3daf6d5b3691f8894ddb59b10ab58514ce1a2e692caf9b86af7142a"
PGP_RE = re.compile(
    rb"-----BEGIN PGP SIGNED MESSAGE-----.*?-----END PGP SIGNATURE-----",
    re.S,
)
QUERIES = (
    "pastebin.com/*7A35090F*",
    "pastebin.com/*3301*",
    "pastebin.com/*cicada*",
    "pastebin.com/*liberprimus*",
    "pastebin.com/raw/*3301*",
    "raw.githubusercontent.com/*7A35090F*",
)


def get(url: str, timeout: int = 60) -> requests.Response:
    validate_url(url)
    return requests.get(url, headers=UA, timeout=timeout, allow_redirects=True)


def cdx(url_pat: str, limit: int = 40) -> tuple[int, list]:
    q = (
        "https://web.archive.org/cdx/search/cdx?url="
        + quote(url_pat, safe="*")
        + f"&output=json&filter=statuscode:200&limit={limit}&from=2014"
    )
    try:
        r = get(q, timeout=90)
    except Exception as exc:
        return -1, [{"error": str(exc)}]
    if r.status_code != 200:
        return r.status_code, []
    try:
        rows = r.json()
    except json.JSONDecodeError:
        return r.status_code, [{"raw": r.text[:200]}]
    if not rows:
        return 200, []
    header, body = rows[0], rows[1:]
    return 200, [dict(zip(header, row)) for row in body]


def ia_fetch(ts: str, url: str) -> bytes | None:
    ia = f"https://web.archive.org/web/{ts}id_/{url}"
    try:
        r = get(ia, timeout=60)
    except Exception as exc:
        print("ia err", ia, exc, flush=True)
        return None
    if r.status_code != 200:
        print("ia status", r.status_code, ia[:90], flush=True)
        return None
    return r.content


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    hits = []
    seen = set()
    for pat in QUERIES:
        status, rows = cdx(pat)
        print(f"cdx {pat} status={status} n={len(rows)}", flush=True)
        for row in rows:
            orig = row.get("original") or ""
            ts = row.get("timestamp") or ""
            key = (orig, ts)
            if key in seen:
                continue
            seen.add(key)
            hits.append({"query": pat, **row})

    print("unique captures", len(hits), flush=True)
    already = set()
    cas = CICADA_ROOT / "corpus/objects/sha256"
    for p in cas.glob("*/*"):
        if p.is_file() and p.stat().st_size < 400_000:
            raw = p.read_bytes()
            if b"BEGIN PGP SIGNED MESSAGE" in raw:
                already.add(hashlib.sha256(raw).hexdigest())
                for m in PGP_RE.findall(raw):
                    already.add(hashlib.sha256(m).hexdigest())

    new_pgp = []
    keeps = []
    inspected = []
    targets = [("prefix400", prefix(400)), ("split015", idxs_of(15))]
    for meta in hits[:30]:
        orig = meta.get("original") or ""
        ts = meta.get("timestamp") or ""
        payload = ia_fetch(ts, orig)
        if payload is None:
            inspected.append({"url": orig, "ts": ts, "ok": False})
            continue
        sha = hashlib.sha256(payload).hexdigest()
        blob = {
            "url": orig,
            "ts": ts,
            "ok": True,
            "sha256": sha,
            "n": len(payload),
            "pgp": bool(PGP_RE.search(payload)),
            "has_fp": b"7A35090F" in payload or b"7a35090f" in payload.lower(),
        }
        inspected.append(blob)
        print("got", blob["n"], blob["pgp"], blob["has_fp"], orig[:80], flush=True)
        if blob["pgp"] or blob["has_fp"] or b"BEGIN PGP" in payload:
            record_blob(payload, f"https://web.archive.org/web/{ts}id_/{orig}")
        for armored in PGP_RE.findall(payload):
            h = hashlib.sha256(armored).hexdigest()
            if h in already:
                continue
            already.add(h)
            try:
                ver = verify_clearsigned(armored, KEY.read_bytes())
                rec = {"url": orig, "sha256": h, "result": ver.get("result"), "fpr": ver.get("signing_fpr")}
            except Exception as exc:
                rec = {"url": orig, "sha256": h, "err": str(exc)}
            new_pgp.append(rec)
            print("NEW PGP", rec, flush=True)
            for span, ct in targets:
                pt = beam_decode(ct, sha256_ctr(armored, 2000))
                lat = GP.latin_stream(pt)
                sc = score_candidate(pt, lat)
                if keep(sc, len(pt)):
                    keeps.append({"src": orig, "span": span, "head": lat[:80], **sc})

    print("new_pgp", len(new_pgp), "keeps", len(keeps), flush=True)
    (OUT / "result.json").write_text(
        json.dumps(
            {
                "n_hits": len(hits),
                "inspected": inspected,
                "new_pgp": new_pgp,
                "keeps": keeps,
                "hits": hits[:80],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
