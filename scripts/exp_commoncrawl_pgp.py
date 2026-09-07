#!/usr/bin/env python3
"""Common Crawl CDX search for post-2017 7A35090F / Cicada signed bodies.

URL-index only (not a full-text crawl). Fetches WARC slices or allowlisted
live URLs when a hit looks like PGP or a paste. New signed bodies are
skip-aware beamed. Known-page replays do not count.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from cicada.acquisition import TIMEOUT, validate_url  # noqa: E402
from cicada.liber_primus.gematria import Gematria  # noqa: E402
from cicada.paths import ROOT as CICADA_ROOT  # noqa: E402
from cicada.pgp import verify_clearsigned  # noqa: E402
from cicada.scoring import score_candidate  # noqa: E402
from cicada.store import get_bytes, object_path  # noqa: E402
from exp_skipaware_marsaglia import idxs_of, prefix, record_blob  # noqa: E402
from exp_skipaware_sha_ctr import beam_decode, keep, sha256_ctr  # noqa: E402

GP = Gematria()
Q = 29
OUT = CICADA_ROOT / "experiments" / "EXP-LP-COMMONCRAWL-PGP-001"
UA = {"User-Agent": "cicada-research/0.1 (historical puzzle archive; passive GET)"}
KNOWN_FP = "6D854CD7933322A601C3286D181F01E57A35090F"
NEEDLES = (
    "7A35090F",
    "6D854CD7933322A601C3286D181F01E57A35090F",
    "BEGIN PGP SIGNED MESSAGE",
    "cicada 3301",
    "CICADA 3301",
    "Liber Primus",
)
QUERIES = (
    "*7A35090F*",
    "*6D854CD7933322A601C3286D181F01E57A35090F*",
    "pastebin.com/*3301*",
    "pastebin.com/*cicada*",
    "pastebin.com/*liber*",
    "github.com/*7A35090F*",
    "raw.githubusercontent.com/*7A35090F*",
)
PGP_RE = re.compile(
    rb"-----BEGIN PGP SIGNED MESSAGE-----.*?-----END PGP SIGNATURE-----",
    re.S,
)
KEY = CICADA_ROOT / "corpus/objects/sha256/ce/ce6c44a4c3daf6d5b3691f8894ddb59b10ab58514ce1a2e692caf9b86af7142a"


def session_get(url: str, **kw) -> requests.Response:
    validate_url(url)
    kw.setdefault("headers", UA)
    kw.setdefault("timeout", TIMEOUT)
    kw.setdefault("allow_redirects", True)
    return requests.get(url, **kw)


def pick_indexes(collinfo: list[dict]) -> list[dict]:
    by_id = {c.get("id"): c for c in collinfo if c.get("cdx-api")}
    chosen = []
    for row in collinfo[:4]:
        if row.get("cdx-api"):
            chosen.append(row)
    for cid in (
        "CC-MAIN-2017-22",
        "CC-MAIN-2017-17",
        "CC-MAIN-2014-23",
        "CC-MAIN-2014-15",
    ):
        if cid in by_id and by_id[cid] not in chosen:
            chosen.append(by_id[cid])
    return chosen


def cdx_query(api: str, url_pat: str, limit: int = 40) -> tuple[int, list[dict]]:
    q = f"{api}?url={requests.utils.quote(url_pat, safe='*')}&output=json&filter=status:200&limit={limit}"
    try:
        resp = session_get(q, timeout=60)
    except Exception as exc:
        return -1, [{"error": str(exc), "query": q}]
    if resp.status_code != 200:
        return resp.status_code, []
    rows = []
    for line in resp.text.splitlines():
        line = line.strip()
        if not line or line.startswith("{"):
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return 200, rows


def warc_slice(filename: str, offset: str, length: str) -> bytes | None:
    url = "https://data.commoncrawl.org/" + filename.lstrip("/")
    start = int(offset)
    end = start + int(length) - 1
    try:
        validate_url(url)
        resp = requests.get(
            url,
            headers={**UA, "Range": f"bytes={start}-{end}"},
            timeout=90,
            allow_redirects=True,
        )
    except Exception as exc:
        print("warc err", filename, exc, flush=True)
        return None
    if resp.status_code not in (200, 206):
        print("warc status", resp.status_code, filename, flush=True)
        return None
    data = resp.content
    if data[:2] == b"\x1f\x8b":
        try:
            data = gzip.decompress(data)
        except OSError:
            pass
    return data


def payload_from_warc(rec: bytes) -> bytes:
    sep = rec.find(b"\r\n\r\n")
    if sep < 0:
        return rec
    rest = rec[sep + 4 :]
    sep2 = rest.find(b"\r\n\r\n")
    if sep2 < 0:
        return rest
    return rest[sep2 + 4 :]


def interesting(url: str, payload: bytes) -> bool:
    blob = payload.lower()
    u = url.lower()
    if any(n.lower().encode() in blob for n in NEEDLES):
        return True
    if b"begin pgp" in blob or b"7a35090f" in blob:
        return True
    if "pastebin.com" in u and (b"3301" in blob or b"cicada" in blob or b"pgp" in blob):
        return True
    return False


def known_pgp_hashes() -> set[str]:
    out = set()
    cas = CICADA_ROOT / "corpus/objects/sha256"
    if not cas.exists():
        return out
    for p in cas.glob("*/*"):
        if not p.is_file() or p.stat().st_size > 400_000:
            continue
        raw = p.read_bytes()
        if b"BEGIN PGP SIGNED MESSAGE" in raw[:80] or b"BEGIN PGP SIGNED MESSAGE" in raw:
            out.add(hashlib.sha256(raw).hexdigest())
            for m in PGP_RE.findall(raw):
                out.add(hashlib.sha256(m).hexdigest())
    return out


def extract_pgp(payload: bytes) -> list[bytes]:
    return PGP_RE.findall(payload)


def live_fetch(url: str) -> bytes | None:
    host = (urlparse(url).hostname or "").lower()
    if host not in {"pastebin.com", "raw.githubusercontent.com", "github.com", "web.archive.org"}:
        return None
    if host == "pastebin.com" and "/raw/" not in url:
        path = urlparse(url).path.rstrip("/")
        pid = path.rsplit("/", 1)[-1]
        if pid and pid.isalnum():
            url = f"https://pastebin.com/raw/{pid}"
    try:
        resp = session_get(url, timeout=45)
    except Exception as exc:
        print("live err", url, exc, flush=True)
        return None
    if resp.status_code != 200:
        print("live status", resp.status_code, url, flush=True)
        return None
    return resp.content


def encode_stream(text: str) -> list[int]:
    compact = "".join(ch for ch in text.upper() if ch.isascii() and ch.isalpha() and ch != "Q")
    return GP.encode_latin_key(compact) if compact else []


def beam_body(label: str, body: bytes, targets) -> list[dict]:
    hits = []
    seeds = [body, hashlib.sha256(body).digest(), body[:64], body.strip().split(b"\n")[0][:80]]
    for i, seed in enumerate(seeds):
        if not seed:
            continue
        ks = sha256_ctr(seed, 2000)
        for span, ct in targets:
            pt = beam_decode(ct, ks)
            lat = GP.latin_stream(pt)
            sc = score_candidate(pt, lat)
            row = {"src": label, "seed_i": i, "span": span, "head": lat[:80], **sc}
            if keep(sc, len(pt)):
                hits.append(row)
    return hits


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    print("collinfo", flush=True)
    info = session_get("https://index.commoncrawl.org/collinfo.json", timeout=60)
    if info.status_code != 200:
        raise SystemExit(f"collinfo {info.status_code}")
    collinfo = info.json()
    indexes = pick_indexes(collinfo)
    print("indexes", [c.get("id") for c in indexes], "of", len(collinfo), flush=True)

    hits_meta = []
    fetch_log = []
    new_pgp = []
    already = known_pgp_hashes()
    print("known pgp hashes", len(already), flush=True)

    seen_urls = set()
    for idx in indexes:
        api = idx["cdx-api"]
        cid = idx.get("id")
        for pat in QUERIES:
            status, rows = cdx_query(api, pat)
            print(f"cdx {cid} {pat} status={status} n={len(rows)}", flush=True)
            for row in rows:
                url = row.get("url") or ""
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                hits_meta.append({"index": cid, "query": pat, **{k: row.get(k) for k in ("url", "timestamp", "filename", "offset", "length", "mime")}})

    print("unique urls", len(seen_urls), flush=True)

    def _prio(m: dict) -> int:
        u = (m.get("url") or "").lower()
        if "7a35090f" in u or "6d854cd7" in u:
            return 0
        if "pgp" in u or "liber" in u:
            return 1
        if "cicada" in u or "3301" in u:
            return 2
        return 3

    hits_meta.sort(key=_prio)
    targets = [("prefix400", prefix(400)), ("split015", idxs_of(15))]
    keeps = []
    inspected = 0
    fetch_budget = 40
    for meta in hits_meta:
        if inspected >= fetch_budget:
            break
        url = meta["url"]
        payload = None
        src = None
        live = live_fetch(url)
        if live is not None:
            payload, src = live, "live"
        elif meta.get("filename") and meta.get("offset") and meta.get("length"):
            raw = warc_slice(meta["filename"], meta["offset"], meta["length"])
            if raw:
                payload, src = payload_from_warc(raw), "warc"
        if payload is None:
            fetch_log.append({"url": url, "ok": False})
            continue
        inspected += 1
        sha = hashlib.sha256(payload).hexdigest()
        note = {
            "url": url,
            "ok": True,
            "src": src,
            "sha256": sha,
            "n": len(payload),
            "interesting": interesting(url, payload),
        }
        fetch_log.append(note)
        if not note["interesting"] and b"BEGIN PGP" not in payload:
            continue
        record_blob(payload, url)
        print("got", src, len(payload), url[:90], flush=True)
        for armored in extract_pgp(payload):
            h = hashlib.sha256(armored).hexdigest()
            if h in already:
                print("known pgp", h[:16], url[:70], flush=True)
                continue
            already.add(h)
            rec = {
                "url": url,
                "sha256": h,
                "n": len(armored),
                "head": armored[:120].decode("utf-8", "replace"),
            }
            try:
                ver = verify_clearsigned(armored, KEY.read_bytes())
                rec["verify"] = {
                    "result": ver.get("result"),
                    "fpr": ver.get("signing_fpr") or ver.get("primary_fpr"),
                }
            except Exception as exc:
                rec["verify_err"] = str(exc)
            new_pgp.append(rec)
            print("NEW PGP", rec, flush=True)
            keeps.extend(beam_body(url, armored, targets))
            body_m = re.search(
                rb"-----BEGIN PGP SIGNED MESSAGE-----\r?\nHash: [^\n]+\r?\n\r?\n(.*?)\r?\n-----BEGIN PGP SIGNATURE-----",
                armored,
                re.S,
            )
            if body_m:
                keeps.extend(beam_body(url + "#body", body_m.group(1), targets))

    print("inspected", inspected, "new_pgp", len(new_pgp), "keeps", len(keeps), flush=True)
    (OUT / "result.json").write_text(
        json.dumps(
            {
                "indexes": [c.get("id") for c in indexes],
                "n_collinfo": len(collinfo),
                "n_urls": len(seen_urls),
                "inspected": inspected,
                "new_pgp": new_pgp,
                "keeps": keeps,
                "hits": hits_meta[:200],
                "fetch_log": fetch_log[:200],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
