from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

from . import db
from .events import emit, utc_now
from .paths import ROOT


STATUS_MAP = {
    "GOODSIG": "VALID",
    "BADSIG": "INVALID",
    "ERRSIG": "INVALID",
    "NO_PUBKEY": "KEY_MISSING",
    "EXPKEYSIG": "POLICY_REJECTED",
    "REVKEYSIG": "POLICY_REJECTED",
}


def gpg_version() -> str:
    gpg = shutil.which("gpg")
    if not gpg:
        return "missing"
    out = subprocess.check_output([gpg, "--version"], text=True)
    return out.splitlines()[0]


def _run_gpg(home: Path, args: list[str], stdin: bytes | None = None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["GNUPGHOME"] = str(home)
    cmd = [
        "gpg",
        "--batch",
        "--no-tty",
        "--status-fd",
        "2",
        "--pinentry-mode",
        "loopback",
        *args,
    ]
    return subprocess.run(
        cmd,
        input=stdin.decode("utf-8") if stdin is not None else None,
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )


def parse_status(stderr: str) -> list[dict[str, str]]:
    recs = []
    for line in stderr.splitlines():
        if line.startswith("[GNUPG:] "):
            parts = line[len("[GNUPG:] ") :].split(" ", 1)
            recs.append({"tag": parts[0], "rest": parts[1] if len(parts) > 1 else ""})
    return recs


def inspect_key(key_bytes: bytes) -> dict:
    with tempfile.TemporaryDirectory(prefix="cicada-gpg-") as tmp:
        home = Path(tmp)
        os.chmod(home, 0o700)
        proc = _run_gpg(home, ["--with-colons", "--import-options", "show-only", "--import"], stdin=key_bytes)
        fpr = None
        keyid = None
        uids = []
        algo = None
        created = None
        for line in proc.stdout.splitlines():
            fields = line.split(":")
            if not fields:
                continue
            if fields[0] == "pub":
                keyid = fields[4] or None
                algo = fields[3] or None
                created = fields[5] or None
            elif fields[0] == "fpr" and fpr is None:
                fpr = fields[9] or None
            elif fields[0] == "uid":
                uids.append(fields[9])
        return {
            "primary_fingerprint": fpr,
            "short_key_id": (fpr[-8:] if fpr else keyid),
            "user_ids": uids,
            "algorithm": algo,
            "created_at_key": created,
            "status_lines": parse_status(proc.stderr),
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "exit_status": proc.returncode,
        }


def verify_clearsigned(message_bytes: bytes, key_bytes: bytes) -> dict:
    tool = gpg_version()
    if tool == "missing":
        return {
            "result": "NOT_ATTEMPTED",
            "reason": "gpg binary not available",
            "tool": None,
            "tool_version": None,
        }
    with tempfile.TemporaryDirectory(prefix="cicada-gpg-") as tmp:
        home = Path(tmp)
        os.chmod(home, 0o700)
        key_path = home / "key.asc"
        msg_path = home / "msg.asc"
        key_path.write_bytes(key_bytes)
        msg_path.write_bytes(message_bytes)
        imp = _run_gpg(home, ["--import", str(key_path)])
        ver = _run_gpg(home, ["--verify", str(msg_path)])
        status = parse_status(imp.stderr) + parse_status(ver.stderr)
        result = "UNKNOWN"
        signing_fpr = None
        primary_fpr = None
        for rec in status:
            if rec["tag"] in STATUS_MAP:
                result = STATUS_MAP[rec["tag"]]
            if rec["tag"] == "VALIDSIG":
                parts = rec["rest"].split()
                if parts:
                    signing_fpr = parts[0]
                if len(parts) >= 10:
                    primary_fpr = parts[9]
                result = "VALID"
            if rec["tag"] == "NO_PUBKEY":
                result = "KEY_MISSING"
            if rec["tag"] == "BADSIG":
                result = "INVALID"
        if not message_bytes.lstrip().startswith(b"-----BEGIN PGP"):
            result = "MALFORMED"
        out = {
            "result": result,
            "tool": "gpg",
            "tool_version": tool,
            "status_lines": status,
            "stdout": ver.stdout,
            "stderr": ver.stderr,
            "exit_status": ver.returncode,
            "import_exit": imp.returncode,
            "signing_fpr": signing_fpr,
            "primary_fpr": primary_fpr,
            "command": "gpg --batch --status-fd 2 --verify (isolated GNUPGHOME)",
        }
        conn = db.connect()
        try:
            conn.execute(
                "INSERT INTO signature_attempts VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    f"sig-{uuid.uuid4().hex[:12]}",
                    None,
                    None,
                    None,
                    result,
                    "gpg",
                    tool,
                    "\n".join(f"{s['tag']} {s['rest']}".strip() for s in status),
                    signing_fpr,
                    primary_fpr,
                    utc_now(),
                ),
            )
            conn.commit()
        finally:
            conn.close()
        emit("pgp_verify", result=result, signing_fpr=signing_fpr, primary_fpr=primary_fpr)
        # also persist raw logs
        log_dir = ROOT / "reports" / "reproductions"
        log_dir.mkdir(parents=True, exist_ok=True)
        return out
