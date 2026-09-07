#!/usr/bin/env python3
"""AES-CTR under attested password SHA-256 keys; solved-LP plains as Porta/Nicodemus."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from cicada.liber_primus.gematria import Gematria  # noqa: E402
from cicada.paths import ROOT as CICADA_ROOT  # noqa: E402
from cicada.scoring import score_candidate  # noqa: E402
from exp_anend_split_aes import pack5, unpack5  # noqa: E402
from exp_autokey_porta_skel import nicodemus_decrypt, porta29  # noqa: E402
from exp_runkey_primer_cgrid import encode_stream, idxs_of, prefix  # noqa: E402
from exp_ulysses_canterbury_runkey import encode_capped  # noqa: E402
from exp_runkey_primer_cgrid import slide_running_key  # noqa: E402

GP = Gematria()
Q = 29
OUT = CICADA_ROOT / "experiments" / "EXP-LP-AES-PW-SOLVED-PORTA-001"
PAGE_DIR = CICADA_ROOT / "corpus/normalized/rtkd_pages"
CAS = CICADA_ROOT / "corpus/objects/sha256"
FIXT = CICADA_ROOT / "tests/liber_primus/replay_fixtures.json"

PASSWORDS = [
    b"3301",
    b"DIVINITY",
    b"AN END",
    b"CICADA",
    b"CICADA 3301",
    b"liber primus",
    b"THELOSSOFDIVINITY",
    b"FIRFUMFERENFE",
    b"6D854CD7933322A601C3286D181F01E57A35090F",
    b"7A35090F",
]


def keep(sc: dict, n: int) -> bool:
    return (
        n >= 80
        and sc["trigram_per_100"] >= 3.5
        and 0.28 <= sc["vowelish_ratio"] <= 0.55
        and sc["ioc"] >= 0.045
    )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    hits = []
    tested = 0
    note = "no AES"
    ct900 = prefix(900)
    sec = idxs_of(15) + idxs_of(16) + idxs_of(17)
    targets = [("prefix900", ct900), ("sec0-2", sec)]
    targets += [(f"split{s:03d}", idxs_of(s)) for s in range(15, 71) if len(idxs_of(s)) >= 80]

    try:
        from Crypto.Cipher import AES
        from Crypto.Util import Counter

        packed = {n: pack5(ct) for n, ct in (("p900", ct900), ("sec", sec))}
        for pw in PASSWORDS:
            key = hashlib.sha256(pw).digest()
            for tname, blob in packed.items():
                n = {"p900": len(ct900), "sec": len(sec)}[tname]
                for nonce in (b"\x00" * 8, pw[:8].ljust(8, b"\x00"), key[:8]):
                    tested += 1
                    ctr = Counter.new(64, prefix=nonce)
                    ptb = AES.new(key, AES.MODE_CTR, counter=ctr).decrypt(blob)
                    out = unpack5(ptb, n)
                    latin = GP.latin_stream(out)
                    sc = score_candidate(out, latin)
                    if pw == b"3301" and tname == "p900" and nonce == b"\x00" * 8:
                        print(f"aes {tname} 3301 tri={sc['trigram_per_100']:.2f} ioc={sc['ioc']:.3f} {latin[:40]}")
                    if keep(sc, len(out)):
                        hits.append({"kind": "aes", "pw": pw.decode("ascii", "replace"), "span": tname, "head": latin[:80], **sc})
            # rune-as-byte on prefix
            tested += 1
            ctr = Counter.new(64, prefix=b"\x00" * 8)
            ptb = AES.new(key, AES.MODE_CTR, counter=ctr).decrypt(bytes(x % 29 for x in ct900))
            out = [b % 29 for b in ptb]
            latin = GP.latin_stream(out)
            sc = score_candidate(out, latin)
            if keep(sc, len(out)):
                hits.append({"kind": "aes_runebyte", "pw": pw.decode("ascii", "replace"), "head": latin[:80], **sc})
        note = "AES-CTR ran"
    except ImportError as e:
        note = f"import {e}"
        print(note)

    fixtures = json.loads(FIXT.read_text(encoding="utf-8"))
    plains = []
    for fx in fixtures:
        lat = fx.get("expected_latin_normalized")
        if lat:
            plains.append((fx["stage_id"], GP.encode_latin_key(lat)))
    # concat LP1+56+57
    concat = []
    for _, ix in plains:
        concat.extend(ix)
    plains.append(("solved_concat", concat))

    for tname, ct in (("prefix900", ct900), ("sec0-2", sec)):
        for pn, key in plains:
            if not key:
                continue
            tested += 1
            pt = porta29(ct, key)
            latin = GP.latin_stream(pt)
            sc = score_candidate(pt, latin)
            if pn == "lp1.warning" and tname == "prefix900":
                print(f"porta {tname} {pn} tri={sc['trigram_per_100']:.2f} ioc={sc['ioc']:.3f} {latin[:40]}")
            if keep(sc, len(pt)):
                hits.append({"kind": "porta_solved", "span": tname, "key": pn, "head": latin[:80], **sc})
            tested += 1
            pt = nicodemus_decrypt(ct, key)
            latin = GP.latin_stream(pt)
            sc = score_candidate(pt, latin)
            if keep(sc, len(pt)):
                hits.append({"kind": "nico_solved", "span": tname, "key": pn, "head": latin[:80], **sc})

    # Kafka (small CAS text) as running key vs prefix400 + long pages only
    xs = list((CAS / "c9").glob("c9f7245e700dc729*"))
    rk_keeps = []
    if xs:
        hay = encode_capped(xs[0].read_text(encoding="utf-8", errors="replace"), 80000)
        print("hay kafka", len(hay))
        for tname, ct in [("prefix400", prefix(400))] + [
            (f"split{s:03d}", idxs_of(s)) for s in (15, 17, 56, 63, 66, 68) if len(idxs_of(s)) >= 80
        ]:
            for rel in ("sub", "add", "beau"):
                tested += 1
                found = slide_running_key(ct, hay, rel)
                for hit in found:
                    hit.update({"hay": "kafka", "span": tname})
                    rk_keeps.append(hit)
                    print("KEEP kafka", tname, rel, hit.get("head", "")[:50])

    print("tested", tested, "keeps", len(hits), "rk", len(rk_keeps), note)
    (OUT / "result.json").write_text(
        json.dumps(
            {"tested": tested, "keeps": hits, "kafka_keeps": rk_keeps, "aes_note": note},
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
