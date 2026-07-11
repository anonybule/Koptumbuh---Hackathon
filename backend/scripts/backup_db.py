#!/usr/bin/env python3
"""pg_dump DATABASE_URL → MinIO backups bucket. Graceful if pg_dump missing."""
from __future__ import annotations
import os
import sys
import shutil
import subprocess
import tempfile
from datetime import datetime
from urllib.parse import urlparse, unquote

# Allow running as script from backend/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _sync_database_url(url: str) -> str:
    """Strip SQLAlchemy async driver prefix for libpq/pg_dump."""
    return (
        url.replace("postgresql+asyncpg://", "postgresql://")
        .replace("postgres+asyncpg://", "postgresql://")
    )


def _parse_dsn(url: str) -> dict:
    parsed = urlparse(_sync_database_url(url))
    return {
        "host": parsed.hostname or "localhost",
        "port": str(parsed.port or 5432),
        "user": unquote(parsed.username or ""),
        "password": unquote(parsed.password or ""),
        "dbname": (parsed.path or "/").lstrip("/") or "postgres",
    }


def run_backup(database_url: str | None = None) -> dict:
    """
    Run pg_dump and upload to MinIO koptumbuh-backups.
    Returns status dict; never raises on missing pg_dump.
    """
    from app.config import settings

    url = database_url or settings.DATABASE_URL
    if not shutil.which("pg_dump"):
        msg = "pg_dump not found on PATH — skip backup"
        print(msg, file=sys.stderr)
        return {"ok": False, "skipped": True, "reason": msg}

    dsn = _parse_dsn(url)
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"koptumbuh_{dsn['dbname']}_{stamp}.sql.gz"
    env = os.environ.copy()
    if dsn["password"]:
        env["PGPASSWORD"] = dsn["password"]

    with tempfile.TemporaryDirectory() as tmp:
        out_path = os.path.join(tmp, filename)
        cmd = [
            "pg_dump",
            "-h", dsn["host"],
            "-p", dsn["port"],
            "-U", dsn["user"],
            "-d", dsn["dbname"],
            "--no-owner",
            "--no-acl",
            "-F", "c",  # custom format (compressed)
            "-f", out_path.replace(".sql.gz", ".dump"),
        ]
        dump_path = out_path.replace(".sql.gz", ".dump")
        filename = filename.replace(".sql.gz", ".dump")
        try:
            proc = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=600)
        except Exception as e:
            return {"ok": False, "error": str(e)}

        if proc.returncode != 0:
            return {
                "ok": False,
                "error": proc.stderr or proc.stdout or f"pg_dump exit {proc.returncode}",
            }

        try:
            from app.config import settings as cfg
            from app.services.minio_service import upload_file

            bucket = getattr(cfg, "MINIO_BUCKET_BACKUPS", "koptumbuh-backups")
            key = f"db/{filename}"
            file_url = upload_file(bucket, key, dump_path, "application/octet-stream")
            size = os.path.getsize(dump_path)
            return {"ok": True, "file_url": file_url, "size": size, "filename": filename}
        except Exception as e:
            return {"ok": False, "error": f"upload failed: {e}", "local_dump": dump_path}


if __name__ == "__main__":
    result = run_backup()
    print(result)
    sys.exit(0 if result.get("ok") or result.get("skipped") else 1)
