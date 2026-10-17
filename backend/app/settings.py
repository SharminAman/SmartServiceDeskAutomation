"""Values read from the project .env file."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")


@dataclass(frozen=True)
class DatabaseConfig:
    host: str
    port: int
    user: str
    password: str
    name: str
    data_dir: Path
    bin_dir: Path


def database_config() -> DatabaseConfig:
    data = os.getenv("PGDATA", ".pgdata")
    data_dir = Path(data)
    if not data_dir.is_absolute():
        data_dir = ROOT / data_dir
    bin_dir = Path(os.getenv("PG_BIN", r"C:\Program Files\PostgreSQL\15\bin"))
    return DatabaseConfig(
        host=os.getenv("PGHOST", "127.0.0.1"),
        port=int(os.getenv("PGPORT", "54329")),
        user=os.getenv("PGUSER", "requestdesk"),
        password=os.getenv("PGPASSWORD", "requestdesk"),
        name=os.getenv("PGDATABASE", "requestdesk"),
        data_dir=data_dir,
        bin_dir=bin_dir,
    )


def database_url() -> str:
    explicit = os.getenv("DATABASE_URL", "").strip()
    if explicit:
        return _for_psycopg(explicit)
    config = database_config()
    if os.getenv("RAILWAY_ENVIRONMENT") and config.host in {"127.0.0.1", "localhost"}:
        raise RuntimeError(
            "The Railway app service is missing its database address. "
            "Open the app service, Variables, and set DATABASE_URL to a reference of the Postgres service DATABASE_URL."
        )
    user = quote_plus(config.user)
    password = quote_plus(config.password)
    return f"postgresql+psycopg://{user}:{password}@{config.host}:{config.port}/{config.name}"


def _for_psycopg(url: str) -> str:
    """Railway supplies postgresql://. This app uses the psycopg driver."""
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    return url
