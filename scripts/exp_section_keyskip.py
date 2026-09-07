#!/usr/bin/env python3
"""Extra key consumes at red-section and page boundaries.

RED-INK-001 marked section openings at onion 0,3,8,15,23,27,33,40,53,54.
Word-end and CT-F extra-consume are closed. This burns 1–3 extra keystream
symbols at those known page starts (and, separately, at every page join)
while the stream keeps running across the concatenated unsolved book.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from cicada.liber_primus.ciphers import apply_named  # noqa: E402
from cicada.liber_primus.fixtures import load_fixtures  # noqa: E402
from cicada.liber_primus.gematria import Gematria  # noqa: E402
from cicada.paths import ROOT as CICADA_ROOT  # noqa: E402
from cicada.scoring import score_candidate  # noqa: E402
from exp_skipaware_sha_ctr import keep, sha256_ctr  # noqa: E402
from exp_word_depth import idxs_of  # noqa: E402
from exp_word_end_keyskip import apply_c, apply_p, totient_ks  # noqa: E402

GP = Gematria()
Q = 29
OUT = CICADA_ROOT / "experiments" / "EXP-LP-SECTION-KEYSKIP-001"
SEEDS = [b"CICADA3301", b"3301", b"DIVINITY", b"AN END", b"LIBERPRIMUS", b"TOTIENT"]
# onion indices with red section openings (solved 56/57 excluded)
SECTION_ONION = (0, 3, 8, 15, 23, 27, 33, 40, 53, 54)


def decode_pages(pages: list[list[int]], ks: list[int], extra: int,
                 burn: set[int], rel: str) -> list[list[int]]:
    """pages[k] is CT of split 15+k (onion k). burn is onion indices."""
    out, j = [], 0
    for k, ct in enumerate(pages):
        if k in burn and extra:
            j += extra
        rec = []
        for c in ct:
            if j >= len(ks):
                break
            rec.append(apply_p(c, ks[j], rel))
            j += 1
        out.append(rec)
    return out


def encode_pages(pages: list[list[int]], ks: list[int], extra: int,
                 burn: set[int], rel: str) -> list[list[int]]:
    out, j = [], 0
    for k, pt in enumerate(pages):
        if k in burn and extra:
            j += extra
        rec = []
        for p in pt:
            rec.append(apply_c(p, ks[j], rel))
            j += 1
        out.append(rec)
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fx = {f["stage_id"]: f for f in load_fixtures()}
    warn = apply_named("atbash", GP.rune_indices(fx["lp1.warning"]["ciphertext"]), None)
    wisd = apply_named("direct", GP.rune_indices(fx["lp1.wisdom"]["ciphertext"]), None)
    # plant: two "pages", burn at start of page 1
    ks = sha256_ctr(b"CICADA3301", (len(warn) + len(wisd) + 8) * 2)
    plants = {}
    for extra in (1, 2, 3):
        for rel in ("sub", "add", "beau"):
            ct = encode_pages([warn, wisd], ks, extra, {1}, rel)
            rec = decode_pages(ct, ks, extra, {1}, rel)
            plants[f"{rel}_e{extra}"] = rec == [warn, wisd]
    plants["wrong"] = decode_pages(encode_pages([warn, wisd], ks, 2, {1}, "sub"),
                                  ks, 0, {1}, "sub") != [warn, wisd]
    plants["ok"] = all(v is True for k, v in plants.items() if k != "ok")
    print("plant", plants, flush=True)
    if not plants["ok"]:
        (OUT / "result.json").write_text(json.dumps({
            "experiment": "EXP-LP-SECTION-KEYSKIP-001", "plant": plants,
            "verified_new_unsolved_runes": 0, "aborted": "plant failed",
        }, indent=2) + "\n")
        return

    pages = [idxs_of(s) for s in range(15, 71)]
    burns = {
        "section": {o for o in SECTION_ONION if o < len(pages)},
        "allpages": set(range(1, len(pages))),  # every join, not first
    }
    streams = [(f"sha:{s.decode()}", lambda n, s=s: sha256_ctr(s, n)) for s in SEEDS]
    streams += [(f"tot{st}", lambda n, st=st: totient_ks(n, st)) for st in (0, 1)]
    need = sum(len(p) for p in pages) + 200
    hits, tested, best = [], 0, None
    for sname, kfn in streams:
        ks = kfn(need)
        for bname, burn in burns.items():
            for extra in (1, 2, 3):
                for rel in ("sub", "add", "beau"):
                    recs = decode_pages(pages, ks, extra, burn, rel)
                    for oi, rec in enumerate(recs):
                        if len(rec) < 80:
                            continue
                        tested += 1
                        lat = GP.latin_stream(rec)
                        sc = score_candidate(rec, lat)
                        row = {"onion": oi, "split": 15 + oi, "stream": sname,
                               "burn": bname, "extra": extra, "rel": rel,
                               "head": lat[:80], **sc, "n": len(rec)}
                        if best is None or sc["trigram_per_100"] > best["trigram_per_100"]:
                            best = row
                        if keep(sc, len(rec)):
                            hits.append(row)
                            print("KEEP", row["split"], sname, bname, extra, rel,
                                  sc["trigram_per_100"], lat[:40], flush=True)

    result = {
        "experiment": "EXP-LP-SECTION-KEYSKIP-001",
        "family": "extra key consume at red-section / page-join boundaries",
        "plant": plants,
        "tested": tested,
        "keep_bar_hits": len(hits),
        "keeps": hits[:12],
        "best": {k: best[k] for k in ("split", "stream", "burn", "extra", "rel", "head", "trigram_per_100", "ioc")} if best else None,
        "skeptic_review": {"verdict": "null" if not hits else "keep-bar needs human English"},
        "verified_new_unsolved_runes": 0,
    }
    (OUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print("tested", tested, "keeps", len(hits),
          "best", None if not best else (best["trigram_per_100"], best["stream"], best["head"][:40]))


if __name__ == "__main__":
    main()
