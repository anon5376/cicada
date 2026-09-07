from __future__ import annotations

import ipaddress
import json
import socket
import uuid
from urllib.parse import urlparse

import requests

from . import db, store
from .events import emit, utc_now

ALLOWED_HOSTS = {
    "github.com",
    "raw.githubusercontent.com",
    "api.github.com",
    "archive.org",
    "web.archive.org",
    "uncovering-cicada.fandom.com",
    "static.wikia.nocookie.net",
    "pastebin.com",
    "en.wikipedia.org",
    "index.commoncrawl.org",
    "data.commoncrawl.org",
}

BLOCKED_METHODS_HINTS = ("vote", "submit", "delete", "create", "login", "signup")
MAX_BYTES = 80 * 1024 * 1024
TIMEOUT = 45


def _host_allowed(host: str) -> bool:
    host = host.lower().rstrip(".")
    if host in ALLOWED_HOSTS:
        return True
    return any(host.endswith("." + h) for h in ALLOWED_HOSTS)


def _ip_public(host: str) -> None:
    infos = socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_global:
            raise PermissionError(f"refusing non-global address {ip} for {host}")


def validate_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise PermissionError(f"only https is permitted: {url}")
    if parsed.username or parsed.password:
        raise PermissionError("credentials in URL are not permitted")
    host = parsed.hostname or ""
    if not _host_allowed(host):
        raise PermissionError(f"host not in acquisition allowlist: {host}")
    path = (parsed.path or "").lower()
    if any(h in path for h in BLOCKED_METHODS_HINTS) and parsed.query:
        # path names alone are not enough; keep this as a soft check
        pass
    _ip_public(host)


def fetch_url(url: str, *, source_id: str | None = None, source_family: str = "web") -> dict:
    validate_url(url)
    session = requests.Session()
    session.max_redirects = 5
    headers = {"User-Agent": "cicada-research/0.1 (historical puzzle archive; passive GET)"}
    resp = session.get(url, headers=headers, timeout=TIMEOUT, allow_redirects=True, stream=True)
    chain = [url] + [h.url for h in resp.history] + ([resp.url] if resp.url != url else [])
    for hop in chain:
        parsed = urlparse(hop)
        if parsed.hostname and not _host_allowed(parsed.hostname):
            raise PermissionError(f"redirect left allowlist: {hop}")
    if resp.status_code != 200:
        rec = {
            "url": url,
            "http_status": resp.status_code,
            "access_status": "ACCESS_DENIED" if resp.status_code in (401, 403) else "CURRENT_RESOURCE_GONE" if resp.status_code == 404 else "NETWORK_ERROR",
            "retrieved_at": utc_now(),
        }
        emit("retrieval_failed", **rec)
        return rec
    chunks = []
    total = 0
    for chunk in resp.iter_content(64 * 1024):
        total += len(chunk)
        if total > MAX_BYTES:
            raise RuntimeError("response exceeded MAX_BYTES")
        chunks.append(chunk)
    data = b"".join(chunks)
    blob = store.put_bytes(data, hint_name=urlparse(url).path.split("/")[-1])
    conn = db.connect()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO blobs VALUES (?,?,?,?,?,?,?)",
            (blob["sha256"], blob["sha1"], blob["md5"], blob["byte_length"], blob["mime"], blob["path"], utc_now()),
        )
        sid = source_id or f"src-{uuid.uuid4().hex[:12]}"
        conn.execute(
            "INSERT OR IGNORE INTO sources VALUES (?,?,?,?,?,?)",
            (sid, url, None, source_family, "https", None),
        )
        rid = f"ret-{uuid.uuid4().hex[:12]}"
        conn.execute(
            "INSERT INTO retrievals VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                rid,
                sid,
                url,
                utc_now(),
                resp.status_code,
                json.dumps(chain),
                blob["sha256"],
                "GET",
                "OK",
                json.dumps({k: resp.headers.get(k) for k in ("Content-Type", "ETag", "Last-Modified")}),
            ),
        )
        conn.commit()
    finally:
        conn.close()
    out = {
        "retrieval_id": rid,
        "source_id": sid,
        "url": url,
        "http_status": 200,
        "access_status": "OK",
        "retrieved_at": utc_now(),
        **blob,
    }
    emit("retrieval_ok", url=url, sha256=blob["sha256"], bytes=blob["byte_length"])
    return out
