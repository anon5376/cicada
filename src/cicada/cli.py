from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import acquisition, db, pgp, store
from .events import atomic_write_json, emit, utc_now
from .experiments import run_transfer_attacks
from .liber_primus.fixtures import replay_all
from .liber_primus.gematria import Gematria
from .paths import ROOT, ensure_dirs
from .reporting import write_all_reports


CORE_URLS = [
    (
        "pgp-key-krisyotam",
        "https://raw.githubusercontent.com/krisyotam/cicada3301/main/pgp/key/cicada-3301-public-key.asc",
        "community-archive",
    ),
    (
        "pgp-key-ibotpeaches",
        "https://raw.githubusercontent.com/iBotPeaches/cicada_3301/master/keys/67F363C61BA8FB6FDBA9C47D0670B0E57A35090F.asc",
        "community-archive",
    ),
    (
        "pgp-2017-04-final-message",
        "https://raw.githubusercontent.com/krisyotam/cicada3301/main/pgp/messages/2017-04-final-message.asc",
        "community-archive",
    ),
    (
        "pgp-2017-04-final-warning",
        "https://raw.githubusercontent.com/krisyotam/cicada3301/main/pgp/messages/2017-04-final-warning.asc",
        "community-archive",
    ),
    (
        "pgp-2014-05-liber-primus-release",
        "https://raw.githubusercontent.com/krisyotam/cicada3301/main/pgp/messages/2014-05-liber-primus-release.asc",
        "community-archive",
    ),
    (
        "pgp-2012-01-key-announcement",
        "https://raw.githubusercontent.com/krisyotam/cicada3301/main/pgp/messages/2012-01-key-announcement.asc",
        "community-archive",
    ),
    (
        "wiki-how-solved",
        "https://uncovering-cicada.fandom.com/wiki/How_the_solved_pages_of_the_Liber_Primus_were_solved",
        "community-wiki",
    ),
    (
        "wiki-liber-primus",
        "https://uncovering-cicada.fandom.com/wiki/Liber_Primus",
        "community-wiki",
    ),
    (
        "wiki-pgp-2017",
        "https://uncovering-cicada.fandom.com/wiki/PGP_Signed_Message_April_2017",
        "community-wiki",
    ),
    (
        "scream314-pages-and-ciphers",
        "https://raw.githubusercontent.com/scream314/cicada3301/master/pages_and_ciphers.md",
        "community-archive",
    ),
    (
        "scream314-liber-primus",
        "https://raw.githubusercontent.com/scream314/cicada3301/master/liber_primus.md",
        "community-archive",
    ),
    (
        "iddqd-transcription",
        "https://raw.githubusercontent.com/rtkd/iddqd/master/liber-primus__transcription--full/liber-primus__transcription--full",
        "community-archive",
    ),
    (
        "lp2-0-jpg",
        "https://raw.githubusercontent.com/rtkd/iddqd/master/liber-primus__images--unsolved/0.jpg",
        "community-archive",
    ),
    (
        "lp2-56-jpg",
        "https://raw.githubusercontent.com/rtkd/iddqd/master/liber-primus__images--unsolved/56.jpg",
        "community-archive",
    ),
    (
        "lp2-57-jpg",
        "https://raw.githubusercontent.com/rtkd/iddqd/master/liber-primus__images--unsolved/57.jpg",
        "community-archive",
    ),
    (
        "lp1-01-jpg",
        "https://raw.githubusercontent.com/scream314/cicada3301/master/assets/2014/liber-primus-complete/01.jpg",
        "community-archive",
    ),
]


def cmd_bootstrap(_args: argparse.Namespace) -> int:
    ensure_dirs()
    db.init_db()
    gp = Gematria()
    run = {
        "run_id": "run-20260907T041550Z",
        "started_at": utc_now(),
        "timezone_local": "Asia/Tokyo (+09)",
        "timezone_utc_offset": "+09:00",
        "phase": "A",
        "status": "running",
    }
    atomic_write_json(ROOT / "state" / "RUN_STATE.json", run)
    emit("bootstrap", run_id=run["run_id"], mapping_q=gp.q)
    write_environment()
    print(f"bootstrapped run {run['run_id']} q={gp.q} db={ROOT / 'db' / 'research.sqlite'}")
    return 0


def write_environment() -> None:
    import os
    import platform
    import shutil

    text = f"""# Environment

Recorded: {utc_now()}

## Time

- UTC at first inspection: 2026-09-07T04:15:50Z
- Local: 2026-09-07T13:15:50+09:00
- Timezone name observed: +09 / +09 (not a named zone from Python `time.tzname`)

## Host

- OS: {platform.platform()}
- Arch: {platform.machine()}
- CPU logical: 15
- Memory: 25769803776 bytes (~24 GiB)
- Disk available at start: ~606 GiB
- Python: {sys.version.split()[0]} ({sys.executable})
- GnuPG: {pgp.gpg_version()}
- curl: present
- wget: present
- ffmpeg: present
- ImageMagick / tesseract / zbar / outguess / steghide / zsteg: not found at first inspection
- Homebrew Python 3.14 and ~/.local Python 3.11 exist but lacked research packages; system Python 3.9 has Pillow, numpy, requests, networkx

## Isolation

- No container runtime is being used as a security sandbox.
- Acquisition uses an HTTPS allowlist and rejects non-global resolved addresses.
- PGP verification uses a temporary `GNUPGHOME`.
- Untrusted repository code is not executed.
- Browser automation exists in this Cursor session but is unused unless a capture requires it.

## Limits

- No explicit dollar budget was provided. No paid services are used.
- Individual HTTP bodies capped at 80 MiB.
- No onion services are probed.

## Persistence

- Workspace: `{ROOT}`
- Prior checkpoint: none. Parent tree was empty except `.cursor`.
"""
    (ROOT / "reports" / "ENVIRONMENT.md").write_text(text, encoding="utf-8")
    (ROOT / "config" / "run.yaml").write_text(
        f"""run_id: run-20260907T041550Z
started_at_utc: 2026-09-07T04:15:50Z
timezone_local_observed: "+09"
python: "{sys.executable}"
gpg: "{shutil.which("gpg")}"
max_http_bytes: 83886080
allow_paid_services: false
isolation: "allowlisted-https + isolated-gnupg-home; not a container sandbox"
""",
        encoding="utf-8",
    )


def cmd_ingest_core(_args: argparse.Namespace) -> int:
    db.init_db()
    results = []
    for source_id, url, family in CORE_URLS:
        try:
            rec = acquisition.fetch_url(url, source_id=source_id, source_family=family)
        except Exception as exc:
            rec = {"url": url, "error": str(exc), "access_status": "NETWORK_ERROR"}
            emit("retrieval_error", url=url, error=str(exc))
        results.append(rec)
        print(json.dumps({k: rec.get(k) for k in ("url", "sha256", "http_status", "access_status", "error") if k in rec or rec.get(k) is not None}, ensure_ascii=False))
    (ROOT / "sources" / "search_logs" / "ingest-core.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return 0


def cmd_verify_pgp(_args: argparse.Namespace) -> int:
    key_path = None
    # prefer smallest community key first
    conn = db.connect()
    try:
        rows = conn.execute(
            "SELECT r.url, r.sha256, b.path FROM retrievals r JOIN blobs b ON b.sha256=r.sha256 WHERE r.source_id LIKE 'pgp-%'"
        ).fetchall()
    finally:
        conn.close()
    keys = [r for r in rows if "public-key" in r["url"] or r["url"].endswith(".asc") and "keys/" in r["url"]]
    msgs = [r for r in rows if "/messages/" in r["url"] or "2017-04" in r["url"] or "key-announcement" in r["url"] or "liber-primus-release" in r["url"]]
    # classify by filename
    key_rows = [r for r in rows if "public-key" in r["url"] or "/keys/" in r["url"]]
    msg_rows = [r for r in rows if "/messages/" in r["url"]]
    reports = []
    for kr in key_rows:
        key_bytes = store.get_bytes(kr["sha256"])
        info = pgp.inspect_key(key_bytes)
        info["key_url"] = kr["url"]
        info["key_sha256"] = kr["sha256"]
        conn = db.connect()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO keys VALUES (?,?,?,?,?,?,?,?)",
                (
                    kr["sha256"][:16],
                    kr["sha256"],
                    info.get("primary_fingerprint"),
                    info.get("short_key_id"),
                    json.dumps(info.get("user_ids")),
                    info.get("algorithm"),
                    info.get("created_at_key"),
                    kr["url"],
                ),
            )
            conn.commit()
        finally:
            conn.close()
        reports.append({"kind": "key", **{k: info.get(k) for k in ("primary_fingerprint", "short_key_id", "user_ids", "key_url", "key_sha256")}})
        print("KEY", info.get("primary_fingerprint"), info.get("short_key_id"), kr["url"])
    # verify each message with each key (usually one intended)
    for mr in msg_rows:
        msg = store.get_bytes(mr["sha256"])
        for kr in key_rows:
            key_bytes = store.get_bytes(kr["sha256"])
            # skip huge keyring for first pass if > 20k and we already have a small key
            if len(key_bytes) > 20000 and any(len(store.get_bytes(k["sha256"])) < 20000 for k in key_rows):
                continue
            result = pgp.verify_clearsigned(msg, key_bytes)
            rec = {
                "message_url": mr["url"],
                "message_sha256": mr["sha256"],
                "key_url": kr["url"],
                "key_sha256": kr["sha256"],
                "result": result.get("result"),
                "signing_fpr": result.get("signing_fpr"),
                "primary_fpr": result.get("primary_fpr"),
                "tool": result.get("tool_version"),
            }
            reports.append(rec)
            print("VERIFY", rec["result"], mr["url"], rec.get("signing_fpr"))
    dest = ROOT / "reports" / "reproductions" / "pgp_verify.json"
    dest.write_text(json.dumps(reports, indent=2) + "\n", encoding="utf-8")
    return 0


def cmd_replay(_args: argparse.Namespace) -> int:
    rows = replay_all()
    dest = ROOT / "reports" / "reproductions" / "known_lp_replay.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for row in rows:
        print(row["stage_id"], "OK" if row["ok"] else "FAIL", row["reproduction_status"], row.get("reasons"))
    return 0 if all(r["ok"] for r in rows) and rows else 1


def cmd_frontier_experiment(_args: argparse.Namespace) -> int:
    # Use wiki combined 0-55 dump if we have it in fixtures companion, else
    # require a local target file.
    target = ROOT / "tests" / "liber_primus" / "lp2_unsolved_head.txt"
    if not target.exists():
        print("missing", target)
        return 2
    text = target.read_text(encoding="utf-8")
    attempt = run_transfer_attacks("lp2.unsolved_head_from_wiki", text)
    print(attempt["interpretation"], "tested", attempt["tested_count"], "interesting", len(attempt["interesting"]))
    return 0


def cmd_reports(_args: argparse.Namespace) -> int:
    write_all_reports()
    print("reports written")
    return 0


def cmd_validate(_args: argparse.Namespace) -> int:
    gp = Gematria()
    assert gp.q == 29
    assert gp.rune_index(chr(0x16A0)) == 0
    assert gp.rune_prime(chr(0x16A0)) == 2
    assert gp.encode_latin_key("DIVINITY") == [23, 10, 1, 10, 9, 10, 16, 26]
    print("validate ok", gp.version)
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="cicada")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("bootstrap").set_defaults(fn=cmd_bootstrap)
    sub.add_parser("validate").set_defaults(fn=cmd_validate)
    sub.add_parser("ingest-core").set_defaults(fn=cmd_ingest_core)
    sub.add_parser("verify-pgp").set_defaults(fn=cmd_verify_pgp)
    sub.add_parser("replay-known").set_defaults(fn=cmd_replay)
    sub.add_parser("run-frontier").set_defaults(fn=cmd_frontier_experiment)
    sub.add_parser("reports").set_defaults(fn=cmd_reports)
    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
