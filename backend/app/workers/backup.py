"""Celery wrapper for DB backup script."""
from __future__ import annotations
import importlib.util
from pathlib import Path
from app.workers.celery_app import celery_app


def _load_backup_module():
    script = Path(__file__).resolve().parents[2] / "scripts" / "backup_db.py"
    spec = importlib.util.spec_from_file_location("koptumbuh_backup_db", script)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load backup script at {script}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@celery_app.task(name="app.workers.backup.run_backup")
def run_backup():
    mod = _load_backup_module()
    return mod.run_backup()
