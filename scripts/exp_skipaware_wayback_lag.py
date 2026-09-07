#!/usr/bin/env python3
"""Wayback fandom wiki pads + skip-aware self-key at DJUBEI lag 6395."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from cicada.liber_primus.gematria import Gematria  # noqa: E402
from cicada.paths import ROOT as CICADA_ROOT  # noqa: E402
from cicada.scoring import score_candidate  # noqa: E402
from exp_skipaware_marsaglia import idxs_of, prefix  # noqa: E402
from exp_skipaware_r12c2 import encode_stream, fetch_text  # noqa: E402
from exp_skipaware_sha_ctr import beam_decode, encrypt_reject, keep  # noqa: E402

GP = Gematria()
Q = 29
OUT = CICADA_ROOT / "experiments" / "EXP-LP-SKIPAWARE-WAYBACK-LAG-001"
LAGS = (6395, 1279, 15, 29, 56, 3301, 1033)
WIKI = (
    (
        "how_solved",
        "https://web.archive.org/web/20230101000000id_/https://uncovering-cicada.fandom.com/wiki/How_the_solved_pages_of_the_Liber_Primus_were_solved",
    ),
    (
        "liber_primus",
        "https://web.archive.org/web/20230101000000id_/https://uncovering-cicada.fandom.com/wiki/Liber_Primus",
    ),
    (
        "pgp_2017",
        "https://web.archive.org/web/20230101000000id_/https://uncovering-cicada.fandom.com/wiki/PGP_Signed_Message_April_2017",
    ),
)


def unsolved_flat() -> list[int]:
    out: list[int] = []
    for s in range(15, 71):
        out.extend(idxs_of(s))
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    plant_pt = GP.encode_latin_key(
        "THEPRIMESARESACREDTHETOTIENTFVNCTIANISSACREDALLTHNGSSHOVLDBEENCRYPTEDAWARNNGBELIEVENOTHNG"
    )
    dummy = [(i * 7 + 3) % Q for i in range(len(plant_pt) * 4)]
    rec = beam_decode(encrypt_reject(plant_pt, dummy)[0], dummy)
    agree = sum(a == b for a, b in zip(rec, plant_pt)) / len(plant_pt) if rec else 0.0
    plant = {"agree": round(agree, 4), "ok": agree >= 0.95}
    print("plant", plant, flush=True)

    flat = unsolved_flat()
    print("flat", len(flat), flush=True)
    targets = [("prefix400", prefix(400)), ("split015", idxs_of(15))]
    hits = []
    tested = 0
    samples = []
    fetch_recs = []
    errors = []

    for lag in LAGS:
        if lag >= len(flat):
            continue
        ks = [flat[(i + lag) % len(flat)] for i in range(max(len(t[1]) for t in targets) * 4)]
        for span, ct in targets:
            tested += 1
            pt = beam_decode(ct, ks[: len(ct) * 4])
            lat = GP.latin_stream(pt)
            sc = score_candidate(pt, lat)
            row = {"src": f"lag{lag}", "span": span, "mode": "self_ct", "head": lat[:80], **sc}
            if tested <= 4:
                print(f"beam lag{lag} {span} tri={sc['trigram_per_100']:.2f} {lat[:36]}", flush=True)
                samples.append(row)
            if keep(sc, len(pt)):
                hits.append(row)
                print("KEEP", row, flush=True)

    for name, url in WIKI:
        try:
            text, rec = fetch_text(name, url)
            fetch_recs.append({"name": name, "sha256": rec.get("sha256"), "byte_length": rec.get("byte_length")})
            hay = encode_stream(text)
            print("wiki", name, "runes", len(hay), flush=True)
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
                row = {"src": name, "span": span, "mode": "wayback_fandom", "head": lat[:80], **sc}
                if keep(sc, len(pt)):
                    hits.append(row)
                    print("KEEP", row, flush=True)
        except Exception as exc:  # noqa: BLE001
            errors.append({"name": name, "error": str(exc)})
            print("FAIL", name, exc, flush=True)

    print("tested", tested, "keeps", len(hits), flush=True)
    (OUT / "result.json").write_text(
        json.dumps(
            {
                "plant": plant,
                "tested": tested,
                "keeps": hits,
                "samples": samples,
                "fetched": fetch_recs,
                "fetch_errors": errors,
                "lags": list(LAGS),
                "flat_n": len(flat),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
