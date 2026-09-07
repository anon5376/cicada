from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def ensure_dirs() -> None:
    for rel in (
        "config",
        "corpus/objects/sha256",
        "corpus/raw",
        "corpus/normalized",
        "corpus/derived",
        "corpus/community",
        "corpus/unverified",
        "corpus/hoaxes",
        "corpus/manifests",
        "db",
        "state/checkpoints",
        "sources/captures",
        "sources/search_logs",
        "experiments",
        "hypotheses",
        "reports/coverage",
        "reports/reproductions",
        "reports/candidates",
        "exports",
        "tests/liber_primus",
    ):
        (ROOT / rel).mkdir(parents=True, exist_ok=True)
