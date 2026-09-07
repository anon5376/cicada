#!/usr/bin/env python3
"""Ulysses + Canterbury Tales as sliding Vigenere pads (encode only to RUNE_CAP)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from cicada.liber_primus.gematria import Gematria  # noqa: E402
from cicada.paths import ROOT as CICADA_ROOT  # noqa: E402
from exp_runkey_primer_cgrid import idxs_of, prefix, slide_running_key  # noqa: E402

GP = Gematria()
OUT = CICADA_ROOT / "experiments" / "EXP-LP-ULYSSES-CANTERBURY-RUNKEY-001"
CAS = CICADA_ROOT / "corpus/objects/sha256"
RUNE_CAP = 220000


def encode_capped(text: str, cap: int) -> list[int]:
    compact = "".join(ch for ch in text.upper() if ch.isalpha() and ch != "Q")
    # encode in chunks so we stop at cap
    out: list[int] = []
    step = 8000
    i = 0
    while i < len(compact) and len(out) < cap:
        out.extend(GP.encode_latin_key(compact[i : i + step]))
        i += step
    return out[:cap]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fetches = []
    hays = {}
    for name, pref in (("ulysses", "d432d18d2535a28e"), ("canterbury", "433661fd210e0351")):
        xs = list((CAS / pref[:2]).glob(pref + "*"))
        if not xs:
            fetches.append({"name": name, "ok": False})
            continue
        raw = xs[0].read_text(encoding="utf-8", errors="replace")
        ix = encode_capped(raw, RUNE_CAP)
        hays[name] = ix
        fetches.append({"name": name, "ok": True, "runes": len(ix), "sha": xs[0].name})
        print("hay", name, "runes", len(ix), flush=True)

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
                print(f"rk {hname:10s} {tname:10s} {rel:4s} keeps={len(found)}", flush=True)
                for hit in found:
                    hit.update({"hay": hname, "span": tname})
                    hits.append(hit)
                    print("KEEP", tname, hname, rel, hit.get("head", "")[:56], flush=True)

    result = {"fetches": fetches, "tested": tested, "keeps": hits, "rune_cap": RUNE_CAP}
    (OUT / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("wrote", OUT / "result.json", "tested", tested, "keeps", len(hits), flush=True)


if __name__ == "__main__":
    main()
