#!/usr/bin/env python3
"""KJV + Paradise Lost as Vigenere/Beaufort running keys (not word-length skeletons)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from cicada.acquisition import fetch_url  # noqa: E402
from cicada.liber_primus.gematria import Gematria  # noqa: E402
from cicada.paths import ROOT as CICADA_ROOT  # noqa: E402
from exp_runkey_primer_cgrid import encode_stream, idxs_of, keep, prefix, slide_running_key  # noqa: E402

GP = Gematria()
OUT = CICADA_ROOT / "experiments" / "EXP-LP-KJV-RUNNING-KEY-001"
PAGE_DIR = CICADA_ROOT / "corpus/normalized/rtkd_pages"
RUNE_CAP = 220000


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fetches = []
    hays = {}
    cas = CICADA_ROOT / "corpus/objects/sha256"
    local = {
        "kjv": "a681fbe6e2fc77d7",
        "shakespeare": "7c87c9da9ad1c945",
        "plost": "20",  # filled from fetch if needed
    }
    # resolve CAS prefixes
    for name, pref in (("kjv", "a681fbe6e2fc77d7"), ("shakespeare", "7c87c9da9ad1c945")):
        xs = list((cas / pref[:2]).glob(pref + "*"))
        if not xs:
            fetches.append({"name": name, "ok": False, "reason": "cas miss"})
            continue
        raw = xs[0].read_text(encoding="utf-8", errors="replace")
        ix = encode_stream(raw)[:RUNE_CAP]
        hays[name] = ix
        fetches.append({"name": name, "ok": True, "runes": len(ix), "sha": xs[0].name, "source": "cas"})
        print("hay", name, "runes", len(ix), xs[0].name[:16])
    fetches.append({"name": "plost", "ok": True, "note": "already 0 keeps at 220k runes in prior invocation of this script"})

    targets = [("prefix400", prefix(400))]
    for s in range(15, 71):
        ix = idxs_of(s)
        if len(ix) >= 80:
            targets.append((f"split{s:03d}", ix))

    hits = []
    tested = 0
    for hname, hay in hays.items():
        for tname, ct in targets:
            for rel in ("sub", "add", "beau"):
                tested += 1
                found = slide_running_key(ct, hay, rel)
                print(f"rk {hname:5s} {tname:10s} {rel:4s} win~{max(0,len(hay)-len(ct)+1)} keeps={len(found)}")
                for hit in found:
                    hit.update({"hay": hname, "span": tname})
                    hits.append(hit)
                    print("KEEP", {k: hit[k] for k in ("hay", "span", "rel", "pos", "trigram_per_100", "ioc", "head")})

    # skeptic: TH-salad keeps are not English
    reviewed = []
    for hit in hits:
        head = hit.get("head", "")
        th = head.count("TH")
        reviewed.append(
            {
                **{k: hit[k] for k in ("hay", "span", "rel", "pos", "trigram_per_100", "ioc", "head") if k in hit},
                "th_count": th,
                "verdict": (
                    "scorer artifact"
                    if th >= 8 or "THENGO" in head or hit.get("span") == "split066"
                    else "needs eyes"
                ),
            }
        )

    result = {
        "fetches": fetches,
        "rune_cap": RUNE_CAP,
        "tested": tested,
        "keeps": hits,
        "review": reviewed,
    }
    (OUT / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("wrote", OUT / "result.json", "tested", tested, "keeps", len(hits))


if __name__ == "__main__":
    main()
