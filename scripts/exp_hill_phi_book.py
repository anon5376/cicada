#!/usr/bin/env python3
"""Hill on φ-substituted / totient-entry book matrices.

EXP-LP-HILL-WISDOM-001 used raw squares mod 29. Dukotah Campaign VII named
φ-substituted variants of the three book matrices as unrun in their rig;
this tree had not applied Euler φ to the entries either.
"""
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
from exp_hill_wisdom_and_headers import C15, WISDOM, det, hill_apply, invert, mat_mod  # noqa: E402
from exp_skipaware_sha_ctr import idxs_of, keep, prefix  # noqa: E402

GP = Gematria()
Q = 29
OUT = CICADA_ROOT / "experiments" / "EXP-LP-HILL-PHI-BOOK-001"

def phi(n: int) -> int:
    n = abs(int(n))
    if n <= 1:
        return 1 if n == 1 else 0
    r, x, p = n, n, 2
    while p * p <= x:
        if x % p == 0:
            while x % p == 0:
                x //= p
            r = r // p * (p - 1)
        p += 1
    if x > 1:
        r = r // x * (x - 1)
    return r


def apply_entries(M: list[list[int]], fn) -> list[list[int]]:
    return [[fn(x) % Q for x in row] for row in M]


def variants(name: str, M: list[list[int]]) -> dict[str, list[list[int]]]:
    raw = mat_mod(M)
    out = {
        f"{name}_mod": raw,
        f"{name}_phi": apply_entries(M, phi),
        f"{name}_m1": apply_entries(M, lambda x: x - 1),
        f"{name}_phi_m1": apply_entries(M, lambda x: phi(x) - 1 if phi(x) else 0),
    }
    extra = {}
    for k, V in list(out.items()):
        extra[k + "T"] = [list(r) for r in zip(*V)]
    out.update(extra)
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    mats: dict[str, list[list[int]]] = {}
    for name, M in (("wisdom", WISDOM), ("c15", C15)):
        mats.update(variants(name, M))

    invs = {}
    invertibility = {}
    for name, M in mats.items():
        K = invert(M)
        invertibility[name] = {"det": det(M), "ok": K is not None, "n": len(M)}
        if K is not None:
            invs[name] = K
    print("invertible", sum(1 for v in invertibility.values() if v["ok"]),
          "/", len(invertibility), flush=True)

    pt = GP.encode_latin_key(
        "THEPRIMESARESACREDTHETOTIENTFVNCTIANISSACREDALLTHNGSSHOVLDBEENCRYPTEDAWARNNGBELIEVENOTHNG"
    )
    plants = {}
    # pick first invertible 5×5 as plant key
    plant_name = next((n for n, K in invs.items() if len(K) == 5), None)
    if plant_name:
        Kinv = invs[plant_name]
        K = mats[plant_name]
        ct = hill_apply(pt, K)
        rec = hill_apply(ct, Kinv)
        plants["roundtrip"] = rec == pt[: len(rec)] and len(rec) >= 80
        # wrong inverse
        other = next((n for n in invs if n != plant_name and len(invs[n]) == 5), None)
        if other:
            plants["wrong"] = hill_apply(ct, invs[other]) != pt[: len(ct) // 5 * 5]
        else:
            plants["wrong"] = True
        plants["plant_matrix"] = plant_name
    plants["ok"] = bool(plants.get("roundtrip") and plants.get("wrong") and invs)
    print("plant", plants, flush=True)
    if not plants["ok"]:
        (OUT / "result.json").write_text(json.dumps({
            "experiment": "EXP-LP-HILL-PHI-BOOK-001", "plant": plants,
            "invertibility": invertibility,
            "verified_new_unsolved_runes": 0, "aborted": "plant failed",
        }, indent=2) + "\n")
        return

    targets = [("prefix400", prefix(400))]
    for s in range(15, 71):
        ct = idxs_of(s)
        if len(ct) >= 80:
            targets.append((f"split{s:03d}", ct))

    hits, tested, best = [], 0, None
    for tname, ct in targets:
        for kname, K in invs.items():
            tested += 1
            rec = hill_apply(ct, K)
            if len(rec) < 40:
                continue
            lat = GP.latin_stream(rec)
            sc = score_candidate(rec, lat)
            row = {"K": kname, "span": tname, "head": lat[:80], **sc, "n": len(rec)}
            if best is None or sc["trigram_per_100"] > best["trigram_per_100"]:
                best = row
            if keep(sc, len(rec)):
                hits.append(row)
                print("KEEP", kname, tname, sc["trigram_per_100"], lat[:40], flush=True)

    result = {
        "experiment": "EXP-LP-HILL-PHI-BOOK-001",
        "family": "Hill φ/totient-entry book matrices (wisdom 5×5, C15 4×4)",
        "plant": plants,
        "invertibility": invertibility,
        "n_invertible": sum(1 for v in invertibility.values() if v["ok"]),
        "tested": tested,
        "keep_bar_hits": len(hits),
        "keeps": hits[:12],
        "best": {k: best[k] for k in ("K", "span", "head", "trigram_per_100", "ioc")} if best else None,
        "skeptic_review": {
            "verdict": "null" if not hits else "keep-bar needs human English",
            "english": False,
        },
        "verified_new_unsolved_runes": 0,
        "note": "Raw-mod-29 wisdom/C15 already closed; this adds φ(entry) and entry-1. No in-repo 3301-trace 5×5 — not invented.",
    }
    (OUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print("tested", tested, "keeps", len(hits),
          "best", None if not best else (best["trigram_per_100"], best["K"], best["head"][:40]))


if __name__ == "__main__":
    main()
