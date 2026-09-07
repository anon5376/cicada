#!/usr/bin/env python3
"""Skip-aware pad/seed tests on the Marsaglia 1995 Diehard CDROM.

Dukotah named this public entropy source as unswept. This is not a full
offset sweep of 600 MB. It tests start-of-file and historically marked
offsets, plus SHA-256 of each retrieved file as a CTR seed.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import sqlite3
import sys
import uuid
from pathlib import Path
from urllib.parse import urlparse

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from cicada import db, store  # noqa: E402
from cicada.acquisition import _host_allowed, validate_url  # noqa: E402
from cicada.db import db_path  # noqa: E402
from cicada.events import emit, utc_now  # noqa: E402
from cicada.liber_primus.gematria import Gematria  # noqa: E402
from cicada.paths import ROOT as CICADA_ROOT  # noqa: E402
from cicada.scoring import score_candidate  # noqa: E402
from exp_skipaware_sha_ctr import (  # noqa: E402
    beam_decode,
    encrypt_reject,
    keep,
    sha256_ctr,
)

GP = Gematria()
Q = 29
PAGE_DIR = CICADA_ROOT / "corpus/normalized/rtkd_pages"
OUT = CICADA_ROOT / "experiments" / "EXP-LP-SKIPAWARE-MARSAGLIA-001"

BASE = "https://raw.githubusercontent.com/jeffThompson/DiehardCDROM/master/CD-ROM"
FILES = (
    "bits.01",
    "bits.15",
    "bits.33",
    "bits.56",
    "canada.bit",
    "calif.bit",
)
OFFSETS = (0, 15, 56, 57, 3301, 2012, 2013, 2014, 1295, 95729)
WAYBACK = (
    "https://web.archive.org/web/20160119150146id_/http://stat.fsu.edu/pub/diehard/cdrom/{name}"
)
WAYBACK_ALT = {
    "bits.01": "bit.01",
    "bits.15": "bit.15",
    "bits.33": "bit.33",
    "bits.56": "bit.56",
}


def idxs_of(split: int) -> list[int]:
    return GP.rune_indices((PAGE_DIR / f"split_{split:03d}.txt").read_text(encoding="utf-8"))


def prefix(n: int = 400) -> list[int]:
    out: list[int] = []
    for s in range(15, 71):
        out.extend(idxs_of(s))
        if len(out) >= n:
            break
    return out[:n]


def pad_bytes(data: bytes, offset: int, n: int) -> list[int]:
    ln = len(data)
    return [data[(offset + i) % ln] % Q for i in range(n)]


def pad_5bit(data: bytes, bit0: int, n: int) -> list[int]:
    out: list[int] = []
    ln = len(data) * 8
    for i in range(n):
        v = 0
        for b in range(5):
            pos = (bit0 + i * 5 + b) % ln
            byte = data[pos // 8]
            v = (v << 1) | ((byte >> (7 - (pos % 8))) & 1)
        out.append(v % Q)
    return out


def record_blob(data: bytes, url: str) -> dict:
    blob = store.put_bytes(data, hint_name=urlparse(url).path.split("/")[-1])
    conn = db.connect()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO blobs VALUES (?,?,?,?,?,?,?)",
            (blob["sha256"], blob["sha1"], blob["md5"], blob["byte_length"], blob["mime"], blob["path"], utc_now()),
        )
        sid = f"src-{uuid.uuid4().hex[:12]}"
        conn.execute(
            "INSERT OR IGNORE INTO sources VALUES (?,?,?,?,?,?)",
            (sid, url, None, "marsaglia-cdrom", "https", None),
        )
        rid = f"ret-{uuid.uuid4().hex[:12]}"
        conn.execute(
            "INSERT INTO retrievals VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                rid,
                sid,
                url,
                utc_now(),
                200,
                json.dumps([url]),
                blob["sha256"],
                "GET",
                "OK",
                json.dumps({}),
            ),
        )
        conn.commit()
    finally:
        conn.close()
    emit("retrieval_ok", url=url, sha256=blob["sha256"], bytes=blob["byte_length"])
    return {**blob, "url": url, "access_status": "OK"}


def already_have(name: str) -> dict | None:
    conn = sqlite3.connect(db_path())
    try:
        rows = conn.execute(
            "SELECT r.url, r.sha256, b.byte_length, b.path FROM retrievals r "
            "JOIN blobs b ON b.sha256 = r.sha256 WHERE r.url LIKE ?",
            (f"%/{name}",),
        ).fetchall()
    finally:
        conn.close()
    for url, sha, n, path in rows:
        p = CICADA_ROOT / path
        if p.exists() and n and n >= 1_000_000:
            return {"name": name, "url": url, "sha256": sha, "byte_length": n, "path": path}
    return None


def fetch_one(name: str) -> dict:
    cached = already_have(name)
    if cached:
        print(f"cache {name} {cached['sha256'][:16]} {cached['byte_length']}", flush=True)
        return cached
    urls = [f"{BASE}/{name}", WAYBACK.format(name=name)]
    if name in WAYBACK_ALT:
        urls.append(WAYBACK.format(name=WAYBACK_ALT[name]))
    last_err = None
    for url in urls:
        try:
            validate_url(url)
            session = requests.Session()
            session.max_redirects = 5
            headers = {"User-Agent": "cicada-research/0.1 (historical puzzle archive; passive GET)"}
            resp = session.get(url, headers=headers, timeout=180, allow_redirects=True)
            hops = [url] + [h.url for h in resp.history] + ([resp.url] if resp.url != url else [])
            for hop in hops:
                host = urlparse(hop).hostname or ""
                if host and not _host_allowed(host):
                    raise PermissionError(f"redirect left allowlist: {hop}")
            if resp.status_code != 200:
                last_err = f"{url} status {resp.status_code}"
                print(last_err, flush=True)
                continue
            data = resp.content
            if len(data) < 1_000_000:
                last_err = f"{url} too small {len(data)}"
                print(last_err, flush=True)
                continue
            rec = record_blob(data, url)
            rec["name"] = name
            print(f"got {name} {rec['sha256'][:16]} {rec['byte_length']}", flush=True)
            return rec
        except Exception as exc:  # noqa: BLE001 — record fetch failure, try next URL
            last_err = f"{url} {exc}"
            print(last_err, flush=True)
    raise RuntimeError(f"could not fetch {name}: {last_err}")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fetched = []
    fetch_errors = []
    for name in FILES:
        try:
            fetched.append(fetch_one(name))
        except Exception as exc:  # noqa: BLE001
            fetch_errors.append({"name": name, "error": str(exc)})
            print("FAIL", name, exc, flush=True)
    if not fetched:
        raise SystemExit(f"no Marsaglia files retrieved: {fetch_errors}")

    plant_lat = (
        "THEPRIMESARESACREDTHETOTIENTFVNCTIANISSACREDALLTHNGSSHOVLDBEENCRYPTEDAWARNNGBELIEVENOTHNG"
    )
    plant_pt = GP.encode_latin_key(plant_lat)
    first = store.get_bytes(fetched[0]["sha256"])
    pks = pad_bytes(first, 0, len(plant_pt) * 4)
    plant_ct, used = encrypt_reject(plant_pt, pks)
    rec = beam_decode(plant_ct, pks)
    agree = sum(a == b for a, b in zip(rec, plant_pt)) / len(plant_pt) if rec else 0.0
    plant = {
        "source": fetched[0]["name"],
        "agree": round(agree, 4),
        "ok": agree >= 0.95,
        "recovered_head": GP.latin_stream(rec)[:80],
    }
    print("plant", plant, flush=True)

    p400 = prefix(400)
    p15 = idxs_of(15)
    targets = [("prefix400", p400), ("split015", p15)]
    hits = []
    tested = 0
    samples = []

    for rec in fetched:
        data = store.get_bytes(rec["sha256"])
        seeds = [
            ("sha_file", bytes.fromhex(rec["sha256"])),
            ("sha_head32", hashlib.sha256(data[:32]).digest()),
            ("name", rec["name"].encode()),
        ]
        for span, ct in targets:
            need = len(ct) * 4
            for off in OFFSETS:
                if off >= len(data):
                    continue
                for mode, ks in (
                    (f"byte29@{off}", pad_bytes(data, off, need)),
                    (f"bit5@{off}", pad_5bit(data, off * 8, need)),
                ):
                    tested += 1
                    pt = beam_decode(ct, ks)
                    lat = GP.latin_stream(pt)
                    sc = score_candidate(pt, lat)
                    row = {
                        "file": rec["name"],
                        "span": span,
                        "mode": mode,
                        "head": lat[:80],
                        **sc,
                    }
                    if tested <= 4 or (rec["name"] == "bits.01" and off == 0 and span == "prefix400"):
                        print(
                            f"beam {rec['name']} {span} {mode} tri={sc['trigram_per_100']:.2f} {lat[:36]}",
                            flush=True,
                        )
                        samples.append(row)
                    if keep(sc, len(pt)):
                        hits.append(row)
                        print("KEEP", row, flush=True)
            for label, seed in seeds:
                tested += 1
                pt = beam_decode(ct, sha256_ctr(seed, need))
                lat = GP.latin_stream(pt)
                sc = score_candidate(pt, lat)
                row = {
                    "file": rec["name"],
                    "span": span,
                    "mode": f"sha256_ctr:{label}",
                    "head": lat[:80],
                    **sc,
                }
                if keep(sc, len(pt)):
                    hits.append(row)
                    print("KEEP", row, flush=True)

    fp = bytes.fromhex("6D854CD7933322A601C3286D181F01E57A35090F")
    for span, ct in targets:
        for msg in (b"0", b"15", b"56", b"3301", b"LIBERPRIMUS", b"AN END"):
            tested += 1
            seed = hmac.new(fp, msg, hashlib.sha256).digest()
            pt = beam_decode(ct, sha256_ctr(seed, len(ct) * 4))
            lat = GP.latin_stream(pt)
            sc = score_candidate(pt, lat)
            row = {
                "file": "hmac-pgp-fp",
                "span": span,
                "mode": f"hmac:{msg.decode()}",
                "head": lat[:80],
                **sc,
            }
            if keep(sc, len(pt)):
                hits.append(row)
                print("KEEP", row, flush=True)

    out = {
        "plant": plant,
        "fetched": [
            {"name": r["name"], "sha256": r["sha256"], "byte_length": r["byte_length"], "url": r.get("url")}
            for r in fetched
        ],
        "fetch_errors": fetch_errors,
        "tested": tested,
        "keeps": hits,
        "samples": samples,
        "offsets": list(OFFSETS),
        "scope": "start-of-file and marked offsets; not a 600 MB offset sweep",
    }
    (OUT / "result.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("tested", tested, "keeps", len(hits), "files", len(fetched), flush=True)


if __name__ == "__main__":
    main()
