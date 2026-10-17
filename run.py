"""Start the project database, then Request Desk.

    .venv\\Scripts\\python.exe run.py

Database settings are read from .env. The site opens at http://127.0.0.1:8000.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV_PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"


def _use_project_python() -> None:
    if not VENV_PYTHON.exists():
        return
    if Path(sys.executable).resolve() == VENV_PYTHON.resolve():
        return
    os.execv(str(VENV_PYTHON), [str(VENV_PYTHON), *sys.argv])


def _tool(bin_dir: Path, name: str) -> Path:
    filename = f"{name}.exe" if os.name == "nt" else name
    return bin_dir / filename


def ensure_postgres() -> None:
    backend = str(ROOT / "backend")
    if backend not in sys.path:
        sys.path.insert(0, backend)
    from app.settings import database_config

    config = database_config()
    pg_ctl = _tool(config.bin_dir, "pg_ctl")
    initdb = _tool(config.bin_dir, "initdb")
    if not pg_ctl.is_file():
        raise SystemExit(
            f"PostgreSQL tools were not found at {config.bin_dir}. Set PG_BIN in .env to the folder that contains pg_ctl."
        )

    if not (config.data_dir / "PG_VERSION").is_file():
        subprocess.run(
            [
                str(initdb),
                "-D",
                str(config.data_dir),
                "-U",
                config.user,
                "--auth=trust",
                "--encoding=UTF8",
                "--locale=C",
            ],
            check=True,
        )

    status = subprocess.run([str(pg_ctl), "-D", str(config.data_dir), "status"], capture_output=True)
    if status.returncode != 0:
        subprocess.run(
            [
                str(pg_ctl),
                "-D",
                str(config.data_dir),
                "-l",
                str(config.data_dir / "server.log"),
                "-w",
                "-o",
                f"-p {config.port}",
                "start",
            ],
            check=True,
        )

    _ensure_database(config.host, config.port, config.user, config.password, config.name)


def _ensure_database(host: str, port: int, user: str, password: str, name: str) -> None:
    import psycopg
    from psycopg import sql

    last_error: Exception | None = None
    for _ in range(30):
        try:
            with psycopg.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                dbname="postgres",
                autocommit=True,
                connect_timeout=3,
            ) as connection:
                row = connection.execute("SELECT 1 FROM pg_database WHERE datname = %s", (name,)).fetchone()
                if row is None:
                    connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
            return
        except psycopg.OperationalError as exc:
            last_error = exc
            time.sleep(1)
    raise SystemExit(f"Could not reach PostgreSQL at {host}:{port}. {last_error}")


def ensure_frontend() -> Path:
    dist = ROOT / "frontend" / "dist"
    if (dist / "index.html").is_file():
        return dist
    npm = "npm.cmd" if os.name == "nt" else "npm"
    subprocess.run([npm, "run", "build"], cwd=ROOT / "frontend", check=True)
    if not (dist / "index.html").is_file():
        raise SystemExit("The website build did not produce frontend/dist/index.html.")
    return dist


def main() -> None:
    _use_project_python()
    sys.path.insert(0, str(ROOT / "backend"))
    ensure_postgres()
    dist = ensure_frontend()
    os.environ["STATIC_DIR"] = str(dist)

    import uvicorn

    print("Request Desk: http://127.0.0.1:8000")
    print("Sign in with the admin username and password in .env")
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, app_dir=str(ROOT / "backend"))


if __name__ == "__main__":
    main()
