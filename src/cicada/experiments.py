from __future__ import annotations

import hashlib
import json
import uuid
from pathlib import Path

from . import db
from .events import emit, utc_now
from .liber_primus.ciphers import apply_named
from .liber_primus.gematria import Gematria
from .paths import ROOT
from .scoring import score_candidate

GP = Gematria()

KNOWN_KEYS = {
    "DIVINITY": GP.encode_latin_key("DIVINITY"),
    "FIRFUMFERENFE": GP.encode_latin_key("FIRFUMFERENFE"),
    "INSTAR": GP.encode_latin_key("INSTAR"),
    "CIRCUMFERENCE": GP.encode_latin_key("CIRCUMFERENCE"),
    "PILGRIM": GP.encode_latin_key("PILGRIM"),
    "PRIMES": GP.encode_latin_key("PRIMES"),
}


def definition_hash(spec: dict) -> str:
    blob = json.dumps(spec, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def run_transfer_attacks(page_id: str, ciphertext: str, *, experiment_id: str = "EXP-LP-TRANSFER-001") -> dict:
    """Test solved-page mechanisms on a target transcription.

    This is a bounded transfer experiment, not a claim that the families are
    exhausted. Vigenere is tested only on the listed historically motivated keys.
    """
    spec = {
        "experiment_id": experiment_id,
        "hypothesis_id": "LP-HYP-000001",
        "target": page_id,
        "mapping_version": GP.version,
        "methods": [
            "direct",
            "atbash",
            "atbash_plus_3",
            "totient_prime",
            "vigenere:DIVINITY",
            "vigenere:FIRFUMFERENFE",
            "vigenere:INSTAR",
            "vigenere:CIRCUMFERENCE",
            "vigenere:PILGRIM",
            "vigenere:PRIMES",
            "vigenere_skip_pt_f:DIVINITY",
            "vigenere_skip_pt_f:FIRFUMFERENFE",
        ],
        "acceptance": "trigram_per_100 >= 8 and vowelish_ratio in [0.28, 0.52] and ioc >= 0.045",
    }
    dhash = definition_hash(spec)
    idxs = GP.rune_indices(ciphertext)
    results = []
    interesting = []
    for item in spec["methods"]:
        if ":" in item:
            name, keyname = item.split(":", 1)
            key = KNOWN_KEYS[keyname]
        else:
            name, key = item, None
        out = apply_named(name, idxs, key)
        latin = GP.latin_stream(out)
        scores = score_candidate(out, latin)
        rec = {"method": item, "latin_head": latin[:80], "scores": scores}
        results.append(rec)
        if (
            scores["trigram_per_100"] >= 8
            and 0.28 <= scores["vowelish_ratio"] <= 0.52
            and scores["ioc"] >= 0.045
        ):
            interesting.append(rec)

    attempt = {
        "attempt_id": f"att-{uuid.uuid4().hex[:12]}",
        "experiment_id": experiment_id,
        "definition_hash": dhash,
        "start_time": utc_now(),
        "end_time": utc_now(),
        "execution_status": "COMPLETED",
        "tested_count": len(results),
        "expected_count": len(spec["methods"]),
        "input_rune_count": len(idxs),
        "interesting": interesting,
        "results": results,
        "interpretation": (
            "At least one historically transferred method crossed the uncalibrated English-like threshold"
            if interesting
            else "No tested transfer crossed the uncalibrated English-like threshold"
        ),
        "does_not_exclude": "other keys, other families, other offsets, other F-skip rules, other transcriptions",
    }
    dest = ROOT / "experiments" / experiment_id
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "spec.json").write_text(json.dumps(spec, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (dest / "result.json").write_text(json.dumps(attempt, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    conn = db.connect()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO experiments VALUES (?,?,?,?,?)",
            (experiment_id, dhash, "LP-HYP-000001", json.dumps(spec), utc_now()),
        )
        conn.execute(
            "INSERT INTO experiment_attempts VALUES (?,?,?,?,?,?,?)",
            (
                attempt["attempt_id"],
                experiment_id,
                attempt["start_time"],
                attempt["end_time"],
                "COMPLETED",
                attempt["tested_count"],
                json.dumps({"interesting": interesting, "tested_count": attempt["tested_count"]}),
            ),
        )
        conn.execute(
            "INSERT OR REPLACE INTO hypotheses VALUES (?,?,?,?,?,?,?,?,?)",
            (
                "LP-HYP-000001",
                1,
                page_id,
                "Unresolved LP2 pages are encrypted with a mechanism already demonstrated on a solved page (direct, atbash, atbash+3, totient-prime, or Vigenere with a historically attested key).",
                "Solved LP1/LP2 pages use these families; transfer is the cheapest discriminating test.",
                "FAILED_WITHIN_TESTED_SCOPE" if not interesting else "INTERESTING",
                json.dumps(spec["methods"]),
                str(len(spec["methods"])),
                utc_now(),
            ),
        )
        conn.commit()
    finally:
        conn.close()
    emit("experiment_complete", experiment_id=experiment_id, interesting=len(interesting), tested=len(results))
    return attempt
