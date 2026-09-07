#!/usr/bin/env python3
"""Skip-aware running key at offset 0 on Dukotah R12-C2 texts (allowlisted hosts only).

Their fetch.sh pulled Gutenberg/globalgrey; those hosts are not in this lab's
allowlist. Wayback + archive.org copies of the same titles are.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.parse import urlparse

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from cicada.acquisition import _host_allowed, validate_url  # noqa: E402
from cicada.liber_primus.gematria import Gematria  # noqa: E402
from cicada.paths import ROOT as CICADA_ROOT  # noqa: E402
from cicada.scoring import score_candidate  # noqa: E402
from cicada.db import db_path  # noqa: E402
from cicada.store import get_bytes  # noqa: E402
from exp_skipaware_marsaglia import idxs_of, prefix, record_blob  # noqa: E402
from exp_skipaware_sha_ctr import beam_decode, encrypt_reject, keep  # noqa: E402

GP = Gematria()
Q = 29
OUT = CICADA_ROOT / "experiments" / "EXP-LP-SKIPAWARE-R12C2-001"
RUNE_CAP = 4000

PG = {
    "plotinus_enneads": 71455,
    "apuleius_golden_ass": 1666,
    "epictetus_discourses": 10661,
    "seneca_letters": 56075,
    "plato_phaedo": 1658,
    "plato_phaedrus": 1636,
    "swedenborg_heaven_hell": 33443,
    "boehme_aurora": 49582,
    "kempis_imitation": 1653,
    "james_varieties": 621,
    "augustine_city_of_god": 45304,
    "frazer_golden_bough": 3623,
    "bruno_heroic": 19833,
}
IA = {
    "theologia_germanica": "https://archive.org/stream/theologiagermani00winkuoft/theologiagermani00winkuoft_djvu.txt",
    "iamblichus_mysteries": "https://archive.org/stream/iamblichusonmyst00iamb/iamblichusonmyst00iamb_djvu.txt",
    "dee_hieroglyphic_monad": "https://archive.org/stream/johndeeshierogly00deejuoft/johndeeshierogly00deejuoft_djvu.txt",
    "meister_eckhart": "https://archive.org/stream/meistereckhartfr00eckh/meistereckhartfr00eckh_djvu.txt",
}


def encode_stream(text: str) -> list[int]:
    compact = "".join(ch for ch in text.upper() if ch.isascii() and ch.isalpha() and ch != "Q")
    return GP.encode_latin_key(compact) if compact else []


def cached_url(url: str) -> dict | None:
    import sqlite3

    conn = sqlite3.connect(db_path())
    try:
        row = conn.execute(
            "SELECT r.sha256, b.byte_length, b.path FROM retrievals r "
            "JOIN blobs b ON b.sha256 = r.sha256 WHERE r.url = ?",
            (url,),
        ).fetchone()
    finally:
        conn.close()
    if not row:
        return None
    sha, n, path = row
    p = CICADA_ROOT / path
    if p.exists() and n and n >= 3000:
        return {"sha256": sha, "byte_length": n, "path": path, "url": url}
    return None


def wayback_pg(pgid: int) -> str:
    return f"https://web.archive.org/web/2024id_/https://www.gutenberg.org/cache/epub/{pgid}/pg{pgid}.txt"


def fetch_text(name: str, url: str) -> tuple[str, dict]:
    hit = cached_url(url)
    if hit:
        data = get_bytes(hit["sha256"])
        rec = {**hit, "name": name}
        print(f"cache {name} {hit['sha256'][:16]} {hit['byte_length']}", flush=True)
        return data.decode("utf-8", "replace"), rec
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
        raise RuntimeError(f"{url} status {resp.status_code}")
    data = resp.content
    if len(data) < 3000:
        raise RuntimeError(f"{url} too small {len(data)}")
    rec = record_blob(data, url)
    rec["name"] = name
    return data.decode("utf-8", "replace"), rec


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fetched, errors = [], []
    texts = {}
    for name, pgid in PG.items():
        try:
            text, rec = fetch_text(name, wayback_pg(pgid))
            texts[name] = text
            fetched.append(rec)
            print("got", name, rec["byte_length"], flush=True)
        except Exception as exc:  # noqa: BLE001
            errors.append({"name": name, "error": str(exc)})
            print("FAIL", name, exc, flush=True)
    for name, url in IA.items():
        try:
            text, rec = fetch_text(name, url)
            texts[name] = text
            fetched.append(rec)
            print("got", name, rec["byte_length"], flush=True)
        except Exception as exc:  # noqa: BLE001
            errors.append({"name": name, "error": str(exc)})
            print("FAIL", name, exc, flush=True)

    if not texts:
        raise SystemExit(f"no texts: {errors}")

    first = encode_stream(next(iter(texts.values())))[:800]
    plant_pt = GP.encode_latin_key(
        "THEPRIMESARESACREDTHETOTIENTFVNCTIANISSACREDALLTHNGSSHOVLDBEENCRYPTEDAWARNNGBELIEVENOTHNG"
    )
    pks = first[: len(plant_pt) * 4]
    if len(pks) < len(plant_pt):
        pks = (pks * (len(plant_pt) * 4 // max(1, len(pks)) + 1))[: len(plant_pt) * 4]
    plant_ct, _ = encrypt_reject(plant_pt, pks)
    rec = beam_decode(plant_ct, pks)
    agree = sum(a == b for a, b in zip(rec, plant_pt)) / len(plant_pt) if rec else 0.0
    plant = {"agree": round(agree, 4), "ok": agree >= 0.95}
    print("plant", plant, flush=True)

    targets = [("prefix400", prefix(400)), ("split015", idxs_of(15))]
    hits = []
    tested = 0
    samples = []
    for name, text in texts.items():
        hay = encode_stream(text)[:RUNE_CAP]
        if len(hay) < 200:
            errors.append({"name": name, "error": f"only {len(hay)} runes"})
            continue
        for span, ct in targets:
            need = len(ct) * 4
            ks = (hay * (need // len(hay) + 1))[:need]
            tested += 1
            pt = beam_decode(ct, ks)
            lat = GP.latin_stream(pt)
            sc = score_candidate(pt, lat)
            row = {"text": name, "span": span, "runes": len(hay), "head": lat[:80], **sc}
            if tested <= 3:
                print(f"beam {name} {span} tri={sc['trigram_per_100']:.2f} {lat[:36]}", flush=True)
                samples.append(row)
            if keep(sc, len(pt)):
                hits.append(row)
                print("KEEP", row, flush=True)

    print("tested", tested, "keeps", len(hits), "texts", len(texts), "errors", len(errors), flush=True)
    (OUT / "result.json").write_text(
        json.dumps(
            {
                "plant": plant,
                "fetched": [
                    {"name": r.get("name"), "sha256": r.get("sha256"), "byte_length": r.get("byte_length")}
                    for r in fetched
                ],
                "fetch_errors": errors,
                "tested": tested,
                "keeps": hits,
                "samples": samples,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
