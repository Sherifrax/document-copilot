"""Shared corpus and database helpers for one-off ingestion commands."""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy.engine import URL, make_url

REPO_ROOT = Path(__file__).resolve().parents[2]
CORPUS_DIR = REPO_ROOT / "data" / "markdown"
MANIFEST_PATH = CORPUS_DIR / "manifest.json"
COMPANY_NAMES = {
    "AAPL": "Apple Inc.",
    "AMZN": "Amazon.com, Inc.",
    "GOOGL": "Alphabet Inc.",
    "MSFT": "Microsoft Corporation",
    "NVDA": "NVIDIA Corporation",
}


def database_url(raw_url: str) -> URL:
    url = make_url(raw_url)
    if url.get_backend_name() != "postgresql":
        raise ValueError("DATABASE_URL must be a PostgreSQL connection")
    return url.set(drivername="postgresql+psycopg")


def load_manifest() -> dict[str, object]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def markdown_paths_by_accession() -> dict[str, Path]:
    manifest = load_manifest()
    return {
        filing["accession_number"]: CORPUS_DIR / filing["local_path"]
        for filing in manifest["filings"]
    }
