from __future__ import annotations

import hashlib
import mimetypes
from pathlib import Path

from .paths import ROOT, ensure_dirs


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha1_bytes(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()


def md5_bytes(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


def object_path(digest: str) -> Path:
    return ROOT / "corpus" / "objects" / "sha256" / digest[:2] / digest


def put_bytes(data: bytes, *, hint_name: str | None = None) -> dict:
    ensure_dirs()
    digest = sha256_bytes(data)
    dest = object_path(digest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        dest.write_bytes(data)
    mime, _ = mimetypes.guess_type(hint_name or "")
    if mime is None:
        if data.startswith(b"\x89PNG"):
            mime = "image/png"
        elif data[:3] == b"\xff\xd8\xff":
            mime = "image/jpeg"
        elif data.startswith(b"%PDF"):
            mime = "application/pdf"
        elif data.lstrip().startswith(b"-----BEGIN"):
            mime = "application/pgp"
        else:
            mime = "application/octet-stream"
    return {
        "sha256": digest,
        "sha1": sha1_bytes(data),
        "md5": md5_bytes(data),
        "byte_length": len(data),
        "mime": mime,
        "path": str(dest.relative_to(ROOT)),
    }


def get_bytes(digest: str) -> bytes:
    return object_path(digest).read_bytes()
