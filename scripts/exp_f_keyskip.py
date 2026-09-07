#!/usr/bin/env python3
"""Known-position extra key consume at ciphertext F (and at CT doublets).

Page 56 leaves the 4th CT F unshifted and does not consume a prime
(skip-encrypt). ANTIREPEAT-SKIP already tried skip-every-F totient/Vigenere
(F copied through, no key consume). This family is different: F is still
decrypted, then 1 or 2 extra keystream symbols are burned. Positions are
observed, so the decode is rigid. Doublet sites are the other observed
anti-repeat marks.
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
from cicada.liber_primus.gematria import Gematria, first_n_primes  # noqa: E402
from cicada.paths import ROOT as CICADA_ROOT  # noqa: E402
from cicada.scoring import score_candidate  # noqa: E402
from exp_skipaware_sha_ctr import keep, sha256_ctr  # noqa: E402
from exp_word_depth import idxs_of  # noqa: E402
from exp_word_end_keyskip import apply_c, apply_p, decode, encode, totient_ks  # noqa: E402

GP = Gematria()
Q = 29
F = 0
OUT = CICADA_ROOT / "experiments" / "EXP-LP-F-KEYSKIP-001"
SEEDS = [b"CICADA3301", b"3301", b"DIVINITY", b"AN END", b"LIBERPRIMUS", b"TOTIENT"]


def f_marks(ct: list[int]):
    return [c == F for c in ct]


def doublet_marks(ct: list[int]):
    return [i > 0 and ct[i] == ct[i - 1] for i in range(len(ct))]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fx = {f["stage_id"]: f for f in load_fixtures()}
    warn = fx["lp1.warning"]
    pt = apply_named(warn["method"], GP.rune_indices(warn["ciphertext"]), None)
    ks = sha256_ctr(b"CICADA3301", len(pt) * 4)
    plants = {}
    dummy_ct_shape = [1] * len(pt)  # marks come from ciphertext; plant uses synthetic CT
    for extra in (1, 2):
        for rel in ("sub", "add", "beau"):
            # plant F-marks on the *ciphertext* that encode produces; iterate once
            # by marking a known PT-side pattern: burn after every 5th index, then
            # separately recover from CT-F of the produced ciphertext.
            marks_every5 = [(i % 5) == 4 for i in range(len(pt))]
            ct = encode(pt, ks, marks_every5, extra, rel, "after")
            rec = decode(ct, ks, marks_every5, extra, rel, "after")
            plants[f"pos5_{rel}_extra{extra}"] = rec == pt
            ct_f = encode(pt, ks, [False] * len(pt), extra, rel, "after")  # no extra; wrap next
    # Real plant: encode with extra-after-CT-F. Marks must be on ciphertext, so
    # generate CT by walking (encode can't see future CT F). Dedicated encoder:
    for extra in (1, 2):
        for rel in ("sub", "add", "beau"):
            ct, j = [], 0
            for p in pt:
                c = apply_c(p, ks[j], rel)
                ct.append(c)
                j += 1
                if c == F:
                    j += extra
            rec = decode(ct, ks, f_marks(ct), extra, rel, "after")
            plants[f"ctF_{rel}_extra{extra}"] = rec == pt
            rec_wrong = decode(ct, ks, f_marks(ct), 0, rel, "after")
            plants[f"ctF_{rel}_extra{extra}_wrong0"] = rec_wrong != pt
    plants["ok"] = all(v is True for k, v in plants.items() if k.startswith("ctF_") and not k.endswith("wrong0")) \
        and all(v is True for k, v in plants.items() if k.endswith("wrong0"))
    print("plant", plants, flush=True)
    if not plants["ok"]:
        (OUT / "result.json").write_text(json.dumps({
            "experiment": "EXP-LP-F-KEYSKIP-001", "plant": plants,
            "verified_new_unsolved_runes": 0, "aborted": "plant failed",
        }, indent=2) + "\n")
        return

    streams = [(f"sha:{s.decode()}", lambda n, s=s: sha256_ctr(s, n)) for s in SEEDS]
    streams += [(f"tot{st}", lambda n, st=st: totient_ks(n, st)) for st in (0, 1)]

    hits, tested, best = [], 0, None
    for sidx in range(15, 71):
        ct = idxs_of(sidx)
        if len(ct) < 80:
            continue
        marks_f = f_marks(ct)
        marks_d = doublet_marks(ct)
        for sname, kfn in streams:
            ks = kfn(len(ct) * 4)
            for extra in (1, 2):
                for rel in ("sub", "add", "beau"):
                    for site, marks in (("ctF", marks_f), ("doublet", marks_d)):
                        tested += 1
                        rec = decode(ct, ks, marks, extra, rel, "after")
                        lat = GP.latin_stream(rec)
                        sc = score_candidate(rec, lat)
                        row = {"split": sidx, "stream": sname, "extra": extra, "rel": rel,
                               "site": site, "head": lat[:80], **sc, "n": len(rec)}
                        if best is None or sc["trigram_per_100"] > best["trigram_per_100"]:
                            best = row
                        if keep(sc, len(rec)):
                            hits.append(row)
                            print("KEEP", sidx, sname, extra, rel, site,
                                  sc["trigram_per_100"], lat[:48], flush=True)

    result = {
        "experiment": "EXP-LP-F-KEYSKIP-001",
        "family": "rigid extra key consume after CT-F or CT-doublet (not skip-encrypt)",
        "plant": {k: plants[k] for k in plants if k.startswith("ctF_") or k == "ok"},
        "tested": tested,
        "keep_bar_hits": len(hits),
        "keeps": hits[:15],
        "best": {k: best[k] for k in ("split", "stream", "extra", "rel", "site", "head", "trigram_per_100", "ioc")} if best else None,
        "skeptic_review": {"verdict": "null" if not hits else "keep-bar needs human English"},
        "verified_new_unsolved_runes": 0,
    }
    (OUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print("tested", tested, "keeps", len(hits),
          "best", None if not best else (best["trigram_per_100"], best["stream"], best["site"], best["head"][:40]))


if __name__ == "__main__":
    main()
