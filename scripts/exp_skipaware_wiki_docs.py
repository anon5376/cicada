#!/usr/bin/env python3
"""Skip-aware running keys from in-CAS Wikipedia raw pages and scream314 docs.

These were ingested or used as word-length skeletons, not as skip-aware pads.
"""
from __future__ import annotations

import json
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
from exp_skipaware_sha_ctr import beam_decode, encrypt_reject, keep, sha256_ctr  # noqa: E402

GP = Gematria()
Q = 29
OUT = CICADA_ROOT / "experiments" / "EXP-LP-SKIPAWARE-WIKI-DOCS-001"
URL_SUBSTR = (
    "en.wikipedia.org/wiki/",
    "scream314/cicada3301/master/liber_primus.md",
    "scream314/cicada3301/master/pages_and_ciphers.md",
    "scream314/cicada3301/master/hints_never_used.md",
    "uncovering-cicada.fandom.com/wiki/",
)


def encode_stream(text: str) -> list[int]:
    compact = "".join(ch for ch in text.upper() if ch.isascii() and ch.isalpha() and ch != "Q")
    return GP.encode_latin_key(compact) if compact else []


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path())
    rows = conn.execute(
        "SELECT r.url, r.sha256, b.byte_length FROM retrievals r "
        "JOIN blobs b ON b.sha256 = r.sha256"
    ).fetchall()
    conn.close()
    docs = {}
    for url, sha, n in rows:
        if not any(s in url for s in URL_SUBSTR):
            continue
        if n and n < 200:
            continue
        name = url.rstrip("/").rsplit("/", 1)[-1].split("?")[0]
        if name in docs:
            continue
        raw = get_bytes(sha).decode("utf-8", "replace")
        ix = encode_stream(raw)
        if len(ix) < 200:
            continue
        docs[name] = {"url": url, "sha256": sha, "runes": len(ix), "ix": ix}
        print("doc", name, len(ix), n, flush=True)

    if not docs:
        raise SystemExit("no wiki/docs in CAS")

    first = next(iter(docs.values()))["ix"]
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
    for name, rec in docs.items():
        hay = rec["ix"]
        for span, ct in targets:
            need = len(ct) * 4
            ks = (hay * (need // len(hay) + 1))[:need]
            for mode, stream in (("pad0", ks), ("sha256_ctr", sha256_ctr(bytes.fromhex(rec["sha256"]), need))):
                tested += 1
                pt = beam_decode(ct, stream)
                lat = GP.latin_stream(pt)
                sc = score_candidate(pt, lat)
                row = {"doc": name, "span": span, "mode": mode, "head": lat[:80], **sc}
                if tested <= 4 or (name.startswith("Cicada") and span == "prefix400"):
                    print(f"beam {name} {span} {mode} tri={sc['trigram_per_100']:.2f} {lat[:36]}", flush=True)
                    samples.append(row)
                if keep(sc, len(pt)):
                    hits.append(row)
                    print("KEEP", row, flush=True)

    print("tested", tested, "keeps", len(hits), flush=True)
    (OUT / "result.json").write_text(
        json.dumps(
            {
                "plant": plant,
                "docs": {k: {kk: vv for kk, vv in v.items() if kk != "ix"} for k, v in docs.items()},
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
