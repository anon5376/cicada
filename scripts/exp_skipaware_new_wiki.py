#!/usr/bin/env python3
"""Skip-aware pads from Wikipedia raw pages not in the prior 13-doc CAS set.

Prior wiki pads: Cicada_3301, totient, Emerald Tablet, Hermetica, Enoch,
Discordia, Beowulf, Aeneid, Tao, Nag Hammadi. These titles are the unused
Cicada-adjacent set (Sefer Yetzirah, Gematria, Agrippa, Liber AL, Soyga, …).
"""
from __future__ import annotations

import hashlib
import json
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
from exp_skipaware_sha_ctr import beam_decode, encrypt_reject, idxs_of, keep, prefix, sha256_ctr  # noqa: E402

GP = Gematria()
Q = 29
OUT = CICADA_ROOT / "experiments" / "EXP-LP-SKIPAWARE-NEW-WIKI-001"
RUNE_CAP = 4000

PAGES = (
    "Sefer_Yetzirah",
    "Gematria",
    "Heinrich_Cornelius_Agrippa",
    "The_Book_of_the_Law",
    "Book_of_Soyga",
    "Atbash",
    "John_Dee",
    "Magic_square",
    "Liber_Primus",
    "Cicada_3301",  # already used as pad; fetch is cheap if cached, skip if so
)


def encode_stream(text: str) -> list[int]:
    compact = "".join(ch for ch in text.upper() if ch.isascii() and ch.isalpha() and ch != "Q")
    return GP.encode_latin_key(compact) if compact else []


def wiki_raw(title: str) -> str:
    return f"https://en.wikipedia.org/wiki/{title}?action=raw"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    docs, errors = {}, []
    for title in PAGES:
        if title == "Cicada_3301":
            continue  # already skip-aware
        url = wiki_raw(title)
        try:
            rec = fetch_url(url, source_family="wikipedia")
            if rec.get("http_status") != 200:
                errors.append({"title": title, "error": rec.get("access_status")})
                print("FAIL", title, rec.get("http_status"), flush=True)
                continue
            raw = get_bytes(rec["sha256"]).decode("utf-8", "replace")
            ix = encode_stream(raw)
            if len(ix) < 200:
                errors.append({"title": title, "error": f"only {len(ix)} runes"})
                continue
            docs[title] = {
                "url": url, "sha256": rec["sha256"], "runes": len(ix),
                "ix": ix[:RUNE_CAP], "bytes": rec["byte_length"],
            }
            print("doc", title, len(ix), rec["byte_length"], flush=True)
        except Exception as exc:  # noqa: BLE001
            errors.append({"title": title, "error": str(exc)})
            print("FAIL", title, exc, flush=True)

    if not docs:
        (OUT / "result.json").write_text(json.dumps({
            "experiment": "EXP-LP-SKIPAWARE-NEW-WIKI-001",
            "errors": errors,
            "verified_new_unsolved_runes": 0,
            "aborted": "no new wiki pads",
        }, indent=2) + "\n")
        return

    pt = GP.encode_latin_key(
        "THEPRIMESARESACREDTHETOTIENTFVNCTIANISSACREDALLTHNGSSHOVLDBEENCRYPTEDAWARNNGBELIEVENOTHNG"
    )
    first = next(iter(docs.values()))
    pks = (first["ix"] * 8)[: len(pt) * 4]
    rec = beam_decode(encrypt_reject(pt, pks)[0], pks)
    agree = sum(a == b for a, b in zip(rec, pt)) / len(pt) if rec else 0.0
    plants = {"pad_beam": {"agree": round(agree, 4), "ok": agree >= 0.85}}
    seed = hashlib.sha256(first["sha256"].encode()).digest()
    ks = sha256_ctr(seed, len(pt) * 4)
    rec2 = beam_decode(encrypt_reject(pt, ks)[0], ks)
    agree2 = sum(a == b for a, b in zip(rec2, pt)) / len(pt) if rec2 else 0.0
    plants["sha_beam"] = {"agree": round(agree2, 4), "ok": agree2 >= 0.85}
    plants["ok"] = all(v.get("ok") for v in plants.values() if isinstance(v, dict))
    print("plant", plants, flush=True)

    targets = [("prefix400", prefix(400)), ("split015", idxs_of(15))]
    hits, tested, best = [], 0, None
    for name, doc in docs.items():
        hay = doc["ix"]
        for tname, ct in targets:
            need = len(ct) * 4
            ks = (hay * (need // len(hay) + 1))[:need]
            tested += 1
            rec = beam_decode(ct, ks)
            lat = GP.latin_stream(rec)
            sc = score_candidate(rec, lat)
            row = {"family": "pad", "key": name, "span": tname, "head": lat[:80], **sc, "n": len(rec)}
            if best is None or sc["trigram_per_100"] > best["trigram_per_100"]:
                best = row
            if keep(sc, len(rec)):
                hits.append(row)
                print("KEEP pad", name, tname, sc["trigram_per_100"], lat[:40], flush=True)
            seed = hashlib.sha256(bytes.fromhex(doc["sha256"])).digest()
            tested += 1
            rec = beam_decode(ct, sha256_ctr(seed, need))
            lat = GP.latin_stream(rec)
            sc = score_candidate(rec, lat)
            row = {"family": "sha", "key": name, "span": tname, "head": lat[:80], **sc, "n": len(rec)}
            if best is None or sc["trigram_per_100"] > best["trigram_per_100"]:
                best = row
            if keep(sc, len(rec)):
                hits.append(row)
                print("KEEP sha", name, tname, sc["trigram_per_100"], lat[:40], flush=True)

    result = {
        "experiment": "EXP-LP-SKIPAWARE-NEW-WIKI-001",
        "family": "skip-aware unused Wikipedia raw pads + file-SHA CTR",
        "plant": plants,
        "docs": {k: {kk: vv for kk, vv in v.items() if kk != "ix"} for k, v in docs.items()},
        "errors": errors,
        "tested": tested,
        "keep_bar_hits": len(hits),
        "keeps": hits[:12],
        "best": {k: best[k] for k in ("family", "key", "span", "head", "trigram_per_100", "ioc")} if best else None,
        "skeptic_review": {"verdict": "null" if not hits else "keep-bar needs human English", "english": False},
        "verified_new_unsolved_runes": 0,
    }
    (OUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print("tested", tested, "keeps", len(hits), "docs", list(docs),
          "best", None if not best else (best["trigram_per_100"], best["key"], best["head"][:40]))


if __name__ == "__main__":
    main()
