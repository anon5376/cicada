from __future__ import annotations

import sqlite3
from pathlib import Path

from .paths import ROOT, ensure_dirs

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS blobs (
    sha256 TEXT PRIMARY KEY,
    sha1 TEXT,
    md5 TEXT,
    byte_length INTEGER NOT NULL,
    mime TEXT,
    path TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sources (
    source_id TEXT PRIMARY KEY,
    url TEXT,
    archive_url TEXT,
    source_family TEXT,
    source_type TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS retrievals (
    retrieval_id TEXT PRIMARY KEY,
    source_id TEXT,
    url TEXT NOT NULL,
    retrieved_at TEXT NOT NULL,
    http_status INTEGER,
    redirect_chain TEXT,
    sha256 TEXT,
    method TEXT,
    access_status TEXT,
    headers_json TEXT,
    FOREIGN KEY (source_id) REFERENCES sources(source_id),
    FOREIGN KEY (sha256) REFERENCES blobs(sha256)
);

CREATE TABLE IF NOT EXISTS artifacts (
    artifact_id TEXT PRIMARY KEY,
    logical_id TEXT,
    sha256 TEXT,
    campaign TEXT,
    stage TEXT,
    original_filename TEXT,
    claimed_date TEXT,
    authenticity_state TEXT,
    notes TEXT,
    FOREIGN KEY (sha256) REFERENCES blobs(sha256)
);

CREATE TABLE IF NOT EXISTS claims (
    claim_id TEXT PRIMARY KEY,
    proposition TEXT NOT NULL,
    scope TEXT,
    status TEXT NOT NULL,
    rationale TEXT,
    evidence_json TEXT,
    dependencies TEXT,
    counterevidence TEXT,
    what_would_change TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS keys (
    key_id TEXT PRIMARY KEY,
    sha256 TEXT,
    primary_fingerprint TEXT,
    short_key_id TEXT,
    user_ids TEXT,
    algorithm TEXT,
    created_at_key TEXT,
    notes TEXT,
    FOREIGN KEY (sha256) REFERENCES blobs(sha256)
);

CREATE TABLE IF NOT EXISTS signature_attempts (
    attempt_id TEXT PRIMARY KEY,
    message_sha256 TEXT,
    signature_sha256 TEXT,
    key_sha256 TEXT,
    result TEXT NOT NULL,
    tool TEXT,
    tool_version TEXT,
    status_text TEXT,
    signing_fpr TEXT,
    primary_fpr TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pages (
    page_id TEXT PRIMARY KEY,
    collection TEXT NOT NULL,
    ordinal INTEGER,
    filename_alias TEXT,
    sha256 TEXT,
    transcription_status TEXT,
    text_recovery_status TEXT,
    method_status TEXT,
    instruction_status TEXT,
    notes TEXT,
    FOREIGN KEY (sha256) REFERENCES blobs(sha256)
);

CREATE TABLE IF NOT EXISTS hypotheses (
    hypothesis_id TEXT PRIMARY KEY,
    version INTEGER NOT NULL,
    target_ids TEXT,
    precise_claim TEXT NOT NULL,
    motivation TEXT,
    status TEXT NOT NULL,
    parameter_domains TEXT,
    search_space_size TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS experiments (
    experiment_id TEXT PRIMARY KEY,
    definition_hash TEXT NOT NULL,
    hypothesis_id TEXT,
    spec_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS experiment_attempts (
    attempt_id TEXT PRIMARY KEY,
    experiment_id TEXT NOT NULL,
    start_time TEXT,
    end_time TEXT,
    execution_status TEXT,
    tested_count INTEGER,
    result_json TEXT,
    FOREIGN KEY (experiment_id) REFERENCES experiments(experiment_id)
);

CREATE TABLE IF NOT EXISTS searches (
    search_id TEXT PRIMARY KEY,
    query TEXT NOT NULL,
    service TEXT,
    checked_at TEXT NOT NULL,
    result_count INTEGER,
    notes TEXT,
    coverage_bound TEXT
);

CREATE TABLE IF NOT EXISTS edges (
    edge_id TEXT PRIMARY KEY,
    src TEXT NOT NULL,
    dst TEXT NOT NULL,
    rel TEXT NOT NULL,
    notes TEXT
);
"""


def db_path() -> Path:
    return ROOT / "db" / "research.sqlite"


def connect() -> sqlite3.Connection:
    ensure_dirs()
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    conn = connect()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()
